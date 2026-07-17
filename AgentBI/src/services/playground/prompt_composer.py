from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from AgentBI.src.services.playground.context_entries import resolve_context_entries


PROMPT_SLOTS = (
    "system_start",
    "system_end",
    "after_last_assistant",
    "before_latest_user",
    "after_latest_user",
)


@dataclass(frozen=True)
class PromptAssembly:
    messages: list[dict[str, str]]
    matched_context_entry_ids: list[str]


class PlaygroundPromptComposer:
    def compose(
        self,
        *,
        profile: dict[str, Any],
        active_path: list[dict[str, Any]],
        modules: list[dict[str, Any]],
        persona: dict[str, Any] | None,
        context_entries: list[dict[str, Any]],
        summary: dict[str, Any] | None,
        previous_state: dict[str, Any] | None,
        context_turns: int = 24,
    ) -> PromptAssembly:
        matched_entries = resolve_context_entries(context_entries, active_path)
        slots = self._collect_slots(
            profile,
            active_path,
            modules,
            persona,
            matched_entries,
            summary,
            previous_state,
        )
        history = self._visible_history(
            active_path,
            profile,
            summary,
            context_turns,
        )
        messages = self._assemble_messages(profile, slots, history)
        return PromptAssembly(
            messages=messages,
            matched_context_entry_ids=[str(item.get("_id", "")) for item in matched_entries],
        )

    def _collect_slots(
        self,
        profile: dict[str, Any],
        active_path: list[dict[str, Any]],
        modules: list[dict[str, Any]],
        persona: dict[str, Any] | None,
        context_entries: list[dict[str, Any]],
        summary: dict[str, Any] | None,
        previous_state: dict[str, Any] | None,
    ) -> dict[str, list[str]]:
        slots = {slot: [] for slot in PROMPT_SLOTS}

        ordered_modules = sorted(
            (item for item in modules if item.get("enabled")),
            key=lambda item: (
                str(item.get("injection_position", "system_end")),
                int(item.get("sort_order", 0)),
                str(item.get("_id", "")),
            ),
        )
        for item in ordered_modules:
            self._append_slot(slots, item.get("injection_position"), str(item.get("content", "")))

        if persona and persona.get("enabled", True):
            fields = [
                ("名称", persona.get("name")),
                ("身份", persona.get("identity_text")),
                ("背景", persona.get("background")),
                ("性格", persona.get("personality")),
                ("初始关系", persona.get("initial_relationship")),
            ]
            content = "\n".join(f"{label}：{value}" for label, value in fields if value)
            if content:
                self._append_slot(
                    slots,
                    persona.get("injection_position"),
                    "[用户人设]\n" + content,
                )

        for entry in context_entries:
            content = str(entry.get("content", "")).strip()
            if content:
                title = str(entry.get("name") or "世界书条目")
                self._append_slot(
                    slots,
                    entry.get("injection_position"),
                    f"[世界书：{title}]\n{content}",
                )

        settings = profile.get("settings") or {}
        summary_settings = settings.get("summary") or {}
        if (
            summary_settings.get("enabled")
            and summary
            and str(summary.get("content") or "").strip()
            and self._valid_summary_boundary(summary, self._history_candidates(active_path))
        ):
            self._append_slot(
                slots,
                summary_settings.get("injection_position")
                or summary.get("injection_position"),
                "[长会话大总结]\n" + str(summary["content"]).strip(),
            )

        state = settings.get("state") or {}
        if state.get("enabled"):
            self._append_slot(
                slots,
                state.get("injection_position"),
                self._state_protocol(state, previous_state),
            )

        action_options = settings.get("action_options") or {}
        if action_options.get("enabled"):
            self._append_slot(
                slots,
                "system_end",
                self._options_protocol(str(action_options.get("style_prompt") or "")),
            )
        return slots

    def _visible_history(
        self,
        active_path: list[dict[str, Any]],
        profile: dict[str, Any],
        summary: dict[str, Any] | None,
        context_turns: int,
    ) -> list[dict[str, str]]:
        candidates = self._history_candidates(active_path)
        settings = profile.get("settings") or {}
        summary_enabled = bool((settings.get("summary") or {}).get("enabled"))
        if summary_enabled and summary and str(summary.get("content") or "").strip():
            boundary = str(summary.get("summarized_through_message_id") or "")
            indexes = {
                str(item.get("_id") or item.get("id") or ""): index
                for index, item in enumerate(candidates)
            }
            if boundary and boundary in indexes:
                candidates = candidates[indexes[boundary] + 1 :]
            elif context_turns > 0:
                candidates = candidates[-max(1, context_turns) * 2 :]
        elif context_turns > 0:
            candidates = candidates[-max(1, context_turns) * 2 :]

        return [
            {"role": str(item["role"]), "content": str(item.get("content") or "")}
            for item in candidates
        ]

    @staticmethod
    def _history_candidates(active_path: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            item
            for item in active_path
            if item.get("role") in {"user", "assistant"}
            and item.get("status", "complete") == "complete"
        ]

    def _assemble_messages(
        self,
        profile: dict[str, Any],
        slots: dict[str, list[str]],
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        system_parts = [
            *slots["system_start"],
            str(profile.get("main_prompt") or "").strip(),
            *slots["system_end"],
        ]
        system_content = "\n\n".join(part for part in system_parts if part)
        if system_content:
            messages.append({"role": "system", "content": system_content})

        latest_user_index = next(
            (index for index in range(len(history) - 1, -1, -1) if history[index]["role"] == "user"),
            None,
        )
        for index, message in enumerate(history):
            if index == latest_user_index:
                messages.extend(self._slot_messages(slots["after_last_assistant"]))
                messages.extend(self._slot_messages(slots["before_latest_user"]))
                messages.append(message)
                messages.extend(self._slot_messages(slots["after_latest_user"]))
            else:
                messages.append(message)
        if latest_user_index is None:
            messages.extend(self._slot_messages(slots["after_last_assistant"]))
            messages.extend(self._slot_messages(slots["before_latest_user"]))
            messages.extend(self._slot_messages(slots["after_latest_user"]))
        return messages

    @staticmethod
    def _slot_messages(contents: list[str]) -> list[dict[str, str]]:
        return [{"role": "system", "content": content} for content in contents if content]

    @staticmethod
    def _append_slot(slots: dict[str, list[str]], slot: Any, content: str) -> None:
        normalized_slot = str(slot or "system_end")
        if normalized_slot not in slots:
            normalized_slot = "system_end"
        normalized_content = content.strip()
        if normalized_content:
            slots[normalized_slot].append(normalized_content)

    @staticmethod
    def _valid_summary_boundary(
        summary: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> bool:
        boundary = str(summary.get("summarized_through_message_id") or "")
        return bool(boundary) and any(
            str(item.get("_id") or item.get("id") or "") == boundary for item in history
        )

    @staticmethod
    def _state_protocol(settings: dict[str, Any], previous_state: dict[str, Any] | None) -> str:
        variables = [
            {
                "key": item.get("key"),
                "type": item.get("type"),
                "label": item.get("label"),
                "description": item.get("description", ""),
                "minimum": item.get("minimum"),
                "maximum": item.get("maximum"),
            }
            for item in settings.get("variables", [])
        ]
        previous = previous_state or {
            str(item.get("key")): item.get("initial_value")
            for item in settings.get("variables", [])
            if item.get("key")
        }
        custom = str(settings.get("update_instructions") or "").strip()
        instruction = (
            "每次回复正文结束后，必须输出角色或世界状态的完整快照。"
            "严格使用 <agentbi_state>{JSON对象}</agentbi_state>，不得使用 Markdown 代码块。"
            "必须保留全部变量，并只根据本轮剧情更新值。这个结构块不会展示给用户，也不会作为普通历史消息回传。"
        )
        if custom:
            instruction += "\n自定义更新要求：" + custom
        return (
            "[状态栏协议]\n"
            + instruction
            + "\n变量定义："
            + json.dumps(variables, ensure_ascii=False)
            + "\n上一轮完整状态："
            + json.dumps(previous, ensure_ascii=False)
            + "\n输出示例：<agentbi_state>{\"key\":\"value\"}</agentbi_state>"
        )

    @staticmethod
    def _options_protocol(style_prompt: str) -> str:
        custom = f"\n选项风格要求：{style_prompt.strip()}" if style_prompt.strip() else ""
        return (
            "[行动选项协议]\n"
            "每次回复正文结束后，必须提供恰好四个可直接推进剧情的行动选项。"
            "严格使用 <agentbi_options>{\"options\":[{\"text\":\"...\"},{\"text\":\"...\"},{\"text\":\"...\"},{\"text\":\"...\"}]}</agentbi_options>。"
            "不得使用 Markdown 代码块，不得在正文中重复列出选项。"
            "自定义风格不得改变标签、JSON 字段或四个选项的固定数量。"
            + custom
        )
