from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MusicTrack(BaseModel):
    id: str
    name: str
    artists: list[str] = Field(default_factory=list)
    album: str = ""
    cover_url: str | None = None
    duration_ms: int | None = None
    available: bool = True
    unavailable_reason: str | None = None


class MusicPlayback(BaseModel):
    track_id: str
    url: str | None = None
    available: bool
    unavailable_reason: str | None = None


class MusicCard(BaseModel):
    kind: Literal["music.track", "music.track-list"]
    title: str | None = None
    tracks: list[MusicTrack]

