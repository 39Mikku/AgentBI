from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TtsProviderId = Literal["minimax", "bailian", "mimo", "volcengine"]
TtsVoiceKind = Literal["builtin", "cloned"]
LiveVoiceTargetModel = Literal[
    "qwen-audio-3.0-realtime-flash",
    "qwen-audio-3.0-realtime-plus",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LiveVoiceEnrollmentRequest(_StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    display_name: str = Field(min_length=1, max_length=80)
    target_model: LiveVoiceTargetModel
    prefix: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    audio_url: str = Field(min_length=1, max_length=4096)

    @field_validator("user_id", "display_name", "prefix", "audio_url")
    @classmethod
    def normalize_enrollment_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("audio_url")
    @classmethod
    def require_https_audio_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise ValueError("参考音频必须使用可公开访问的 HTTPS URL")
        return value


class TtsVoiceCreate(_StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    provider: TtsProviderId
    display_name: str = Field(min_length=1, max_length=80)
    external_voice_id: str = Field(min_length=1, max_length=256)
    voice_kind: TtsVoiceKind = "cloned"
    bound_model: str | None = Field(default=None, max_length=128)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_id", "display_name", "external_voice_id", "bound_model")
    @classmethod
    def strip_voice_fields(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_model_binding(self) -> "TtsVoiceCreate":
        provider_models = {
            "bailian": {
                "cosyvoice-v3.5-plus",
                "cosyvoice-v3.5-flash",
                "qwen-audio-3.0-realtime-flash",
                "qwen-audio-3.0-realtime-plus",
            },
            "volcengine": {"doubao-seed-icl-2.0"},
        }
        allowed_models = provider_models.get(self.provider)
        if self.voice_kind == "cloned" and allowed_models and self.bound_model not in allowed_models:
            raise ValueError("该供应商的复刻音色必须绑定准确的推理模型")
        return self


class TtsVoiceUpdate(_StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bound_model: str | None = Field(default=None, max_length=128)
    provider_metadata: dict[str, Any] | None = None

    @field_validator("display_name", "bound_model")
    @classmethod
    def strip_update_fields(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class TtsVoiceResponse(TtsVoiceCreate):
    id: str
    created_at: str
    updated_at: str


class TtsSynthesisRequest(_StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    provider: TtsProviderId
    model: str = Field(min_length=1, max_length=128)
    voice_id: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=10000)
    audio_format: Literal["mp3", "wav", "pcm"] = "mp3"
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_id", "model", "voice_id", "text")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("字段不能为空")
        return normalized


class TtsCapabilityResponse(_StrictModel):
    providers: list[dict[str, Any]]
