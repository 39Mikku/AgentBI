from __future__ import annotations

from typing import Any


def resolve_context_entries(
    entries: list[dict[str, Any]],
    active_path: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve constant and keyword lorebook entries without truncating matches."""

    visible_path = [
        item
        for item in active_path
        if item.get("role") in {"user", "assistant"}
        and item.get("status", "complete") == "complete"
    ]
    resolved: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.get("enabled"):
            continue
        if entry.get("activation_mode") == "constant":
            resolved.append(entry)
            continue
        if entry.get("activation_mode") != "keyword":
            continue
        depth = max(1, int(entry.get("scan_depth", 8)))
        haystack = "\n".join(
            str(item.get("content", "")) for item in visible_path[-depth:]
        ).casefold()
        keywords = (
            str(keyword).strip().casefold()
            for keyword in entry.get("keywords", [])
        )
        if any(keyword and keyword in haystack for keyword in keywords):
            resolved.append(entry)

    return sorted(
        resolved,
        key=lambda item: (
            str(item.get("injection_position", "system_end")),
            -int(item.get("priority", 0)),
            str(item.get("_id", "")),
        ),
    )
