from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from AgentBI.src.services.playground.state_templates import normalize_state_snapshot


@dataclass(frozen=True)
class StructuredTailResult:
    visible_tail: str
    state_snapshot: dict[str, Any] | None
    action_options: list[dict[str, str]] | None
    errors: list[str]


class StructuredTailParser:
    STATE_OPEN = "<agentbi_state>"
    STATE_CLOSE = "</agentbi_state>"
    OPTIONS_OPEN = "<agentbi_options>"
    OPTIONS_CLOSE = "</agentbi_options>"

    def __init__(
        self,
        *,
        expect_state: bool,
        expect_options: bool,
        variable_definitions: list[dict[str, Any]] | None = None,
        previous_state: dict[str, Any] | None = None,
    ):
        self.expect_state = expect_state
        self.expect_options = expect_options
        self.variable_definitions = variable_definitions or []
        self.previous_state = previous_state or {}
        self._buffer = ""
        self._capturing = False

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        if not self.expect_state and not self.expect_options:
            return chunk

        self._buffer += chunk
        if self._capturing:
            return ""

        open_tags = []
        if self.expect_state:
            open_tags.append(self.STATE_OPEN)
        if self.expect_options:
            open_tags.append(self.OPTIONS_OPEN)
        positions = [position for tag in open_tags if (position := self._buffer.find(tag)) >= 0]
        if positions:
            position = min(positions)
            visible, self._buffer = self._buffer[:position], self._buffer[position:]
            self._capturing = True
            return visible

        keep = max(len(tag) for tag in open_tags) - 1
        if len(self._buffer) <= keep:
            return ""
        visible, self._buffer = self._buffer[:-keep], self._buffer[-keep:]
        return visible

    def finish(self) -> StructuredTailResult:
        if not self.expect_state and not self.expect_options:
            return StructuredTailResult("", None, None, [])
        if not self._capturing:
            visible = self._buffer
            self._buffer = ""
            return StructuredTailResult(visible, None, None, [])

        errors: list[str] = []
        state: dict[str, Any] | None = None
        options: list[dict[str, str]] | None = None
        if self.expect_state:
            raw_state = self._extract(self.STATE_OPEN, self.STATE_CLOSE, "状态", errors)
            if raw_state is not None:
                try:
                    parsed_state = json.loads(raw_state)
                    if not isinstance(parsed_state, dict):
                        raise ValueError("状态必须是 JSON 对象")
                    state = normalize_state_snapshot(
                        self.variable_definitions,
                        self.previous_state,
                        parsed_state,
                    )
                except (json.JSONDecodeError, ValueError, TypeError) as error:
                    errors.append(f"状态协议无效：{error}")

        if self.expect_options:
            raw_options = self._extract(self.OPTIONS_OPEN, self.OPTIONS_CLOSE, "行动选项", errors)
            if raw_options is not None:
                try:
                    parsed_options = json.loads(raw_options)
                    if isinstance(parsed_options, dict):
                        parsed_options = parsed_options.get("options")
                    options = self._normalize_options(parsed_options)
                except (json.JSONDecodeError, ValueError, TypeError) as error:
                    errors.append(f"行动选项协议无效：{error}")

        self._buffer = ""
        return StructuredTailResult("", state, options, errors)

    def _extract(
        self,
        opening: str,
        closing: str,
        label: str,
        errors: list[str],
    ) -> str | None:
        start = self._buffer.find(opening)
        if start < 0:
            errors.append(f"未返回{label}协议")
            return None
        start += len(opening)
        end = self._buffer.find(closing, start)
        if end < 0:
            errors.append(f"{label}协议未闭合")
            return None
        return self._buffer[start:end].strip()

    @staticmethod
    def _normalize_options(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list) or len(value) != 4:
            raise ValueError("行动选项必须恰好四个")
        result: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("每个行动选项必须是对象")
            text = str(item.get("text") or "").strip()
            if not text:
                raise ValueError("行动选项文本不能为空")
            result.append({"text": text})
        return result
