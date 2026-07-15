from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from AgentBI.src.schemas.toolbox_tts_schema import TtsSynthesisRequest


AUDIO_FORMATS: dict[str, tuple[str, str]] = {
    "mp3": ("audio/mpeg", "mp3"),
    "wav": ("audio/wav", "wav"),
    "pcm": ("audio/L16", "pcm"),
}


@dataclass(slots=True)
class TtsSynthesisResult:
    audio: bytes
    content_type: str
    extension: str
    elapsed_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


class TtsProviderError(RuntimeError):
    def __init__(self, message: str, *, code: str = "upstream_error") -> None:
        super().__init__(message)
        self.code = code


class TtsConfigurationError(TtsProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error")


class TtsValidationError(TtsProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


def audio_format_metadata(audio_format: str) -> tuple[str, str]:
    try:
        return AUDIO_FORMATS[audio_format]
    except KeyError as exc:
        raise TtsValidationError("不支持的音频格式") from exc


def require_configuration(**values: str) -> None:
    missing = [name for name, value in values.items() if not value.strip()]
    if missing:
        raise TtsConfigurationError(f"缺少语音供应商配置：{', '.join(missing)}")


def ensure_model(model: str, allowed_models: set[str]) -> None:
    if model not in allowed_models:
        raise TtsValidationError("当前供应商不支持所选模型")


def ensure_success_status(response: Any) -> None:
    status_code = int(getattr(response, "status_code", 500))
    if 200 <= status_code < 300:
        return
    raise TtsProviderError(f"语音供应商请求失败（HTTP {status_code}）")


class TtsProviderAdapter(Protocol):
    provider_id: str

    def capability(self) -> dict[str, Any]: ...

    async def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult: ...
