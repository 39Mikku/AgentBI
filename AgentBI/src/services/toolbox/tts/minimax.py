from __future__ import annotations

import time
from typing import Any

import httpx

from AgentBI.src.schemas.toolbox_tts_schema import TtsSynthesisRequest
from AgentBI.src.services.toolbox.tts.base import (
    TtsProviderError,
    TtsSynthesisResult,
    audio_format_metadata,
    ensure_model,
    ensure_success_status,
    require_configuration,
)


class MiniMaxTtsAdapter:
    provider_id = "minimax"
    endpoint = "https://api.minimaxi.com/v1/t2a_v2"
    models = {"speech-2.8-hd", "speech-2.8-turbo"}

    def __init__(self, *, api_key: str, http_client: Any | None = None) -> None:
        self.api_key = api_key.strip()
        self.http_client = http_client

    def capability(self) -> dict[str, Any]:
        return {"id": self.provider_id, "models": sorted(self.models)}

    async def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        require_configuration(MINIMAX_API_KEY=self.api_key)
        ensure_model(request.model, self.models)
        content_type, extension = audio_format_metadata(request.audio_format)
        parameters = request.parameters
        voice_setting: dict[str, Any] = {
            "voice_id": request.voice_id,
            "speed": float(parameters.get("speed", 1.0)),
            "vol": float(parameters.get("volume", 1.0)),
            "pitch": int(parameters.get("pitch", 0)),
        }
        emotion = str(parameters.get("emotion", "")).strip()
        if emotion:
            voice_setting["emotion"] = emotion
        payload = {
            "model": request.model,
            "text": request.text,
            "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": request.audio_format,
                "channel": 1,
            },
            "language_boost": "auto",
        }
        started = time.perf_counter()
        request_kwargs = {
            "headers": {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            "json": payload,
        }
        if self.http_client is not None:
            response = await self.http_client.post(self.endpoint, **request_kwargs)
        else:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.endpoint, **request_kwargs)
        ensure_success_status(response)
        body = response.json()
        base_response = body.get("base_resp") or {}
        if int(base_response.get("status_code", 0)) != 0:
            raise TtsProviderError(str(base_response.get("status_msg") or "MiniMax 语音合成失败"))
        encoded_audio = str((body.get("data") or {}).get("audio") or "")
        try:
            audio = bytes.fromhex(encoded_audio)
        except ValueError as exc:
            raise TtsProviderError("MiniMax 返回了无法解析的音频") from exc
        if not audio:
            raise TtsProviderError("MiniMax 未返回音频")
        return TtsSynthesisResult(
            audio=audio,
            content_type=content_type,
            extension=extension,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            metadata={"trace_id": body.get("trace_id")},
        )
