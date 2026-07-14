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
    return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\\n\\n"


class ChatService:
    def __init__(self, repository: ChatRepository):
        self.repository = repository

    def build_context(self, conversation_id: str, user_id: str, context_turns: int) -> list[dict[str, str]]:
        return build_context_messages(self.repository.list_messages(conversation_id, user_id), context_turns)

