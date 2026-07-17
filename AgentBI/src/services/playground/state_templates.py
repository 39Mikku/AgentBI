from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal


StateTemplateId = Literal["adventure", "nurturing", "romance", "custom"]


STATE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "adventure": [
        {"key": "hp", "type": "progress", "label": "生命", "minimum": 0, "maximum": 100},
        {"key": "stamina", "type": "progress", "label": "体力", "minimum": 0, "maximum": 100},
        {"key": "location", "type": "text", "label": "地点"},
        {"key": "world_time", "type": "text", "label": "时间"},
        {"key": "weather", "type": "text", "label": "天气"},
        {"key": "current_goal", "type": "text", "label": "当前目标"},
        {"key": "danger_level", "type": "progress", "label": "危险度", "minimum": 0, "maximum": 100},
        {"key": "party", "type": "list", "label": "队伍"},
        {"key": "key_items", "type": "list", "label": "关键物品"},
        {"key": "recent_event", "type": "text", "label": "近期事件"},
    ],
    "nurturing": [
        {"key": "date_phase", "type": "text", "label": "日期阶段"},
        {"key": "energy", "type": "progress", "label": "精力", "minimum": 0, "maximum": 100},
        {"key": "mood", "type": "text", "label": "心情"},
        {"key": "health", "type": "progress", "label": "健康", "minimum": 0, "maximum": 100},
        {"key": "stats", "type": "list", "label": "能力"},
        {"key": "plans", "type": "list", "label": "计划"},
        {"key": "goals", "type": "list", "label": "目标"},
        {"key": "unlocks", "type": "list", "label": "已解锁"},
        {"key": "recent_changes", "type": "text", "label": "近期变化"},
    ],
    "romance": [
        {"key": "scene", "type": "text", "label": "场景"},
        {"key": "relationship_stage", "type": "text", "label": "关系阶段"},
        {"key": "affection", "type": "progress", "label": "好感", "minimum": 0, "maximum": 100},
        {"key": "trust", "type": "progress", "label": "信任", "minimum": 0, "maximum": 100},
        {"key": "emotion", "type": "text", "label": "情绪"},
        {"key": "relationship_status", "type": "text", "label": "关系状态"},
        {"key": "important_memory", "type": "text", "label": "重要记忆"},
        {"key": "recent_relation_change", "type": "text", "label": "近期关系变化"},
    ],
    "custom": [],
}


def list_state_templates() -> dict[str, list[dict[str, Any]]]:
    """Return a defensive copy suitable for API responses and editors."""

    return deepcopy(STATE_TEMPLATES)


def validate_state_variables(
    template: StateTemplateId | str,
    variables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep preset keys/types stable while allowing presentation overrides and extras.

    Missing preset variables are restored from the template. This makes deletion of a
    protected key impossible without forcing clients to resend an unchanged full list.
    """

    if template not in STATE_TEMPLATES:
        raise ValueError("未知的状态栏模板")

    protected = {item["key"]: item for item in STATE_TEMPLATES[template]}
    incoming: dict[str, dict[str, Any]] = {}
    incoming_order: list[str] = []
    for raw in variables:
        item = dict(raw)
        key = str(item.get("key") or "").strip()
        if not key:
            raise ValueError("状态变量 key 不能为空")
        if key in incoming:
            raise ValueError(f"状态变量 key 重复：{key}")
        expected = protected.get(key)
        if expected and item.get("type") != expected["type"]:
            raise ValueError(f"预置变量 {key} 的类型不能修改")
        incoming[key] = item
        incoming_order.append(key)

    normalized: list[dict[str, Any]] = []
    for default in STATE_TEMPLATES[template]:
        override = incoming.pop(default["key"], None)
        normalized.append({**deepcopy(default), **(override or {})})

    for key in incoming_order:
        if key in incoming:
            normalized.append(incoming[key])
    return normalized


def normalize_state_snapshot(
    variable_definitions: list[dict[str, Any]],
    previous_snapshot: dict[str, Any] | None,
    candidate_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize model values against the user-owned variable schema."""

    previous = previous_snapshot if isinstance(previous_snapshot, dict) else {}
    candidate = candidate_snapshot if isinstance(candidate_snapshot, dict) else {}
    result: dict[str, Any] = {}
    for definition in variable_definitions:
        key = str(definition.get("key") or "")
        if not key:
            continue
        fallback = previous.get(key, definition.get("initial_value"))
        raw = candidate.get(key, fallback)
        value_type = definition.get("type", "text")

        if value_type in {"progress", "number"}:
            value = _normalize_number(raw)
            if value is None:
                value = _normalize_number(fallback)
            if value is not None:
                minimum = _normalize_number(definition.get("minimum"))
                maximum = _normalize_number(definition.get("maximum"))
                if minimum is not None:
                    value = max(minimum, value)
                if maximum is not None:
                    value = min(maximum, value)
                if float(value).is_integer():
                    value = int(value)
            result[key] = value
        elif value_type in {"list", "tags"}:
            result[key] = _normalize_list(raw, fallback)
        else:
            result[key] = raw if isinstance(raw, str) else (
                fallback if isinstance(fallback, str) else ""
            )
    return result


def _normalize_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_list(value: Any, fallback: Any) -> list[str]:
    selected = value if isinstance(value, (str, list)) else fallback
    if isinstance(selected, str):
        stripped = selected.strip()
        return [stripped] if stripped else []
    if isinstance(selected, list):
        return [str(item).strip() for item in selected if isinstance(item, str) and item.strip()]
    return []
