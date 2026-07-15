from __future__ import annotations

from typing import Any


def compose_live_instructions(
    role_instructions: str,
    memory: str | None,
    messages: list[dict[str, Any]],
) -> str:
    """Compose persisted context into the session instructions.

    Qwen Audio Realtime currently accepts ``conversation.item.create`` only
    for function-call outputs, so persisted text history cannot be replayed as
    message items. Keeping the generated sections explicit also prevents the
    transcript from being mistaken for new user input.
    """
    sections = [role_instructions.strip()]
    normalized_memory = (memory or "").strip()
    if normalized_memory:
        sections.append(f"<role_memory>\n{normalized_memory}\n</role_memory>")

    history_lines: list[str] = []
    role_labels = {"user": "用户", "assistant": "助手"}
    for message in messages:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "").strip()
        if role in role_labels and content:
            history_lines.append(f"{role_labels[role]}：{content}")
    if history_lines:
        sections.append(
            "<conversation_history>\n"
            "以下是同一角色、同一会话此前已完成的转写，仅作为续聊背景：\n"
            + "\n".join(history_lines)
            + "\n</conversation_history>"
        )
    return "\n\n".join(section for section in sections if section)
