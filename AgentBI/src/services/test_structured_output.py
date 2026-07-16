from __future__ import annotations

import json
from json import JSONDecodeError
from typing import TypeVar

from pydantic import BaseModel, ValidationError


MAX_STRUCTURED_OUTPUT_BYTES = 256 * 1024
T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(ValueError):
    """The upstream text is not one safe, schema-valid JSON object."""

    def __init__(self, message: str, *, safe_detail: bool = False):
        super().__init__(message)
        self.safe_detail = safe_detail


class StructuredOutputTooLargeError(StructuredOutputError):
    """The upstream text exceeds the local structured-output byte limit."""


def _scan_top_level_object_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    object_start: int | None = None
    object_depth = 0
    array_depth = 0
    in_string = False
    escaped = False

    for index, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if object_depth:
            if character == "{":
                object_depth += 1
            elif character == "}":
                object_depth -= 1
                if object_depth == 0:
                    if object_start is None:  # pragma: no cover - defensive invariant
                        raise StructuredOutputError("invalid structured output")
                    spans.append((object_start, index + 1))
                    object_start = None
            continue
        if character == "[":
            array_depth += 1
        elif character == "]" and array_depth:
            array_depth -= 1
        elif character == "{" and array_depth == 0:
            object_start = index
            object_depth = 1

    if object_depth:
        raise StructuredOutputError("unbalanced JSON object")
    return spans


def _strip_adjacent_code_fence(text: str, *, before_object: bool) -> str:
    stripped = text.strip()
    if before_object:
        lowered = stripped.lower()
        for marker in ("```json", "```"):
            if lowered.endswith(marker):
                return stripped[: -len(marker)].strip()
    elif stripped.startswith("```"):
        return stripped[3:].strip()
    return stripped


def _is_complete_json_value(text: str) -> bool:
    if not text:
        return False
    try:
        json.loads(text)
    except (JSONDecodeError, TypeError):
        return False
    return True


def _safe_error_location(location: tuple[object, ...]) -> str:
    segments: list[str] = []
    for segment in location:
        if isinstance(segment, int):
            segments.append(str(segment))
        elif (
            isinstance(segment, str)
            and segment.isascii()
            and 0 < len(segment) <= 64
            and all(character.isalnum() or character == "_" for character in segment)
        ):
            segments.append(segment)
        else:
            segments.append("?")
    return ".".join(segments) or "root"


def safe_validation_summary(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        error_count = exc.error_count()
        noun = "error" if error_count == 1 else "errors"
        details = []
        for error in exc.errors(include_url=False)[:8]:
            location = _safe_error_location(tuple(error.get("loc", ())))
            error_type = str(error.get("type", "validation_error"))
            if not error_type.isascii() or not all(
                character.isalnum() or character == "_" for character in error_type
            ):
                error_type = "validation_error"
            details.append(f"{location} [{error_type}]")
        suffix = f": {'; '.join(details)}" if details else ""
        summary = f"schema validation failed ({error_count} {noun}){suffix}"
    elif isinstance(exc, JSONDecodeError):
        summary = "invalid JSON (1 error)"
    elif isinstance(exc, StructuredOutputTooLargeError):
        summary = "structured output exceeds 256 KiB"
    elif isinstance(exc, StructuredOutputError):
        summary = str(exc) if exc.safe_detail else "structured output is invalid"
    else:
        summary = "structured output validation failed"
    return " ".join(summary.split())[:400]


def parse_structured_object(text: str, model_type: type[T]) -> T:
    if not isinstance(text, str):
        raise StructuredOutputError("structured output must be text")
    if len(text.encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
        raise StructuredOutputTooLargeError("structured output exceeds 256 KiB")

    spans = _scan_top_level_object_spans(text)
    if len(spans) != 1:
        raise StructuredOutputError("structured output must contain exactly one top-level object")
    start, end = spans[0]
    prefix = _strip_adjacent_code_fence(text[:start], before_object=True)
    suffix = _strip_adjacent_code_fence(text[end:], before_object=False)
    if _is_complete_json_value(prefix) or _is_complete_json_value(suffix):
        raise StructuredOutputError("structured output contains an additional JSON value")

    try:
        payload = json.loads(text[start:end])
        return model_type.model_validate(payload)
    except (JSONDecodeError, ValidationError) as exc:
        raise StructuredOutputError(
            safe_validation_summary(exc), safe_detail=True
        ) from exc
