from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=120)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.7, ge=0, le=2)
    context_turns: int = Field(default=8, ge=1, le=50)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_turns: int | None = Field(default=None, ge=1, le=50)


class ChatPreferencesUpdate(BaseModel):
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.7, ge=0, le=2)
    context_turns: int = Field(default=8, ge=1, le=50)


class ChatPreferencesResponse(ChatPreferencesUpdate):
    user_id: str

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ChatPreferencesResponse":
        return cls(
            user_id=document["user_id"],
            provider_id=document.get("provider_id"),
            model=document.get("model"),
            temperature=document.get("temperature", 0.7),
            context_turns=document.get("context_turns", 8),
        )


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    provider_id: str | None = None
    model: str | None = None
    temperature: float = 0.7
    context_turns: int = 8
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_message_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ConversationResponse":
        return cls(
            id=str(document["_id"]),
            user_id=document["user_id"],
            title=document["title"],
            provider_id=document.get("provider_id"),
            model=document.get("model"),
            temperature=document.get("temperature", 0.7),
            context_turns=document.get("context_turns", 8),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
            last_message_at=document.get("last_message_at"),
        )


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    reasoning_summary: str | None = None
    tool_events: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["complete", "streaming", "error"] = "complete"
    created_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ChatMessageResponse":
        return cls(
            id=str(document["_id"]),
            conversation_id=str(document["conversation_id"]),
            user_id=document["user_id"],
            role=document["role"],
            content=document["content"],
            reasoning_summary=document.get("reasoning_summary"),
            tool_events=document.get("tool_events", []),
            timeline=document.get("timeline", []),
            status=document.get("status", "complete"),
            created_at=document.get("created_at"),
        )


class ChatStreamRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    conversation_id: str
    content: str = Field(min_length=1, max_length=30000)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_turns: int | None = Field(default=None, ge=1, le=50)
    user_name: str | None = Field(default=None, max_length=120)
    locale: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)
