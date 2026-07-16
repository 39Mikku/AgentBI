import re
from typing import Any, Literal, cast


ThinkingLevel = Literal["low", "medium", "high"]
THINKING_LEVELS: tuple[ThinkingLevel, ...] = ("low", "medium", "high")
_GEMINI_THINKING_MODEL = re.compile(r"(?:^|/)gemini-(?:2\.5|3(?:\.\d+)?)(?:-|$)")
_NON_TEXT_MARKERS = ("image", "imagen", "audio", "tts", "embedding")


def supports_gemini_thinking(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return bool(_GEMINI_THINKING_MODEL.search(normalized)) and not any(
        marker in normalized for marker in _NON_TEXT_MARKERS
    )


def normalize_thinking_level(value: str | None) -> ThinkingLevel:
    normalized = (value or "").strip().lower()
    return cast(ThinkingLevel, normalized) if normalized in THINKING_LEVELS else "medium"


def gemini_request_options(model: str, thinking_level: str | None) -> dict[str, Any]:
    if not supports_gemini_thinking(model):
        return {}
    return {
        "extra_body": {
            "extra_body": {
                "google": {
                    "thinking_config": {
                        "thinking_level": normalize_thinking_level(thinking_level),
                        "include_thoughts": True,
                    }
                }
            }
        }
    }
