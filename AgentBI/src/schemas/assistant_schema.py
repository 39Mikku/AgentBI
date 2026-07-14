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


class AssistantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    system_prompt: str | None = Field(default=None, max_length=12000)
    capability_ids: list[str] | None = Field(default=None, max_length=30)
    avatar_data_url: str | None = Field(default=None, max_length=2_000_000)
    include_runtime_context: bool | None = None


class AssistantResponse(BaseModel):
    id: str
    user_id: str
    name: str
    system_prompt: str
    capability_ids: list[str] = Field(default_factory=list)
    avatar_data_url: str | None = None
    include_runtime_context: bool = True
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
            is_default=document.get("is_default", False),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )
