from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssistantCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(default="", max_length=12000)
    capability_ids: list[str] = Field(default_factory=list, max_length=30)
    avatar_data_url: str | None = Field(default=None, max_length=2_000_000)
    include_runtime_context: bool = True
    memory_enabled: bool = False
    memory_update_interval: int = Field(default=12, ge=2, le=100)
    history_search_enabled: bool = False
    history_similarity_threshold: float = Field(default=0.58, ge=-1, le=1)
    history_result_limit: int = Field(default=3, ge=1, le=10)
    context_strategy: str = Field(default="window", pattern=r"^(window|compression)$")
    compression_threshold_turns: int = Field(default=12, ge=4, le=200)
    compression_threshold_tokens: int = Field(default=8000, ge=1000, le=500000)
    compression_keep_recent_turns: int = Field(default=4, ge=1, le=32)


class AssistantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    system_prompt: str | None = Field(default=None, max_length=12000)
    capability_ids: list[str] | None = Field(default=None, max_length=30)
    avatar_data_url: str | None = Field(default=None, max_length=2_000_000)
    include_runtime_context: bool | None = None
    memory_enabled: bool | None = None
    memory_update_interval: int | None = Field(default=None, ge=2, le=100)
    history_search_enabled: bool | None = None
    history_similarity_threshold: float | None = Field(default=None, ge=-1, le=1)
    history_result_limit: int | None = Field(default=None, ge=1, le=10)
    context_strategy: str | None = Field(default=None, pattern=r"^(window|compression)$")
    compression_threshold_turns: int | None = Field(default=None, ge=4, le=200)
    compression_threshold_tokens: int | None = Field(default=None, ge=1000, le=500000)
    compression_keep_recent_turns: int | None = Field(default=None, ge=1, le=32)


class AssistantResponse(BaseModel):
    id: str
    user_id: str
    name: str
    system_prompt: str
    capability_ids: list[str] = Field(default_factory=list)
    avatar_data_url: str | None = None
    include_runtime_context: bool = True
    memory_enabled: bool = False
    memory_update_interval: int = 12
    history_search_enabled: bool = False
    history_similarity_threshold: float = 0.58
    history_result_limit: int = 3
    context_strategy: str = "window"
    compression_threshold_turns: int = 12
    compression_threshold_tokens: int = 8000
    compression_keep_recent_turns: int = 4
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "AssistantResponse":
        return cls(
            id=str(document["_id"]),
            user_id=document["user_id"],
            name=document["name"],
            system_prompt=document.get("system_prompt", ""),
            capability_ids=document.get("capability_ids", []),
            avatar_data_url=document.get("avatar_data_url"),
            include_runtime_context=document.get("include_runtime_context", True),
            memory_enabled=document.get("memory_enabled", False),
            memory_update_interval=document.get("memory_update_interval", 12),
            history_search_enabled=document.get("history_search_enabled", False),
            history_similarity_threshold=document.get("history_similarity_threshold", 0.58),
            history_result_limit=document.get("history_result_limit", 3),
            context_strategy=document.get("context_strategy", "window"),
            compression_threshold_turns=document.get("compression_threshold_turns", 12),
            compression_threshold_tokens=document.get("compression_threshold_tokens", 8000),
            compression_keep_recent_turns=document.get("compression_keep_recent_turns", 4),
            is_default=document.get("is_default", False),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )


class AssistantMemoryUpdate(BaseModel):
    summary: str = Field(default="", max_length=30000)


class AssistantMemoryResponse(BaseModel):
    assistant_id: str
    user_id: str
    summary: str = ""
    last_summarized_message_id: str | None = None
    updated_at: datetime | None = None
