from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

from AgentBI.src.schemas.capability_settings_schema import resolve_capability_config
from AgentBI.src.schemas.video_generation_schema import (
    VideoGenerationConfig,
    dimensions_for_aspect_ratio,
    frames_for_duration,
)
from AgentBI.src.services.video_generation.provider import VideoCreateRequest, VideoProvider


_MODEL_PROVIDERS = {
    "agnes-video-v2.0": "agnes",
    "doubao-seedance-1-0-pro-250528": "volcengine",
}

_MODEL_DURATIONS = {
    "agnes-video-v2.0": (3, 5, 10, 18),
    "doubao-seedance-1-0-pro-250528": (5, 10),
}
_MODEL_RATIOS = {
    "agnes-video-v2.0": {"16:9", "9:16", "1:1", "4:3", "3:4"},
    "doubao-seedance-1-0-pro-250528": {
        "16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"
    },
}


class VideoGenerationService:
    def __init__(
        self,
        *,
        repository: Any,
        output_root: str | Path,
        asset_service: Any,
        client: VideoProvider | None = None,
        providers: dict[str, VideoProvider] | None = None,
        poll_interval: float = 5.0,
        max_transient_failures: int = 4,
    ):
        configured = dict(providers or {})
        if client is not None:
            configured.setdefault(getattr(client, "provider_id", "agnes"), client)
        self.repository = repository
        self.providers = configured
        self.client = client or configured.get("agnes")
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.asset_service = asset_service
        self.poll_interval = max(0.0, poll_interval)
        self.max_transient_failures = max(1, max_transient_failures)
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def _provider(self, provider_id: str) -> VideoProvider:
        provider = self.providers.get(provider_id)
        if not provider:
            raise ValueError(f"视频提供商未配置：{provider_id}")
        return provider

    async def submit(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        message_id: str | None,
        prompt: str,
        aspect_ratio: str | None = None,
        duration_seconds: int | None = None,
        use_attached_image: bool = False,
        reference_image_data_url: str | None = None,
    ) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("请提供完整的视频生成提示词")
        stored = self.repository.get_capability_config(user_id, "tool.video_generation")
        base_config = resolve_capability_config("tool.video_generation", stored)
        model = str(base_config["model"])
        requested_duration = int(duration_seconds) if duration_seconds is not None else None
        selected_duration = (
            min(_MODEL_DURATIONS[model], key=lambda value: (abs(value - requested_duration), value))
            if requested_duration is not None
            else base_config["default_duration_seconds"]
        )
        selected_ratio = (
            aspect_ratio
            if aspect_ratio in _MODEL_RATIOS[model]
            else base_config["default_aspect_ratio"]
        )
        selected = VideoGenerationConfig.model_validate(
            {
                **base_config,
                "default_aspect_ratio": selected_ratio,
                "default_duration_seconds": selected_duration,
            }
        )
        provider_id = _MODEL_PROVIDERS[selected.model]
        provider = self._provider(provider_id)
        if use_attached_image and provider_id != "volcengine":
            raise ValueError("当前视频模型不支持附件图生视频")
        if use_attached_image and not reference_image_data_url:
            raise ValueError("当前消息没有可用于图生视频的附件图片")

        width = height = num_frames = None
        if provider_id == "agnes":
            width, height = dimensions_for_aspect_ratio(selected.default_aspect_ratio)
            num_frames = frames_for_duration(selected.default_duration_seconds)

        job = self.repository.create_video_generation_job(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "prompt": clean_prompt,
                "provider": provider_id,
                "model": selected.model,
                "aspect_ratio": selected.default_aspect_ratio,
                "duration_seconds": selected.default_duration_seconds,
                "num_frames": num_frames or 0,
                "frame_rate": 24,
                "resolution": selected.resolution,
                "generate_audio": selected.generate_audio,
                "watermark": selected.watermark,
                "use_attached_image": use_attached_image,
            }
        )
        request = VideoCreateRequest(
            prompt=clean_prompt,
            model=selected.model,
            aspect_ratio=selected.default_aspect_ratio,
            duration_seconds=selected.default_duration_seconds,
            resolution=selected.resolution,
            generate_audio=selected.generate_audio,
            watermark=selected.watermark,
            width=width,
            height=height,
            num_frames=num_frames,
            image_data_url=reference_image_data_url if use_attached_image else None,
        )
        try:
            remote = await provider.create_video(request)
        except Exception as error:
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": str(error)}
            )
            raise
        task_id = str(remote.get("task_id") or remote.get("video_id") or "").strip()
        if not task_id:
            error = ValueError("视频提供商创建任务后未返回任务 ID")
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": str(error)}
            )
            raise error
        queued = self.repository.update_video_generation_job(
            job["_id"],
            {
                "provider_video_id": task_id,
                "status": "queued",
                "progress": int(remote.get("progress") or 0),
            },
        )
        self._schedule(job["_id"])
        return queued

    def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        return self.repository.get_video_generation_job(job_id, user_id)

    async def start(self) -> None:
        for job in self.repository.list_active_video_generation_jobs():
            if job.get("provider_video_id") and job.get("provider") in self.providers:
                self._schedule(job["_id"])
            else:
                self.repository.update_video_generation_job(
                    job["_id"],
                    {"status": "failed", "error": "服务重启后无法恢复该视频任务"},
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
                provider = self._provider(str(job.get("provider") or "agnes"))
                result = await provider.get_video(str(job["provider_video_id"]))
                failures = 0
            except Exception as error:
                failures += 1
                if bool(getattr(error, "retryable", False)) and failures < self.max_transient_failures:
                    await asyncio.sleep(self.poll_interval * failures)
                    continue
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
                await self._complete_job(job, result, provider)
                return
            self.repository.update_video_generation_job(
                job_id,
                {"status": "queued" if status == "queued" else "in_progress", "progress": progress},
            )
            await asyncio.sleep(self.poll_interval)

    async def _complete_job(
        self, job: dict[str, Any], result: dict[str, Any], provider: VideoProvider
    ) -> None:
        url = str(result.get("url") or "").strip()
        if not url:
            self.repository.update_video_generation_job(
                job["_id"], {"status": "failed", "error": "视频任务完成但没有返回视频 URL"}
            )
            return
        try:
            content = await provider.download_video(url)
            if len(content) < 12 or content[4:8] != b"ftyp":
                raise ValueError("视频提供商返回的 MP4 文件无效")
            user_directory = hashlib.sha256(job["user_id"].encode("utf-8")).hexdigest()[:16]
            relative_path = Path("videos") / user_directory / f"{job['_id']}.mp4"
            target = self.output_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            provider_metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
            asset = self.asset_service.register_generated_video(
                user_id=job["user_id"],
                job_id=job["_id"],
                relative_path=relative_path.as_posix(),
                size=len(content),
                metadata={
                    "provider": job.get("provider"),
                    "model": job.get("model"),
                    "prompt": job["prompt"],
                    "aspect_ratio": job["aspect_ratio"],
                    "duration_seconds": job["duration_seconds"],
                    "resolution": provider_metadata.get("resolution") or job.get("resolution"),
                    "generate_audio": provider_metadata.get("generate_audio", job.get("generate_audio")),
                    "use_attached_image": bool(job.get("use_attached_image")),
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
        return str(error or "视频生成失败")

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        closed: set[int] = set()
        for provider in self.providers.values():
            if id(provider) in closed:
                continue
            closed.add(id(provider))
            close = getattr(provider, "close", None)
            if close:
                await close()
