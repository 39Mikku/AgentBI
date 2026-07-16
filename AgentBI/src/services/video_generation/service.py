from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from AgentBI.src.schemas.capability_settings_schema import resolve_capability_config
from AgentBI.src.schemas.video_generation_schema import (
    dimensions_for_aspect_ratio,
    frames_for_duration,
)
from AgentBI.src.services.video_generation.agnes_client import AgnesVideoClient, AgnesVideoError


class VideoGenerationService:
    def __init__(
        self,
        *,
        repository: Any,
        client: AgnesVideoClient,
        output_root: str | Path,
        asset_service: Any,
        poll_interval: float = 5.0,
        max_transient_failures: int = 4,
    ):
        self.repository = repository
        self.client = client
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.asset_service = asset_service
        self.poll_interval = max(0.0, poll_interval)
        self.max_transient_failures = max(1, max_transient_failures)
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def submit(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        message_id: str | None,
        prompt: str,
        aspect_ratio: str | None = None,
        duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("请提供完整的视频生成提示词")
        stored = self.repository.get_capability_config(user_id, "tool.video_generation")
        config = resolve_capability_config("tool.video_generation", stored)
        selected_ratio = aspect_ratio or config["default_aspect_ratio"]
        selected_duration = int(duration_seconds or config["default_duration_seconds"])
        width, height = dimensions_for_aspect_ratio(selected_ratio)
        num_frames = frames_for_duration(selected_duration)
        job = self.repository.create_video_generation_job(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "prompt": clean_prompt,
                "aspect_ratio": selected_ratio,
                "duration_seconds": selected_duration,
                "num_frames": num_frames,
                "frame_rate": 24,
            }
        )
        try:
            provider = await self.client.create_video(
                prompt=clean_prompt,
                width=width,
                height=height,
                num_frames=num_frames,
            )
        except Exception as error:
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": str(error)}
            )
            raise
        queued = self.repository.update_video_generation_job(
            job["_id"],
            {
                "provider_video_id": str(provider["video_id"]),
                "status": "queued",
                "progress": int(provider.get("progress") or 0),
            },
        )
        self._schedule(job["_id"])
        return queued

    def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        return self.repository.get_video_generation_job(job_id, user_id)

    async def start(self) -> None:
        for job in self.repository.list_active_video_generation_jobs():
            if job.get("provider_video_id"):
                self._schedule(job["_id"])
            else:
                self.repository.update_video_generation_job(
                    job["_id"],
                    {"status": "failed", "error": "服务重启后无法恢复未提交的 Agnes 任务"},
                )

    def _schedule(self, job_id: str) -> None:
        active = self._tasks.get(job_id)
        if active and not active.done():
            return
        task = asyncio.create_task(self._poll_job(job_id))
        self._tasks[job_id] = task
        task.add_done_callback(lambda completed, key=job_id: self._forget(key, completed))

    def _forget(self, job_id: str, task: asyncio.Task[None]) -> None:
        if self._tasks.get(job_id) is task:
            self._tasks.pop(job_id, None)

    async def wait_for_job(self, job_id: str) -> None:
        task = self._tasks.get(job_id)
        if task:
            await asyncio.shield(task)

    async def _poll_job(self, job_id: str) -> None:
        failures = 0
        while True:
            job = self.repository.get_video_generation_job_by_id(job_id)
            if not job or job.get("status") in {"completed", "failed"}:
                return
            try:
                result = await self.client.get_video(str(job["provider_video_id"]))
                failures = 0
            except AgnesVideoError as error:
                failures += 1
                if error.retryable and failures < self.max_transient_failures:
                    await asyncio.sleep(self.poll_interval * failures)
                    continue
                self.repository.update_video_generation_job(
                    job_id, {"status": "failed", "error": str(error)}
                )
                return
            except Exception as error:
                self.repository.update_video_generation_job(
                    job_id, {"status": "failed", "error": str(error)}
                )
                return

            status = str(result.get("status") or "in_progress")
            progress = max(0, min(100, int(result.get("progress") or 0)))
            if status == "failed":
                self.repository.update_video_generation_job(
                    job_id,
                    {"status": "failed", "progress": progress, "error": self._error_text(result)},
                )
                return
            if status == "completed":
                await self._complete_job(job, result)
                return
            self.repository.update_video_generation_job(
                job_id,
                {"status": "queued" if status == "queued" else "in_progress", "progress": progress},
            )
            await asyncio.sleep(self.poll_interval)

    async def _complete_job(self, job: dict[str, Any], result: dict[str, Any]) -> None:
        url = str(result.get("url") or "").strip()
        if not url:
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": "Agnes 已完成任务但没有返回视频 URL"}
            )
            return
        try:
            content = await self.client.download_video(url)
            if len(content) < 12 or content[4:8] != b"ftyp":
                raise ValueError("Agnes 返回的 MP4 文件无效")
            user_directory = hashlib.sha256(job["user_id"].encode("utf-8")).hexdigest()[:16]
            relative_path = Path("videos") / user_directory / f"{job['_id']}.mp4"
            target = self.output_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            asset = self.asset_service.register_generated_video(
                user_id=job["user_id"],
                job_id=job["_id"],
                relative_path=relative_path.as_posix(),
                size=len(content),
                metadata={
                    "model": "agnes-video-v2.0",
                    "prompt": job["prompt"],
                    "aspect_ratio": job["aspect_ratio"],
                    "duration_seconds": job["duration_seconds"],
                    "provider_size": result.get("size"),
                },
            )
            asset_id = str(asset["_id"])
            if job.get("message_id"):
                self.repository.bind_message_assets(
                    str(job["message_id"]), job["user_id"], [asset_id]
                )
            self.repository.update_video_generation_job(
                job["_id"],
                {"status": "completed", "progress": 100, "asset_id": asset_id, "error": None},
            )
        except Exception as error:
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": str(error)}
            )

    @staticmethod
    def _error_text(result: dict[str, Any]) -> str:
        error = result.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("detail") or error)
        return str(error or "Agnes 视频生成失败")

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        close = getattr(self.client, "close", None)
        if close:
            await close()
