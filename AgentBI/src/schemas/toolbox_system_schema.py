from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectorySelectionRequest(_StrictModel):
    title: str = Field(default="选择目录", min_length=1, max_length=80)
    initial_directory: str | None = Field(default=None, max_length=4096)

    @field_validator("title", "initial_directory")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DirectorySelectionResponse(_StrictModel):
    path: str | None
    cancelled: bool

