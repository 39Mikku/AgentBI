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


class BailianCosyVoiceAdapter:
    provider_id = "bailian"
    models = {"cosyvoice-v3.5-plus", "cosyvoice-v3.5-flash"}

    def __init__(self, *, api_key: str, workspace_id: str, http_client: Any | None = None) -> None:
        self.api_key = api_key.strip()
        self.workspace_id = workspace_id.strip()
        self.http_client = http_client

    @property
    def endpoint(self) -> str:
        return (
            f"https://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/api/v1/services/audio/tts/SpeechSynthesizer"
        )

    def capability(self) -> dict[str, Any]:
        return {"id": self.provider_id, "models": sorted(self.models)}

    async def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        require_configuration(DASHSCOPE_API_KEY=self.api_key, DASHSCOPE_WORKSPACE_ID=self.workspace_id)
        ensure_model(request.model, self.models)
        content_type, extension = audio_format_metadata(request.audio_format)
        parameters = request.parameters
        input_data: dict[str, Any] = {
            "text": request.text,
            "voice": request.voice_id,
            "format": request.audio_format,
            "sample_rate": 24000,
            "volume": int(parameters.get("volume", 50)),
            "rate": float(parameters.get("speech_rate", 1.0)),
            "pitch": float(parameters.get("pitch", 1.0)),
        }
        instruction = str(parameters.get("instruction", "")).strip()
        if instruction:
            input_data["instruction"] = instruction
        payload = {"model": request.model, "input": input_data}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        started = time.perf_counter()
        if self.http_client is not None:
            response = await self.http_client.post(self.endpoint, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
        ensure_success_status(response)
        body = response.json()
        if body.get("code"):
            raise TtsProviderError(str(body.get("message") or "百炼语音合成失败"))
        audio_record = ((body.get("output") or {}).get("audio") or {})
        audio_url = str(audio_record.get("url") or "")
        if not audio_url:
            raise TtsProviderError("百炼未返回音频地址")
        if self.http_client is not None:
            audio_response = await self.http_client.get(audio_url)
        else:
            async with httpx.AsyncClient(timeout=90) as client:
                audio_response = await client.get(audio_url)
        ensure_success_status(audio_response)
        audio = bytes(audio_response.content)
        if not audio:
            raise TtsProviderError("百炼返回的音频为空")
        return TtsSynthesisResult(
            audio=audio,
            content_type=content_type,
            extension=extension,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            metadata={"request_id": body.get("request_id"), "audio_id": audio_record.get("id")},
        )
