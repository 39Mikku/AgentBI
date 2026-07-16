from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


VideoAspectRatio = Literal["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"]
VideoDuration = int
VideoGenerationStatus = Literal["queued", "in_progress", "completed", "failed"]
VideoModel = Literal["agnes-video-v2.0", "doubao-seedance-1-0-pro-250528"]

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

    model: VideoModel = "agnes-video-v2.0"
    default_aspect_ratio: VideoAspectRatio = "16:9"
    default_duration_seconds: VideoDuration = 5
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    generate_audio: bool = False
    watermark: bool = False

    @model_validator(mode="before")
    @classmethod
    def migrate_unavailable_seedance_model(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if value.get("model") != "doubao-seedance-1-5-pro-251215":
            return value
        migrated = dict(value)
        migrated["model"] = "doubao-seedance-1-0-pro-250528"
        if migrated.get("default_duration_seconds") not in {5, 10}:
            migrated["default_duration_seconds"] = 5
        if migrated.get("resolution") == "1080p":
            migrated["resolution"] = "720p"
        migrated["generate_audio"] = False
        return migrated

    @model_validator(mode="after")
    def validate_model_settings(self) -> "VideoGenerationConfig":
        if self.model == "agnes-video-v2.0":
            if self.default_duration_seconds not in {3, 5, 10, 18}:
                raise ValueError("Agnes 时长仅支持 3、5、10 或 18 秒")
            if self.default_aspect_ratio in {"21:9", "adaptive"}:
                raise ValueError("Agnes 不支持该画幅")
        elif self.default_duration_seconds not in {5, 10}:
            raise ValueError("Seedance 1.0 Pro 时长仅支持 5 或 10 秒")
        if self.model == "doubao-seedance-1-0-pro-250528":
            if self.resolution == "1080p":
                raise ValueError("Seedance 1.0 Pro 仅支持 480p 或 720p")
            if self.generate_audio:
                raise ValueError("Seedance 1.0 Pro 不支持同步生成音频")
        return self


class VideoGenerationJobResponse(BaseModel):
    id: str
    user_id: str
    conversation_id: str | None = None
    message_id: str | None = None
    prompt: str
    provider: Literal["agnes", "volcengine"] = "agnes"
    model: str = "agnes-video-v2.0"
    aspect_ratio: VideoAspectRatio
    duration_seconds: VideoDuration
    resolution: str = "720p"
    generate_audio: bool = False
    watermark: bool = False
    use_attached_image: bool = False
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
            provider=document.get("provider") or "agnes",
            model=document.get("model") or "agnes-video-v2.0",
            aspect_ratio=document["aspect_ratio"],
            duration_seconds=document["duration_seconds"],
            resolution=document.get("resolution") or "720p",
            generate_audio=bool(document.get("generate_audio")),
            watermark=bool(document.get("watermark")),
            use_attached_image=bool(document.get("use_attached_image")),
            status=document["status"],
            progress=int(document.get("progress") or 0),
            provider_video_id=document.get("provider_video_id"),
            asset_id=document.get("asset_id"),
            video_url=document.get("video_url"),
            error=document.get("error"),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )
