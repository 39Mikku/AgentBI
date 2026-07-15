from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, ValidationError, field_validator

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.services.live.conversation_service import (
    LiveConversationService,
    LiveWorkspaceError,
    PreparedLiveCall,
)
from AgentBI.src.services.live.memory_service import LiveMemoryService
from AgentBI.src.services.live.title_service import LiveTitleService
from AgentBI.src.services.live.qwen_audio_realtime import (
    LiveConfigurationError,
    LiveSessionConfig,
    QwenAudioRealtimeSession,
)

LiveModelId = Literal[
    "qwen-audio-3.0-realtime-flash",
    "qwen-audio-3.0-realtime-plus",
]
class LivePreferencesUpdate(BaseModel):
    model: LiveModelId
    history_context_turns: int = Field(default=12, ge=0, le=50)
    max_history_turns: int = Field(default=20, ge=1, le=50)


class LivePreferencesResponse(LivePreferencesUpdate):
    user_id: str


class LiveRoleCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=320)
    name: str = Field(min_length=1, max_length=80)
    instructions: str = Field(min_length=1, max_length=12000)
    voice: str = Field(min_length=1, max_length=128)
    avatar_data_url: str | None = Field(default=None, max_length=8_000_000)
    memory_enabled: bool = False


    @field_validator("user_id", "name", "instructions", "voice")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("字段不能为空")
        return normalized


class LiveRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    instructions: str | None = Field(default=None, min_length=1, max_length=12000)
    voice: str | None = Field(default=None, min_length=1, max_length=128)
    avatar_data_url: str | None = Field(default=None, max_length=8_000_000)
    memory_enabled: bool | None = None

    @field_validator("name", "instructions", "voice")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("字段不能为空")
        return normalized


class LiveRoleResponse(BaseModel):
    id: str
    user_id: str
    name: str
    instructions: str
    voice: str
    avatar_data_url: str | None = None
    memory_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class LiveRoleMemoryUpdate(BaseModel):
    content: str = Field(default="", max_length=50000)


class LiveRoleMemoryResponse(BaseModel):
    user_id: str
    role_id: str
    content: str
    last_message_id: str | None = None
    updated_at: datetime | None = None


class LiveConversationCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=320)
    role_id: str = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=80)


class LiveConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("会话标题不能为空")
        return normalized


class LiveConversationResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime


class LiveMessageResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    role_id: str
    item_id: str
    role: Literal["user", "assistant"]
    content: str
    status: Literal["complete", "interrupted"]
    created_at: datetime
    updated_at: datetime


class LiveSessionStart(BaseModel):
    type: Literal["session.start"]
    role_id: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=64)


router = APIRouter(tags=["live"])
logger = logging.getLogger(__name__)
_live_maintenance_tasks: set[asyncio.Task] = set()


def _track_live_maintenance(task: asyncio.Task, failure_message: str) -> None:
    _live_maintenance_tasks.add(task)

    def finish(completed: asyncio.Task) -> None:
        _live_maintenance_tasks.discard(completed)
        try:
            completed.result()
        except Exception:
            logger.exception(failure_message)

    task.add_done_callback(finish)


def _schedule_live_maintenance(repository, prepared: PreparedLiveCall) -> None:
    recorder = prepared.recorder
    if not recorder.has_new_complete_messages:
        return

    _track_live_maintenance(
        asyncio.create_task(
            LiveTitleService(repository).generate_after_call(
                prepared.user_id,
                prepared.role["id"],
                prepared.conversation["id"],
            )
        ),
        "Live 会话标题后台生成失败",
    )
    if not prepared.role["memory_enabled"]:
        return
    _track_live_maintenance(
        asyncio.create_task(LiveMemoryService(repository).update_after_call(
            prepared.user_id,
            prepared.role["id"],
            recorder.last_complete_message_id,
        )),
        "Live 角色记忆后台更新失败",
    )


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


def owned_live_role(repository, role_id: str, user_id: str):
    role = repository.get_live_role(role_id, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="Live 角色不存在")
    return role


def owned_live_conversation(repository, conversation_id: str, user_id: str):
    conversation = repository.get_live_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Live 会话不存在")
    return conversation


