from __future__ import annotations

import base64
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


class MimoTtsAdapter:
    provider_id = "mimo"
    endpoint = "https://api.xiaomimimo.com/v1/chat/completions"
    models = {"mimo-v2.5-tts"}

    def __init__(self, *, api_key: str, http_client: Any | None = None) -> None:
        self.api_key = api_key.strip()
        self.http_client = http_client

    def capability(self) -> dict[str, Any]:
        return {"id": self.provider_id, "models": sorted(self.models)}

    async def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        require_configuration(MIMO_API_KEY=self.api_key)
        ensure_model(request.model, self.models)
        content_type, extension = audio_format_metadata(request.audio_format)
        style = str(request.parameters.get("style", "")).strip()
        messages: list[dict[str, str]] = []
        if style:
            messages.append({"role": "user", "content": f"请使用以下表达风格生成语音：{style}"})
        messages.append({"role": "assistant", "content": request.text})
        payload = {
            "model": request.model,
            "messages": messages,
            "audio": {"format": request.audio_format, "voice": request.voice_id},
        }
        started = time.perf_counter()
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        if self.http_client is not None:
            response = await self.http_client.post(self.endpoint, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
        ensure_success_status(response)
        body = response.json()
        if body.get("error"):
            raise TtsProviderError(str((body.get("error") or {}).get("message") or "MiMo 语音合成失败"))
        try:
            audio_record = body["choices"][0]["message"]["audio"]
            audio = base64.b64decode(audio_record["data"], validate=True)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise TtsProviderError("MiMo 返回了无法解析的音频") from exc
        if not audio:
            raise TtsProviderError("MiMo 未返回音频")
        return TtsSynthesisResult(
            audio=audio,
            content_type=content_type,
            extension=extension,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            metadata={"audio_id": audio_record.get("id")},
        )
