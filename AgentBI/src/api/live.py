from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError, field_validator

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.services.live.qwen_audio_realtime import (
    LiveConfigurationError,
    LiveSessionConfig,
    QwenAudioRealtimeSession,
)

LiveModelId = Literal[
    "qwen-audio-3.0-realtime-flash",
    "qwen-audio-3.0-realtime-plus",
]
LiveVoiceId = Literal[
    "longanqian",
    "longanlingxin",
    "longanlingxi",
    "longanxiaoxin",
    "longanlufeng",
]


class LivePreferencesUpdate(BaseModel):
    model: LiveModelId
    voice: LiveVoiceId
    instructions: str = Field(min_length=1, max_length=12000)

    @field_validator("instructions")
    @classmethod
    def normalize_instructions(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("系统提示词不能为空")
        return normalized


class LivePreferencesResponse(LivePreferencesUpdate):
    user_id: str


class LiveSessionStart(LivePreferencesUpdate):
    type: Literal["session.start"]


router = APIRouter(tags=["live"])


@router.get("/live/preferences", response_model=LivePreferencesResponse)
def get_live_preferences(request: Request, user_id: str = Query(min_length=1)):
    return get_chat_repository(request).get_live_preferences(user_id)


@router.put("/live/preferences", response_model=LivePreferencesResponse)
def save_live_preferences(
    request: Request,
    payload: LivePreferencesUpdate,
    user_id: str = Query(min_length=1),
):
    return get_chat_repository(request).save_live_preferences(user_id, payload.model_dump())


@router.websocket("/live/ws")
async def live_websocket(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        try:
            start = LiveSessionStart.model_validate(await websocket.receive_json())
        except (ValidationError, ValueError, TypeError):
            await websocket.send_json(
                {
                    "type": "session.error",
                    "code": "invalid_session_start",
                    "message": "Live 会话配置无效，请检查模型、音色和系统提示词",
                    "recoverable": False,
                }
            )
            await websocket.close(code=1008)
            return

        try:
            session = QwenAudioRealtimeSession(
                api_key=os.getenv("DASHSCOPE_API_KEY", ""),
                workspace_id=os.getenv("DASHSCOPE_WORKSPACE_ID", ""),
            )
        except LiveConfigurationError as error:
            await websocket.send_json(
                {
                    "type": "session.error",
                    "code": "live_configuration_missing",
                    "message": str(error),
                    "recoverable": False,
                }
            )
            await websocket.close(code=1011)
            return

        await session.run(
            websocket,
            LiveSessionConfig(
                model=start.model,
                voice=start.voice,
                instructions=start.instructions,
            ),
        )
        await websocket.send_json({"type": "session.closed"})
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.send_json(
                {
                    "type": "session.error",
                    "code": "live_session_failed",
                    "message": "实时语音连接异常，请结束后重新开始",
                    "recoverable": True,
                }
            )
            await websocket.close(code=1011)
        except Exception:
            return
