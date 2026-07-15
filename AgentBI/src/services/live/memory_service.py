from __future__ import annotations

from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.model_task_service import ModelTaskService


def _format_messages(messages: list[dict[str, Any]]) -> str:
    names = {"user": "user", "assistant": "assistant"}
    return "\n".join(
        f"{names.get(str(item.get('role')), 'message')}: {item.get('content', '')}"
        for item in messages
    )


class LiveMemoryService:
    def __init__(
        self,
        repository: SqliteChatRepository,
        model_tasks: ModelTaskService | Any | None = None,
    ):
        self.repository = repository
        self.model_tasks = model_tasks or ModelTaskService(repository)

    def _messages_between(
        self,
        user_id: str,
        role_id: str,
        marker: str | None,
        until_message_id: str | None,
        force_all: bool = False,
    ) -> list[dict[str, Any]]:
        messages = self.repository.list_live_role_messages(user_id, role_id)
        ids = [item["id"] for item in messages]
        if not force_all and marker in ids:
            messages = messages[ids.index(marker) + 1 :]
        if until_message_id:
            selected_ids = [item["id"] for item in messages]
            if until_message_id in selected_ids:
                messages = messages[: selected_ids.index(until_message_id) + 1]
        return messages

    async def _update(
        self,
        user_id: str,
        role_id: str,
        until_message_id: str | None,
        force_all: bool,
    ) -> dict[str, Any] | None:
        role = self.repository.get_live_role(role_id, user_id)
        if not role or not role["memory_enabled"]:
            return None
        memory = self.repository.get_live_role_memory(user_id, role_id)
        messages = self._messages_between(
            user_id,
            role_id,
            memory.get("last_message_id"),
            until_message_id,
            force_all,
        )
        if not messages:
            return memory
        summary = await self.model_tasks.complete(
            user_id,
            "memory",
            (
                "Maintain concise durable memory for this user and voice role. "
                "Keep stable preferences, relationships, goals, promises and important facts. "
                "Merge duplicates and remove transient chatter. Return only the updated memory."
            ),
            (
                f"Existing memory:\n{memory.get('content') or '(empty)'}"
                f"\n\nNew completed call material:\n{_format_messages(messages)}"
            ),
        )
        if not summary:
            return None
        return self.repository.save_live_role_memory(
            user_id,
            role_id,
            summary,
            messages[-1]["id"],
        )

    async def update_after_call(
        self,
        user_id: str,
        role_id: str,
        last_message_id: str | None,
    ) -> dict[str, Any] | None:
        return await self._update(
            user_id,
            role_id,
            last_message_id,
            force_all=False,
        )

    async def refresh(self, user_id: str, role_id: str) -> dict[str, Any] | None:
        return await self._update(
            user_id,
            role_id,
            until_message_id=None,
            force_all=True,
        )
