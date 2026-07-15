from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.live.context import compose_live_instructions
from AgentBI.src.services.live.protocol import LiveEvent
from AgentBI.src.services.live.qwen_audio_realtime import LiveSessionConfig


class LiveWorkspaceError(ValueError):
    pass


class LiveCallRecorder:
    def __init__(
        self,
        repository: SqliteChatRepository,
        user_id: str,
        role_id: str,
        conversation_id: str,
    ):
        self.repository = repository
        self.user_id = user_id
        self.role_id = role_id
        self.conversation_id = conversation_id
        self._assistant_buffers: dict[str, str] = {}
        self._active_assistant_item_id: str | None = None
        self._complete_message_ids: list[str] = []

    @property
    def has_new_complete_messages(self) -> bool:
        return bool(self._complete_message_ids)

    @property
    def last_complete_message_id(self) -> str | None:
        return self._complete_message_ids[-1] if self._complete_message_ids else None

    def _persist(
        self,
        event: LiveEvent,
        item_id: str,
        role: str,
        content: str,
        status: str,
    ) -> LiveEvent:
        normalized = content.strip()
        if not normalized:
            return event
        message = self.repository.append_live_message(
            self.conversation_id,
            self.user_id,
            self.role_id,
            role,
            normalized,
            item_id,
            status,
        )
        if status == "complete" and message["id"] not in self._complete_message_ids:
            self._complete_message_ids.append(message["id"])
        return LiveEvent(
            event.type,
            {
                **event.payload,
                "message_id": message["id"],
                "conversation_id": self.conversation_id,
                "status": status,
            },
        )

    async def handle(self, event: LiveEvent) -> LiveEvent:
        if event.type == "assistant.transcript.delta":
            item_id = str(event.payload.get("item_id") or "")
            if item_id:
                self._active_assistant_item_id = item_id
                self._assistant_buffers[item_id] = (
                    self._assistant_buffers.get(item_id, "")
                    + str(event.payload.get("delta") or "")
                )
            return event
        if event.type == "user.transcript.final":
            item_id = str(event.payload.get("item_id") or "")
            return self._persist(
                event,
                item_id,
                "user",
                str(event.payload.get("transcript") or ""),
                "complete",
            )
        if event.type == "assistant.transcript.final":
            item_id = str(event.payload.get("item_id") or self._active_assistant_item_id or "")
            content = str(event.payload.get("transcript") or self._assistant_buffers.get(item_id, ""))
            self._assistant_buffers.pop(item_id, None)
            if self._active_assistant_item_id == item_id:
                self._active_assistant_item_id = None
            return self._persist(event, item_id, "assistant", content, "complete")
        if event.type == "response.interrupted" and self._active_assistant_item_id:
            item_id = self._active_assistant_item_id
            content = self._assistant_buffers.pop(item_id, "")
            self._active_assistant_item_id = None
            return self._persist(event, item_id, "assistant", content, "interrupted")
        return event


@dataclass(frozen=True)
class PreparedLiveCall:
    user_id: str
    role: dict[str, Any]
    preferences: dict[str, Any]
    conversation: dict[str, Any]
    config: LiveSessionConfig
    recorder: LiveCallRecorder


class LiveConversationService:
    def __init__(self, repository: SqliteChatRepository):
        self.repository = repository

    def prepare(
        self,
        user_id: str,
        role_id: str,
        conversation_id: str | None,
    ) -> PreparedLiveCall:
        role = self.repository.get_live_role(role_id, user_id)
        if not role:
            raise LiveWorkspaceError("Live role not found")
        conversation = (
            self.repository.get_live_conversation(conversation_id, user_id)
            if conversation_id
            else self.repository.create_live_conversation(
                {"user_id": user_id, "role_id": role_id}
            )
        )
        if not conversation or conversation["role_id"] != role_id:
            raise LiveWorkspaceError("Live conversation not found for role")
        preferences = self.repository.get_live_preferences(user_id)
        replay = self.repository.list_live_replay_messages(
            conversation["id"],
            user_id,
            int(preferences["history_context_turns"]),
        )
        memory = (
            self.repository.get_live_role_memory(user_id, role_id)["content"]
            if role["memory_enabled"]
            else None
        )
        recorder = LiveCallRecorder(
            self.repository,
            user_id,
            role_id,
            conversation["id"],
        )
        return PreparedLiveCall(
            user_id=user_id,
            role=role,
            preferences=preferences,
            conversation=conversation,
            config=LiveSessionConfig(
                model=preferences["model"],
                voice=role["voice"],
                instructions=compose_live_instructions(
                    role["instructions"], memory, replay
                ),
                max_history_turns=preferences["max_history_turns"],
            ),
            recorder=recorder,
        )
