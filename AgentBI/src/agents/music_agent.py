from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.services.netease_music_client import NeteaseMusicClient
from AgentBI.src.tools.music_tools import (
    MusicToolResult,
    daily_recommendations,
    resolve_track,
    search_tracks,
)


class MusicAgent:
    system_prompt = (
        "你是音乐点播子代理。根据用户意图搜索歌曲、获取每日推荐或按歌曲 ID 获取详情。"
        "必须通过工具获得真实歌曲数据，不得编造歌曲 ID。得到结果后用一句简短中文说明卡片内容。"
    )

    def __init__(self, client: NeteaseMusicClient | None):
        self.client = client

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_tracks",
                    "description": "按歌曲名、歌手或关键词搜索网易云音乐，最多返回三首。",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "daily_recommendations",
                    "description": "获取当前固定网易云账号的每日推荐歌曲。",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "resolve_track",
                    "description": "根据已确认的网易云歌曲 ID 获取一首歌的卡片。",
                    "parameters": {
                        "type": "object",
                        "properties": {"track_id": {"type": "string"}},
                        "required": ["track_id"],
                    },
                },
            },
        ]

    async def stream(
        self,
        llm_client: AsyncOpenAI,
        model: str,
        temperature: float,
        instruction: str,
    ) -> AsyncIterator[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": instruction},
        ]
        for _ in range(3):
            content_parts: list[str] = []
            tool_calls: dict[int, dict[str, str]] = {}
            response = await llm_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
                tools=self.tool_definitions(),
            )
            async for chunk in response:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                delta = choice.delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "delta", "content": delta.content}
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield {"type": "reasoning_summary", "content": reasoning}
                for tool_call in delta.tool_calls or []:
                    entry = tool_calls.setdefault(tool_call.index, {"id": "", "name": "", "arguments": ""})
                    if tool_call.id:
                        entry["id"] = tool_call.id
                    if tool_call.function and tool_call.function.name:
                        entry["name"] = tool_call.function.name
                    if tool_call.function and tool_call.function.arguments:
                        entry["arguments"] += tool_call.function.arguments
            if not tool_calls:
                return
            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(content_parts) or None,
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": call["name"], "arguments": call["arguments"]},
                        }
                        for call in tool_calls.values()
                    ],
                }
            )
            for call in tool_calls.values():
                yield {"type": "tool_started", "tool": self._tool_label(call["name"])}
                result = await self._invoke_tool(call["name"], call["arguments"])
                if result.card:
                    yield {"type": "card", **result.card}
                yield {
                    "type": "tool_finished",
                    "tool": self._tool_label(call["name"]),
                    "content": result.content,
                }
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result.content})

    async def _invoke_tool(self, name: str, arguments: str) -> MusicToolResult:
        if not self.client:
            return MusicToolResult("音乐服务当前不可用。")
        try:
            payload = json.loads(arguments or "{}")
            if name == "search_tracks":
                query = str(payload.get("query", "")).strip()
                if not query:
                    return MusicToolResult("请提供要搜索的歌曲、歌手或关键词。")
                return await search_tracks(self.client, query)
            if name == "daily_recommendations":
                return await daily_recommendations(self.client)
            if name == "resolve_track":
                return await resolve_track(self.client, str(payload.get("track_id", "")))
            return MusicToolResult(f"未知音乐工具: {name}")
        except Exception as error:
            return MusicToolResult(f"音乐任务失败：{error}")

    @staticmethod
    def _tool_label(name: str) -> str:
        return {
            "search_tracks": "搜索歌曲",
            "daily_recommendations": "每日推荐",
            "resolve_track": "获取歌曲",
        }.get(name, name)
