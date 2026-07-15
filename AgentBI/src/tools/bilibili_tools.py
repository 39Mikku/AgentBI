from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from AgentBI.src.schemas.bilibili_schema import BilibiliVideo
from AgentBI.src.services.bilibili_client import BilibiliClient


@dataclass(slots=True)
class BilibiliToolResult:
    content: str
    card: dict[str, Any] | None = None


def _card(kind: str, title: str, videos: list[BilibiliVideo]) -> dict[str, Any]:
    return {
        "kind": kind,
        "payload": {
            "title": title,
            "videos": [video.model_dump(mode="json") for video in videos],
        },
    }


def _content(videos: list[BilibiliVideo]) -> str:
    return json.dumps(
        {
            "videos": [
                {
                    "bvid": video.bvid,
                    "title": video.title,
                    "author": video.author,
                    "duration_seconds": video.duration_seconds,
                    "play_count": video.play_count,
                    "url": video.url,
                }
                for video in videos
            ]
        },
        ensure_ascii=False,
    )


async def search_videos(client: BilibiliClient, query: str) -> BilibiliToolResult:
    videos = await client.search_videos(query, limit=3)
    return BilibiliToolResult(
        content=_content(videos) if videos else "没有找到匹配的哔哩哔哩视频。",
        card=_card("bilibili.video-list", f"搜索：{query}", videos) if videos else None,
    )


async def get_video_detail(client: BilibiliClient, bvid: str) -> BilibiliToolResult:
    video = await client.get_video(bvid)
    return BilibiliToolResult(
        content=_content([video]),
        card=_card("bilibili.video", "视频详情", [video]),
    )

