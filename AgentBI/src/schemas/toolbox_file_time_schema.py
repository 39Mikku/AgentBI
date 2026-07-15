from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


FileTimeOperation = Literal[
    "creation_from_modified",
    "modified_from_creation",
    "filename_to_creation",
    "move_by_creation_range",
]
FileTimeJobStatus = Literal["queued", "running", "completed", "failed"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileTimeRequest(_StrictModel):
    operation: FileTimeOperation
    input_directory: str = Field(min_length=1, max_length=4096)
    output_directory: str | None = Field(default=None, max_length=4096)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("input_directory", "output_directory")
    @classmethod
    def normalize_paths(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("目录不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_operation_fields(self) -> "FileTimeRequest":
        needs_output = self.operation in {"filename_to_creation", "move_by_creation_range"}
        if needs_output and not self.output_directory:
            raise ValueError("当前操作需要输出目录")
        if self.operation == "move_by_creation_range":
            if self.start_date is None or self.end_date is None:
                raise ValueError("按日期移动文件需要开始和结束日期")
            if self.start_date > self.end_date:
                raise ValueError("开始日期不能晚于结束日期")
        return self


class FileTimePreview(_StrictModel):
    operation: FileTimeOperation
    total_files: int = 0
    update_count: int = 0
    move_count: int = 0
    skip_count: int = 0
    examples: list[str] = Field(default_factory=list)


class FileTimeJobResponse(_StrictModel):
    id: str
    operation: FileTimeOperation
    status: FileTimeJobStatus
    total_files: int = 0
    processed_files: int = 0
    updated_count: int = 0
    moved_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None

