import json
from collections.abc import Iterable
from typing import Any

from AgentBI.src.repositories.chat_repository import ChatRepository


def build_context_messages(messages: list[dict[str, Any]], context_turns: int) -> list[dict[str, str]]:
    limit = max(1, context_turns) * 2
    return [
        {"role": item["role"], "content": item["content"]}
        for item in messages[-limit:]
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
    ]


def encode_sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def append_timeline_event(timeline: list[dict[str, Any]], event_type: str, event: dict[str, Any]) -> None:
    """Persist the exact event order while coalescing adjacent streamed text."""
    content = event.get("content")
    if event_type in {"delta", "reasoning_summary"} and content:
        if timeline and timeline[-1].get("type") == event_type:
            timeline[-1]["content"] += content
        else:
            timeline.append({"type": event_type, "content": content})
        return
    if event_type in {"tool_started", "tool_finished"}:
        entry = {"type": event_type, "tool": event.get("tool", "工具")}
        if content:
            entry["content"] = content
        timeline.append(entry)


def format_model_error(error: Exception) -> str:
    message = str(error).strip() or "未知错误"
    return f"模型调用被提供商拒绝：{message}"


class ChatService:
    def __init__(self, repository: ChatRepository):
        self.repository = repository

    def build_context(self, conversation_id: str, user_id: str, context_turns: int) -> list[dict[str, str]]:
        return build_context_messages(self.repository.list_messages(conversation_id, user_id), context_turns)
