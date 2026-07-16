from __future__ import annotations

import re
from typing import Any

from AgentBI.src.services.gemini_thinking import gemini_request_options, supports_gemini_thinking


_DEEPSEEK_V4_THINKING_MODEL = re.compile(r"(?:^|/)deepseek-v4-(?:flash|pro)(?:-|$)")


def supports_deepseek_v4_thinking(model: str) -> bool:
    return bool(_DEEPSEEK_V4_THINKING_MODEL.search((model or "").strip().lower()))


def model_reasoning_request_options(model: str, thinking_level: str | None) -> dict[str, Any]:
    if supports_gemini_thinking(model):
        return gemini_request_options(model, thinking_level)
    if not supports_deepseek_v4_thinking(model):
        return {}

    level = (thinking_level or "").strip().lower()
    if level == "off":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {
        "reasoning_effort": "max" if level == "high" else "high",
        "extra_body": {"thinking": {"type": "enabled"}},
    }
