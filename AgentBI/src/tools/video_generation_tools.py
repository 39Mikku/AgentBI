from __future__ import annotations

import json

from AgentBI.src.services.video_generation.service import VideoGenerationService
from AgentBI.src.tools.image_generation_tools import AtomicToolResult


async def generate_video(
    service: VideoGenerationService,
    *,
    user_id: str,
    conversation_id: str | None,
    message_id: str | None,
    prompt: str,
    aspect_ratio: str | None = None,
    duration_seconds: int | None = None,
) -> AtomicToolResult:
    job = await service.submit(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        duration_seconds=duration_seconds,
    )
    job_id = str(job["_id"])
    compact = {
        "status": job["status"],
        "job_id": job_id,
        "video_generation_started": True,
        "display_instruction": "视频生成任务已由界面卡片接管并自动更新；不要重复输出链接，也不要反复查询进度。",
    }
    return AtomicToolResult(
        content=json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        card={
            "kind": "video.generation",
            "payload": {
                "job_id": job_id,
                "status": job["status"],
                "progress": int(job.get("progress") or 0),
                "prompt": job["prompt"],
                "aspect_ratio": job["aspect_ratio"],
                "duration_seconds": job["duration_seconds"],
                "model": "agnes-video-v2.0",
            },
        },
    )
