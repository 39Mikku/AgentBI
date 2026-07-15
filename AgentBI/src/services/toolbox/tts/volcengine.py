from __future__ import annotations

import base64
import json
import time
import uuid
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


class VolcengineTtsAdapter:
    provider_id = "volcengine"
    endpoint = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    models = {"doubao-seed-tts-2.0", "doubao-seed-icl-2.0"}

    def __init__(
        self,
        *,
        app_id: str,
        access_token: str,
        tts_resource_id: str,
        icl_resource_id: str,
        http_client: Any | None = None,
    ) -> None:
        self.app_id = app_id.strip()
        self.access_token = access_token.strip()
        self.tts_resource_id = tts_resource_id.strip() or "seed-tts-2.0"
        self.icl_resource_id = icl_resource_id.strip() or "seed-icl-2.0"
        self.http_client = http_client

    def capability(self) -> dict[str, Any]:
        return {"id": self.provider_id, "models": sorted(self.models)}

    @staticmethod
    def _decode_chunked_audio(content: bytes) -> tuple[bytes, dict[str, Any]]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TtsProviderError("火山引擎返回了无法解析的响应") from exc
        decoder = json.JSONDecoder()
        position = 0
        audio_parts: list[bytes] = []
        final_record: dict[str, Any] = {}
        while position < len(text):
            while position < len(text) and text[position].isspace():
                position += 1
            if position >= len(text):
                break
            try:
                record, position = decoder.raw_decode(text, position)
            except json.JSONDecodeError as exc:
                raise TtsProviderError("火山引擎返回了不完整的音频流") from exc
            final_record = record
            code = int(record.get("code", 0))
            if code not in {0, 20000000}:
                raise TtsProviderError(str(record.get("message") or f"火山引擎语音合成失败（{code}）"))
            if record.get("data"):
                try:
                    audio_parts.append(base64.b64decode(record["data"], validate=True))
                except (TypeError, ValueError) as exc:
                    raise TtsProviderError("火山引擎返回了无法解析的音频片段") from exc
        audio = b"".join(audio_parts)
        if not audio:
            raise TtsProviderError("火山引擎未返回音频")
        return audio, final_record

    async def synthesize(self, request: TtsSynthesisRequest) -> TtsSynthesisResult:
        require_configuration(
            VOLCENGINE_TTS_APP_ID=self.app_id,
            VOLCENGINE_TTS_ACCESS_TOKEN=self.access_token,
        )
        ensure_model(request.model, self.models)
        content_type, extension = audio_format_metadata(request.audio_format)
        resource_id = self.icl_resource_id if request.model == "doubao-seed-icl-2.0" else self.tts_resource_id
        parameters = request.parameters
        req_params: dict[str, Any] = {
            "text": request.text,
            "speaker": request.voice_id,
            "speed_ratio": float(parameters.get("speed_ratio", 1.0)),
            "volume_ratio": float(parameters.get("volume_ratio", 1.0)),
            "audio_params": {"format": request.audio_format, "sample_rate": 24000},
        }
        context_text = str(parameters.get("context_text", "")).strip()
        if context_text:
            req_params["additions"] = {"context_texts": [context_text]}
        request_id = str(uuid.uuid4())
        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "Content-Type": "application/json",
        }
        payload = {"user": {"uid": request.user_id}, "req_params": req_params}
        started = time.perf_counter()
        if self.http_client is not None:
            response = await self.http_client.post(self.endpoint, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
        ensure_success_status(response)
        audio, final_record = self._decode_chunked_audio(bytes(response.content))
        response_headers = getattr(response, "headers", {})
        return TtsSynthesisResult(
            audio=audio,
            content_type=content_type,
            extension=extension,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
            metadata={
                "request_id": request_id,
                "log_id": response_headers.get("X-Tt-Logid"),
                "message": final_record.get("message"),
            },
        )
