from __future__ import annotations

import re
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.model_task_service import ModelTaskService


DEFAULT_LIVE_TITLES = {"新语音会话", "未命名会话"}


class LiveTitleService:
    def __init__(
        self,
        repository: SqliteChatRepository,
        model_tasks: ModelTaskService | Any | None = None,
    ):
        self.repository = repository
        self.model_tasks = model_tasks or ModelTaskService(repository)

    def _first_complete_pair(
        self, conversation_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        pending_user: dict[str, Any] | None = None
        for message in self.repository.list_live_messages(conversation_id, user_id):
            if message.get("status") != "complete":
                continue
            if message.get("role") == "user":
                pending_user = message
            elif message.get("role") == "assistant" and pending_user:
                return [pending_user, message]
        return []

    async def generate_after_call(
        self,
        user_id: str,
        role_id: str,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        conversation = self.repository.get_live_conversation(conversation_id, user_id)
        if (
            not conversation
            or conversation.get("role_id") != role_id
            or conversation.get("title") not in DEFAULT_LIVE_TITLES
        ):
            return None
        pair = self._first_complete_pair(conversation_id, user_id)
        if len(pair) < 2:
            return None
        prompt = "\n".join(
            f"{message['role']}: {message['content']}" for message in pair
        )
        title = await self.model_tasks.complete(
            user_id,
            "title",
            (
                "Create a concise conversation title in the user's language. "
                "Return only the title, 8 to 18 Chinese characters or equivalent "
                "length, without quotes or punctuation at the end."
            ),
            prompt,
        )
        if not title:
            return None
        normalized = re.sub(
            r"^[\s\"'《》]+|[\s\"'。！!？?《》]+$", "", title
        )[:60]
        if not normalized:
            return None
        latest = self.repository.get_live_conversation(conversation_id, user_id)
        if not latest or latest.get("title") not in DEFAULT_LIVE_TITLES:
            return None
        return self.repository.update_live_conversation(
            conversation_id, user_id, {"title": normalized}
        )
