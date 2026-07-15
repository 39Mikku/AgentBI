from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.services.bilibili_client import BilibiliClient
from AgentBI.src.tools.bilibili_tools import BilibiliToolResult, get_video_detail, search_videos


class BilibiliAgent:
    system_prompt = (
        "你是哔哩哔哩视频子代理。根据用户意图搜索公开视频，或按 BV 号获取视频详情。"
        "必须通过工具取得真实视频数据，不得编造 BV 号。得到结果后，用一句简短中文说明卡片内容。"
        "你不负责点赞、投币、收藏、评论或账户操作。"
    )

    def __init__(self, client: BilibiliClient | None):
        self.client = client

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_videos",
                    "description": "按标题、UP 主或关键词搜索哔哩哔哩公开视频，最多返回三个候选。",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "视频搜索关键词"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_video_detail",
                    "description": "根据明确的 BV 号获取一个哔哩哔哩视频详情。",
                    "parameters": {
                        "type": "object",
                        "properties": {"bvid": {"type": "string", "description": "完整 BV 号"}},
                        "required": ["bvid"],
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

    async def _invoke_tool(self, name: str, arguments: str) -> BilibiliToolResult:
        if not self.client:
            return BilibiliToolResult("哔哩哔哩服务当前不可用。")
        try:
            payload = json.loads(arguments or "{}")
            if name == "search_videos":
                query = str(payload.get("query", "")).strip()
                if not query:
                    return BilibiliToolResult("请提供视频搜索关键词。")
                return await search_videos(self.client, query)
            if name == "get_video_detail":
                bvid = str(payload.get("bvid", "")).strip()
                if not bvid:
                    return BilibiliToolResult("请提供完整 BV 号。")
                return await get_video_detail(self.client, bvid)
            return BilibiliToolResult(f"未知哔哩哔哩工具：{name}")
        except Exception as error:
            return BilibiliToolResult(f"哔哩哔哩任务失败：{error}")

    @staticmethod
    def _tool_label(name: str) -> str:
        return {
            "search_videos": "搜索哔哩哔哩视频",
            "get_video_detail": "获取哔哩哔哩视频",
        }.get(name, name)

