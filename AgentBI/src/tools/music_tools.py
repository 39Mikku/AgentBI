from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from AgentBI.src.schemas.music_schema import MusicTrack
from AgentBI.src.services.netease_music_client import NeteaseMusicClient


@dataclass(slots=True)
class MusicToolResult:
    content: str
    card: dict[str, Any] | None = None


def _card(kind: str, title: str, tracks: list[MusicTrack]) -> dict[str, Any]:
    return {
        "kind": kind,
        "payload": {
            "title": title,
            "tracks": [track.model_dump(mode="json") for track in tracks],
        },
    }


def _content(tracks: list[MusicTrack]) -> str:
    return json.dumps(
        {
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "artists": track.artists,
                    "album": track.album,
                    "available": track.available,
                }
                for track in tracks
            ]
        },
        ensure_ascii=False,
    )


async def search_tracks(client: NeteaseMusicClient, query: str) -> MusicToolResult:
    tracks = await client.search_tracks(query)
    return MusicToolResult(
        content=_content(tracks) if tracks else "没有找到匹配的歌曲。",
        card=_card("music.track-list", f"搜索：{query}", tracks) if tracks else None,
    )


async def daily_recommendations(client: NeteaseMusicClient) -> MusicToolResult:
    tracks = await client.daily_recommendations()
    return MusicToolResult(
        content=_content(tracks) if tracks else "今天暂时没有可用的每日推荐。",
        card=_card("music.track-list", "今日推荐", tracks) if tracks else None,
    )


async def resolve_track(client: NeteaseMusicClient, track_id: str) -> MusicToolResult:
    track = await client.resolve_track(track_id)
    return MusicToolResult(
        content=_content([track]),
        card=_card("music.track", "为你点播", [track]),
    )
