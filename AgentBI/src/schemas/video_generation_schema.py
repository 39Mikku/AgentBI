from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


VideoAspectRatio = Literal["16:9", "9:16", "1:1", "4:3", "3:4"]
VideoDuration = Literal[3, 5, 10, 18]
VideoGenerationStatus = Literal["queued", "in_progress", "completed", "failed"]

_FRAME_PRESETS: dict[int, int] = {3: 81, 5: 121, 10: 241, 18: 441}
_DIMENSION_PRESETS: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (768, 768),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
}


def frames_for_duration(duration_seconds: int) -> int:
    try:
        return _FRAME_PRESETS[duration_seconds]
    except KeyError as error:
        raise ValueError("视频时长仅支持 3、5、10 或 18 秒") from error


def dimensions_for_aspect_ratio(aspect_ratio: str) -> tuple[int, int]:
    try:
        return _DIMENSION_PRESETS[aspect_ratio]
    except KeyError as error:
        raise ValueError("视频画幅仅支持 16:9、9:16、1:1、4:3 或 3:4") from error


class VideoGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_aspect_ratio: VideoAspectRatio = "16:9"
    default_duration_seconds: VideoDuration = 5


class VideoGenerationJobResponse(BaseModel):
    id: str
    user_id: str
    conversation_id: str | None = None
    message_id: str | None = None
    prompt: str
    aspect_ratio: VideoAspectRatio
    duration_seconds: VideoDuration
    status: VideoGenerationStatus
    progress: int = Field(default=0, ge=0, le=100)
    provider_video_id: str | None = None
    asset_id: str | None = None
    video_url: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "VideoGenerationJobResponse":
        return cls(
            id=str(document["_id"]),
            user_id=document["user_id"],
            conversation_id=document.get("conversation_id"),
            message_id=document.get("message_id"),
            prompt=document["prompt"],
            aspect_ratio=document["aspect_ratio"],
            duration_seconds=document["duration_seconds"],
            status=document["status"],
            progress=int(document.get("progress") or 0),
            provider_video_id=document.get("provider_video_id"),
            asset_id=document.get("asset_id"),
            video_url=document.get("video_url"),
            error=document.get("error"),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )
