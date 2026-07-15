from __future__ import annotations

from pydantic import BaseModel, Field


class BilibiliVideo(BaseModel):
    bvid: str = Field(pattern=r"^BV[0-9A-Za-z]{10}$")
    title: str
    author: str = ""
    cover_url: str | None = None
    duration_seconds: int = Field(default=0, ge=0)
    play_count: int = Field(default=0, ge=0)
    published_at: int | None = None
    description: str = ""
    url: str

