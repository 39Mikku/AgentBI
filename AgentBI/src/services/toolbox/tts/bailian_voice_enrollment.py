from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from AgentBI.src.schemas.toolbox_tts_schema import LiveVoiceEnrollmentRequest
from AgentBI.src.services.toolbox.tts.base import (
    TtsProviderError,
    ensure_success_status,
    require_configuration,
)


@dataclass(slots=True, frozen=True)
class LiveVoiceEnrollmentResult:
    voice_id: str
    request_id: str | None = None


class BailianLiveVoiceEnrollmentAdapter:
    def __init__(self, *, api_key: str, workspace_id: str, http_client: Any | None = None) -> None:
        self.api_key = api_key.strip()
        self.workspace_id = workspace_id.strip()
        self.http_client = http_client

    @property
    def endpoint(self) -> str:
        return (
            f"https://{self.workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/api/v1/services/audio/tts/customization"
        )

    async def enroll(self, request: LiveVoiceEnrollmentRequest) -> LiveVoiceEnrollmentResult:
        require_configuration(
            DASHSCOPE_API_KEY=self.api_key,
            DASHSCOPE_WORKSPACE_ID=self.workspace_id,
        )
        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": request.target_model,
                "prefix": request.prefix,
                "url": request.audio_url,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self.http_client is not None:
                response = await self.http_client.post(self.endpoint, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise TtsProviderError("无法连接百炼 Live 音色复刻服务") from exc
        ensure_success_status(response)
        try:
            body = response.json()
        except (TypeError, ValueError) as exc:
            raise TtsProviderError("百炼 Live 音色复刻返回了无效响应") from exc
        request_id = str(body.get("request_id") or "") or None
        if body.get("code"):
            raise TtsProviderError(
                "百炼 Live 音色复刻失败"
                + (f"（request_id: {request_id}）" if request_id else "")
            )
        voice_id = str((body.get("output") or {}).get("voice_id") or "").strip()
        if not voice_id:
            raise TtsProviderError(
                "百炼未返回复刻音色 ID"
                + (f"（request_id: {request_id}）" if request_id else "")
            )
        return LiveVoiceEnrollmentResult(voice_id=voice_id, request_id=request_id)