@router.get("/live/roles", response_model=list[LiveRoleResponse])
def list_live_roles(request: Request, user_id: str = Query(min_length=1)):
    return get_chat_repository(request).list_live_roles(user_id)


@router.post("/live/roles", response_model=LiveRoleResponse, status_code=status.HTTP_201_CREATED)
def create_live_role(request: Request, payload: LiveRoleCreate):
    return get_chat_repository(request).create_live_role(payload.model_dump())


@router.put("/live/roles/{role_id}", response_model=LiveRoleResponse)
def update_live_role(
    role_id: str,
    request: Request,
    payload: LiveRoleUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    return repository.update_live_role(
        role_id,
        user_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete("/live/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_live_role(role_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    if not repository.delete_live_role(role_id, user_id):
        raise HTTPException(status_code=409, detail="默认 Live 角色不可删除")


@router.get("/live/roles/{role_id}/memory", response_model=LiveRoleMemoryResponse)
def get_live_role_memory(role_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    return repository.get_live_role_memory(user_id, role_id)


@router.put("/live/roles/{role_id}/memory", response_model=LiveRoleMemoryResponse)
def save_live_role_memory(
    role_id: str,
    request: Request,
    payload: LiveRoleMemoryUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    current = repository.get_live_role_memory(user_id, role_id)
    return repository.save_live_role_memory(
        user_id,
        role_id,
        payload.content,
        current.get("last_message_id"),
    )


@router.delete("/live/roles/{role_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
def clear_live_role_memory(role_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    repository.clear_live_role_memory(user_id, role_id)


@router.post("/live/roles/{role_id}/memory/refresh", response_model=LiveRoleMemoryResponse)
async def refresh_live_role_memory(
    role_id: str,
    request: Request,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    role = owned_live_role(repository, role_id, user_id)
    if not role["memory_enabled"]:
        raise HTTPException(status_code=400, detail="请先启用角色记忆")
    await LiveMemoryService(repository).refresh(user_id, role_id)
    return repository.get_live_role_memory(user_id, role_id)


@router.get("/live/conversations", response_model=list[LiveConversationResponse])
def list_live_conversations(
    request: Request,
    user_id: str = Query(min_length=1),
    role_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_role(repository, role_id, user_id)
    return repository.list_live_conversations(user_id, role_id)


@router.post(
    "/live/conversations",
    response_model=LiveConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_live_conversation(request: Request, payload: LiveConversationCreate):
    repository = get_chat_repository(request)
    owned_live_role(repository, payload.role_id, payload.user_id)
    return repository.create_live_conversation(payload.model_dump())


@router.put("/live/conversations/{conversation_id}", response_model=LiveConversationResponse)
def update_live_conversation(
    conversation_id: str,
    request: Request,
    payload: LiveConversationUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_conversation(repository, conversation_id, user_id)
    return repository.update_live_conversation(
        conversation_id,
        user_id,
        payload.model_dump(),
    )


@router.delete("/live/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_live_conversation(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_conversation(repository, conversation_id, user_id)
    repository.delete_live_conversation(conversation_id, user_id)


@router.get(
    "/live/conversations/{conversation_id}/messages",
    response_model=list[LiveMessageResponse],
)
def list_live_messages(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_live_conversation(repository, conversation_id, user_id)
    return repository.list_live_messages(conversation_id, user_id)


@router.websocket("/live/ws")
async def live_websocket(websocket: WebSocket, user_id: str):
    await websocket.accept()
    repository = None
    prepared: PreparedLiveCall | None = None
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

        repository = get_chat_repository(websocket)  # type: ignore[arg-type]
        try:
            prepared = LiveConversationService(repository).prepare(
                user_id,
                start.role_id,
                start.conversation_id,
            )
        except LiveWorkspaceError:
            await websocket.send_json(
                {
                    "type": "session.error",
                    "code": "live_workspace_not_found",
                    "message": "Live 角色或会话不存在，请刷新后重试",
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
            prepared.config,
            event_handler=prepared.recorder.handle,
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
    finally:
        if repository is not None and prepared is not None:
            _schedule_live_maintenance(repository, prepared)
