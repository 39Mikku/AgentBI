from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from AgentBI.src.schemas.studio_asset_schema import StudioAssetResponse


class ConversationCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=120)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.7, ge=0, le=2)
    context_turns: int = Field(default=8, ge=0, le=128)
    assistant_id: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_turns: int | None = Field(default=None, ge=0, le=128)


class ChatPreferencesUpdate(BaseModel):
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.7, ge=0, le=2)
    context_turns: int = Field(default=8, ge=0, le=128)
    thinking_level: Literal["low", "medium", "high"] = "medium"


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
            thinking_level=document.get("thinking_level", "medium"),
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
    active_message_id: str | None = None
    source_thread_id: str | None = None
    source_message_id: str | None = None
    assistant_id: str | None = None

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
            active_message_id=str(document["active_message_id"]) if document.get("active_message_id") else None,
            source_thread_id=str(document["source_thread_id"]) if document.get("source_thread_id") else None,
            source_message_id=str(document["source_message_id"]) if document.get("source_message_id") else None,
            assistant_id=str(document["assistant_id"]) if document.get("assistant_id") else None,
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
    parent_id: str | None = None
    sibling_count: int = 1
    sibling_index: int = 0
    version_ids: list[str] = Field(default_factory=list)
    model_snapshot: dict[str, Any] = Field(default_factory=dict)
    assets: list[StudioAssetResponse] = Field(default_factory=list)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ChatMessageResponse":
        return cls(
            id=str(document["_id"]),
            conversation_id=str(document.get("conversation_id") or document["thread_id"]),
            user_id=document["user_id"],
            role=document["role"],
            content=document["content"],
            reasoning_summary=document.get("reasoning_summary"),
            tool_events=document.get("tool_events", []),
            timeline=document.get("timeline", []),
            status=document.get("status", "complete"),
            created_at=document.get("created_at"),
            parent_id=str(document["parent_id"]) if document.get("parent_id") else None,
            sibling_count=document.get("sibling_count", 1),
            sibling_index=document.get("sibling_index", 0),
            version_ids=document.get("version_ids", []),
            model_snapshot=document.get("model_snapshot", {}),
            assets=[StudioAssetResponse.from_document(item) for item in document.get("assets", [])],
        )


class ConversationBranchCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    source_message_id: str
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ActiveMessageUpdate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)


class MessageEditRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=30000)


class ChatStreamRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    conversation_id: str
    content: str = Field(default="", max_length=30000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_turns: int | None = Field(default=None, ge=0, le=128)
    thinking_level: Literal["low", "medium", "high"] = "medium"
    user_name: str | None = Field(default=None, max_length=120)
    locale: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def require_content_or_attachment(self):
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError("消息内容和附件不能同时为空")
        return self


class ChatRetryStreamRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    conversation_id: str
    message_id: str
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    context_turns: int | None = Field(default=None, ge=0, le=128)
    thinking_level: Literal["low", "medium", "high"] = "medium"
    user_name: str | None = Field(default=None, max_length=120)
    locale: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)


class ChatEditStreamRequest(ChatRetryStreamRequest):
    content: str = Field(min_length=1, max_length=30000)
