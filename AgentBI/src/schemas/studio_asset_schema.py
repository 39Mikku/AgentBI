from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StudioAssetResponse(BaseModel):
    id: str
    source: Literal["uploaded", "generated"]
    kind: Literal["image", "docx", "video"]
    filename: str
    mime_type: str
    size: int
    url: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    deleted_at: datetime | None = None
    source_conversation_id: str | None = None
    source_conversation_title: str | None = None
    source_message_id: str | None = None

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "StudioAssetResponse":
        return cls(
            id=str(document["_id"]),
            source=document["source"],
            kind=document["kind"],
            filename=document["filename"],
            mime_type=document["mime_type"],
            size=document["size"],
            url=document.get("url"),
            status=document.get("status", "ready"),
            metadata=document.get("metadata", {}),
            created_at=document.get("created_at"),
            deleted_at=document.get("deleted_at"),
            source_conversation_id=document.get("source_conversation_id"),
            source_conversation_title=document.get("source_conversation_title"),
            source_message_id=document.get("source_message_id"),
        )
