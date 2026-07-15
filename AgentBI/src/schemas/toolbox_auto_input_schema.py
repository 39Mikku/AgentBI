from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AutoInputStatus = Literal["countdown", "running", "completed", "cancelled", "failed"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutoInputCreate(_StrictModel):
    text: str = Field(min_length=1, max_length=100_000)
    delay_seconds: float = Field(default=0.05, ge=0, le=2)
    countdown_seconds: int = Field(default=5, ge=1, le=30)

    @field_validator("text")
    @classmethod
    def require_visible_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("自动输入文本不能为空")
        return value


class AutoInputJobResponse(_StrictModel):
    id: str
    status: AutoInputStatus
    delay_seconds: float
    countdown_seconds: int
    countdown_remaining: int
    total_characters: int
    typed_characters: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

