from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoegirlFetchRequest(_StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    name: str = Field(min_length=1, max_length=200)

    @field_validator("user_id", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("字段不能为空")
        return normalized


class MoegirlArtifactSummaryResponse(_StrictModel):
    id: str = Field(pattern=r"^[a-f0-9]{24}$")
    requested_name: str
    title: str
    source_url: str
    fetched_at: str
    updated_at: str
    character_count: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MoegirlArtifactDocumentResponse(MoegirlArtifactSummaryResponse):
    markdown: str


class MoegirlFetchResponse(_StrictModel):
    kind: Literal["saved", "disambiguation"]
    title: str
    source_url: str
    markdown: str
    message: str
    artifact: MoegirlArtifactSummaryResponse | None

    @model_validator(mode="after")
    def validate_kind_artifact_invariant(self) -> "MoegirlFetchResponse":
        if self.kind == "saved" and self.artifact is None:
            raise ValueError("saved 结果必须包含 artifact")
        if self.kind == "disambiguation" and self.artifact is not None:
            raise ValueError("disambiguation 结果不能包含 artifact")
        return self
