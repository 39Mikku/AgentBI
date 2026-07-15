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


async def search_videos(client: BilibiliClient, query: str, limit: int = 3) -> BilibiliToolResult:
    videos = await client.search_videos(query, limit=limit)
    return BilibiliToolResult(
        content=_content(videos) if videos else "没有找到匹配的哔哩哔哩视频。",
        card=_card("bilibili.video-list", f"搜索：{query}", videos) if videos else None,
    )


async def search_creator_videos(
    client: BilibiliClient,
    creator: str,
    query: str = "",
    *,
    limit: int = 3,
    scan_limit: int = 20,
) -> BilibiliToolResult:
    videos = await client.search_creator_videos(
        creator,
        query,
        limit=limit,
        scan_limit=scan_limit,
    )
    subject = f"{creator} · {query}" if query else f"{creator} · 最新投稿"
    return BilibiliToolResult(
        content=_content(videos) if videos else f"没有在 {creator} 的稿件中找到匹配视频。",
        card=_card("bilibili.video-list", subject, videos) if videos else None,
    )


async def get_video_detail(client: BilibiliClient, bvid: str) -> BilibiliToolResult:
    video = await client.get_video(bvid)
    return BilibiliToolResult(
        content=_content([video]),
        card=_card("bilibili.video", "视频详情", [video]),
    )
