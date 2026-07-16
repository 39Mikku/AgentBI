from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VideoCreateRequest:
    prompt: str
    model: str
    aspect_ratio: str
    duration_seconds: int
    resolution: str = "720p"
    generate_audio: bool = False
    watermark: bool = False
    width: int | None = None
    height: int | None = None
    num_frames: int | None = None
    image_data_url: str | None = None


class VideoProvider(Protocol):
    provider_id: str

    async def create_video(self, request: VideoCreateRequest) -> dict: ...

    async def get_video(self, task_id: str) -> dict: ...

    async def download_video(self, url: str) -> bytes: ...

    async def close(self) -> None: ...
