from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ProviderProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(min_length=1, max_length=1000)
    default_model: str | None = Field(default=None, max_length=200)


class ProviderProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: str | None = Field(default=None, min_length=8, max_length=500)
    api_key: str | None = Field(default=None, min_length=1, max_length=1000)
    default_model: str | None = Field(default=None, max_length=200)


class ProviderProfileResponse(BaseModel):
    id: str
    name: str
    base_url: str
    default_model: str | None = None
    available_models: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ProviderProfileResponse":
        return cls(
            id=str(document["_id"]),
            name=document["name"],
            base_url=document["base_url"],
            default_model=document.get("default_model"),
            available_models=document.get("available_models", []),
            created_at=document.get("created_at"),
            updated_at=document.get("updated_at"),
        )

