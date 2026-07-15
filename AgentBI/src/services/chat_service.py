import json
from collections.abc import Iterable
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


def build_context_messages(messages: list[dict[str, Any]], context_turns: int) -> list[dict[str, str]]:
    selected_messages = messages if context_turns <= 0 else messages[-max(1, context_turns) * 2 :]
    return [
        {"role": item["role"], "content": item["content"]}
        for item in selected_messages
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str)
    ]


def build_active_path_context_messages(active_path: list[dict[str, Any]], context_turns: int) -> list[dict[str, str]]:
    """Build model context from one selected root-to-leaf path in the message DAG."""
    return build_context_messages(active_path, context_turns)


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
        return
    if event_type == "card" and isinstance(event.get("kind"), str) and isinstance(event.get("payload"), dict):
        timeline.append(
            {
                "type": "card",
                "kind": event["kind"],
                "payload": event["payload"],
            }
        )


def format_model_error(error: Exception) -> str:
    message = str(error).strip() or "未知错误"
    return f"模型调用被提供商拒绝：{message}"


class ChatService:
    def __init__(self, repository: SqliteChatRepository):
        self.repository = repository

    def build_context(self, conversation_id: str, user_id: str, context_turns: int) -> list[dict[str, str]]:
        return build_active_path_context_messages(
            self.repository.get_active_path(conversation_id, user_id),
            context_turns,
        )

    def build_context_to_message(
        self,
        conversation_id: str,
        user_id: str,
        message_id: str,
        context_turns: int,
    ) -> list[dict[str, str]]:
        return build_active_path_context_messages(
            self.repository.get_path_to_message(conversation_id, user_id, message_id),
            context_turns,
        )
