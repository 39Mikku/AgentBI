import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from AgentBI.src.agents.chat_agent import ChatAgent
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.logging.logging import Logger
from AgentBI.src.schemas.chat_schema import ChatEditStreamRequest, ChatRetryStreamRequest, ChatStreamRequest
from AgentBI.src.services.chat_service import append_timeline_event, encode_sse_event, format_model_error
from AgentBI.src.services.bilibili_client import BilibiliClient
from AgentBI.src.services.memory_service import MemoryService, build_context_bundle
from AgentBI.src.api.music import get_music_client
from AgentBI.src.services.netease_music_client import NeteaseMusicClient
from AgentBI.src.services.image_generation.service import ImageGenerationService
from AgentBI.src.services.video_generation.service import VideoGenerationService
from AgentBI.src.services.model_task_service import ModelTaskConfigurationError
from AgentBI.src.services.multimodal_context_service import MultimodalContextService

router = APIRouter(tags=["chat"])
logger = Logger.get_logger(__name__)


def build_runtime_context(payload: Any) -> dict[str, str]:
    timezone = payload.timezone or "Asia/Shanghai"
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        timezone = "Asia/Shanghai"
        now = datetime.now(ZoneInfo(timezone))
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone,
        "locale": payload.locale or "zh-CN",
        "user_name": payload.user_name or payload.user_id,
    }


def resolve_generation(repository: Any, payload: Any) -> tuple[dict[str, Any], dict[str, Any], str, float, int, str, dict[str, Any]]:
    thread = repository.get_conversation(payload.conversation_id, payload.user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="会话不存在")
    assistant = repository.get_assistant(thread.get("assistant_id"), payload.user_id) or repository.ensure_default_assistant(payload.user_id)
    if thread.get("assistant_id") != assistant["_id"]:
        thread = repository.update_conversation(payload.conversation_id, payload.user_id, {"assistant_id": assistant["_id"]}) or thread
    provider_id = payload.provider_id or thread.get("provider_id")
    if not provider_id:
        raise HTTPException(status_code=400, detail="请先在设置页选择模型提供商")
    provider = repository.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="模型提供商不存在")
    model = payload.model or thread.get("model") or provider.get("default_model")
    if not model:
        raise HTTPException(status_code=400, detail="请先选择模型")
    temperature = payload.temperature if payload.temperature is not None else thread.get("temperature", 0.7)
    context_turns = payload.context_turns if payload.context_turns is not None else thread.get("context_turns", 8)
    thinking_level = payload.thinking_level
    thread = repository.update_conversation(
        payload.conversation_id,
        payload.user_id,
        {
            "provider_id": provider_id,
            "model": model,
            "temperature": temperature,
            "context_turns": context_turns,
        },
    )
    logger.info(
        "聊天请求: provider=%s model=%s temperature=%s context_turns=%s thinking_level=%s",
        provider_id,
        model,
        temperature,
        context_turns,
        thinking_level,
    )
    return thread, provider, model, temperature, context_turns, thinking_level, assistant


def model_snapshot(thread: dict[str, Any], provider: dict[str, Any], model: str, temperature: float, context_turns: int, thinking_level: str, assistant: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": str(provider["_id"]),
        "provider_name": provider.get("name"),
        "model": model,
        "temperature": temperature,
        "context_turns": context_turns,
        "thinking_level": thinking_level,
        "assistant_id": str(assistant["_id"]),
    }


def build_message_start_payload(
    conversation_id: str,
    assistant_message: dict[str, Any],
    conversation_title: str,
) -> dict[str, str]:
    """Provide enough persisted metadata for the client to finalize optimistic nodes."""
    created_at = assistant_message.get("created_at")
    timestamp = created_at.isoformat() if isinstance(created_at, datetime) else ""
    message_id = str(assistant_message["_id"])
    return {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "parent_message_id": str(assistant_message["parent_id"]),
        "created_at": timestamp,
        "conversation_title": conversation_title,
        "conversation_updated_at": timestamp,
        "conversation_last_message_at": timestamp,
        "conversation_active_message_id": message_id,
    }


def stream_assistant(
    repository: Any,
    conversation_id: str,
    assistant_message: dict[str, Any],
    context: list[dict[str, Any]],
    provider: dict[str, Any],
    model: str,
    temperature: float,
    thinking_level: str,
    runtime_context: dict[str, str],
    conversation_title: str,
    assistant: dict[str, Any],
    memory_service: MemoryService,
    memory_summary: str | None = None,
    context_summary: str | None = None,
    music_client: NeteaseMusicClient | None = None,
    bilibili_client: BilibiliClient | None = None,
    image_generation_service: ImageGenerationService | None = None,
    video_generation_service: VideoGenerationService | None = None,
    asset_service: Any | None = None,
) -> AsyncIterator[str]:
    async def event_stream() -> AsyncIterator[str]:
        answer: list[str] = []
        reasoning: list[str] = []
        tool_events: list[dict[str, Any]] = []
        timeline: list[dict[str, Any]] = []
        yield encode_sse_event(
            "message_start",
            build_message_start_payload(conversation_id, assistant_message, conversation_title),
        )
        try:
            reference_image_data_url = (
                asset_service.message_reference_image_data_url(
                    str(assistant_message["parent_id"]), assistant_message["user_id"]
                )
                if asset_service
                else None
            )
            async for event in ChatAgent(
                assistant.get("system_prompt"),
                assistant.get("capability_ids", []),
                assistant.get("include_runtime_context", True),
                repository,
                memory_service,
                assistant_message["user_id"],
                assistant,
                memory_summary,
                context_summary,
                conversation_id,
                music_client,
                bilibili_client,
                image_generation_service=image_generation_service,
                video_generation_service=video_generation_service,
                assistant_message_id=str(assistant_message["_id"]),
                reference_image_data_url=reference_image_data_url,
            ).stream(context, provider, model, temperature, thinking_level, runtime_context):
                event_type = event["type"]
                if event_type == "delta":
                    answer.append(event["content"])
                    append_timeline_event(timeline, event_type, event)
                    yield encode_sse_event("delta", event)
                elif event_type == "reasoning_summary":
                    reasoning.append(event["content"])
                    append_timeline_event(timeline, event_type, event)
                    yield encode_sse_event("reasoning_summary", event)
                elif event_type in {"tool_started", "tool_finished"}:
                    tool_events.append(event)
                    append_timeline_event(timeline, event_type, event)
                    yield encode_sse_event(event_type, event)
                elif event_type == "card":
                    asset_id = event.get("payload", {}).get("asset_id")
                    if asset_id and asset_service:
                        repository.bind_message_assets(
                            str(assistant_message["_id"]),
                            assistant_message["user_id"],
                            [str(asset_id)],
                        )
                    append_timeline_event(timeline, event_type, event)
                    yield encode_sse_event("card", event)
            message = repository.complete_assistant_message(
                str(assistant_message["_id"]),
                "".join(answer) or "工具任务已执行完成。",
                reasoning_summary="".join(reasoning) or None,
                tool_events=tool_events,
                timeline=timeline,
            )
            yield encode_sse_event("done", {"message_id": str(message["_id"]), "conversation_id": conversation_id})
            latest_thread = repository.get_conversation(conversation_id, assistant_message["user_id"])
            if latest_thread:
                try:
                    title = await memory_service.generate_title(latest_thread)
                    if title:
                        yield encode_sse_event(
                            "conversation_title_updated",
                            {"conversation_id": conversation_id, "title": title},
                        )
                except Exception:
                    logger.exception("会话标题生成失败: conversation_id=%s", conversation_id)
                asyncio.create_task(_maintain_after_reply(memory_service, latest_thread, assistant))
        except Exception as error:
            message = format_model_error(error)
            logger.exception("模型流式调用失败: provider=%s model=%s", provider.get("name"), model)
            failed = repository.fail_assistant_message(str(assistant_message["_id"]), message)
            yield encode_sse_event(
                "error",
                {"message": message, "message_id": str(failed["_id"]) if failed else None, "conversation_id": conversation_id},
            )

    return event_stream()


async def prepare_multimodal_context(
    request: Request,
    repository: Any,
    *,
    user_id: str,
    provider_id: str,
    model: str,
    context: list[dict[str, Any]],
    path: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    asset_service = getattr(request.app.state, "studio_asset_service", None)
    if not asset_service:
        return context
    try:
        return await MultimodalContextService(repository, asset_service).prepare(
            user_id=user_id,
            provider_id=provider_id,
            model=model,
            context=context,
            path=path,
        )
    except (ModelTaskConfigurationError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


async def _maintain_after_reply(
    memory_service: MemoryService,
    thread: dict[str, Any],
    assistant: dict[str, Any],
) -> None:
    try:
        await memory_service.maintain_after_reply(thread, assistant)
    except Exception:
        logger.exception("助手后台记忆维护失败: conversation_id=%s", thread.get("_id"))


@router.post("/chat/stream")
async def stream_chat(request: Request, payload: ChatStreamRequest):
    repository = get_chat_repository(request)
    thread, provider, model, temperature, context_turns, thinking_level, assistant = resolve_generation(repository, payload)
    asset_service = getattr(request.app.state, "studio_asset_service", None)
    if payload.attachment_ids:
        if not asset_service:
            raise HTTPException(status_code=503, detail="附件服务尚未初始化")
        try:
            asset_service.validate_assets(payload.user_id, payload.attachment_ids)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    user_message = repository.create_user_message(payload.conversation_id, payload.user_id, payload.content)
    if not user_message:
        raise HTTPException(status_code=404, detail="无法创建用户消息")
    if payload.attachment_ids:
        asset_service.bind_assets(str(user_message["_id"]), payload.user_id, payload.attachment_ids)
    memory_service = MemoryService(repository)
    bundle = memory_service.context_bundle(thread, assistant, context_turns)
    path = repository.get_active_path(payload.conversation_id, payload.user_id)
    context = await prepare_multimodal_context(
        request,
        repository,
        user_id=payload.user_id,
        provider_id=str(provider["_id"]),
        model=model,
        context=bundle["messages"],
        path=path,
    )
    assistant_message = repository.create_assistant_message(
        payload.conversation_id,
        payload.user_id,
        str(user_message["_id"]),
        model_snapshot(thread, provider, model, temperature, context_turns, thinking_level, assistant),
    )
    if not assistant_message:
        raise HTTPException(status_code=404, detail="无法创建助手消息")
    return StreamingResponse(
        stream_assistant(
            repository,
            payload.conversation_id,
            assistant_message,
            context,
            provider,
            model,
            temperature,
            thinking_level,
            build_runtime_context(payload),
            thread.get("title", ""),
            assistant,
            memory_service,
            memory_service.core_memory(payload.user_id, assistant),
            bundle["summary"],
            get_music_client(request),
            BilibiliClient(),
            image_generation_service=getattr(request.app.state, "image_generation_service", None),
            video_generation_service=getattr(request.app.state, "video_generation_service", None),
            asset_service=asset_service,
        ),
        media_type="text/event-stream",
    )


@router.post("/chat/retry/stream")
async def retry_stream(request: Request, payload: ChatRetryStreamRequest):
    repository = get_chat_repository(request)
    thread, provider, model, temperature, context_turns, thinking_level, assistant = resolve_generation(repository, payload)
    source_path = repository.get_path_to_message(payload.conversation_id, payload.user_id, payload.message_id)
    source = source_path[-1] if source_path else None
    if not source or source.get("role") != "assistant" or not source.get("parent_id"):
        raise HTTPException(status_code=404, detail="助手消息不存在")
    memory_service = MemoryService(repository)
    bundle = build_context_bundle(
        source_path[:-1],
        context_turns,
        assistant.get("context_strategy", "window"),
        thread.get("context_summary"),
        thread.get("context_summary_until_message_id"),
        assistant.get("compression_keep_recent_turns", 4),
    )
    context = await prepare_multimodal_context(
        request,
        repository,
        user_id=payload.user_id,
        provider_id=str(provider["_id"]),
        model=model,
        context=bundle["messages"],
        path=source_path[:-1],
    )
    assistant_message = repository.retry_assistant_message(
        payload.conversation_id,
        payload.user_id,
        payload.message_id,
        model_snapshot(thread, provider, model, temperature, context_turns, thinking_level, assistant),
    )
    if not assistant_message:
        raise HTTPException(status_code=404, detail="无法创建重试版本")
    return StreamingResponse(
        stream_assistant(
            repository,
            payload.conversation_id,
            assistant_message,
            context,
            provider,
            model,
            temperature,
            thinking_level,
            build_runtime_context(payload),
            thread.get("title", ""),
            assistant,
            memory_service,
            memory_service.core_memory(payload.user_id, assistant),
            bundle["summary"],
            get_music_client(request),
            BilibiliClient(),
            image_generation_service=getattr(request.app.state, "image_generation_service", None),
            video_generation_service=getattr(request.app.state, "video_generation_service", None),
            asset_service=getattr(request.app.state, "studio_asset_service", None),
        ),
        media_type="text/event-stream",
    )


@router.post("/chat/edit/stream")
async def edit_stream(request: Request, payload: ChatEditStreamRequest):
    repository = get_chat_repository(request)
    thread, provider, model, temperature, context_turns, thinking_level, assistant = resolve_generation(repository, payload)
    user_message = repository.edit_user_message(payload.conversation_id, payload.user_id, payload.message_id, payload.content)
    if not user_message:
        raise HTTPException(status_code=404, detail="用户消息不存在")
    memory_service = MemoryService(repository)
    bundle = memory_service.context_bundle(thread, assistant, context_turns)
    path = repository.get_active_path(payload.conversation_id, payload.user_id)
    context = await prepare_multimodal_context(
        request,
        repository,
        user_id=payload.user_id,
        provider_id=str(provider["_id"]),
        model=model,
        context=bundle["messages"],
        path=path,
    )
    assistant_message = repository.create_assistant_message(
        payload.conversation_id,
        payload.user_id,
        str(user_message["_id"]),
        model_snapshot(thread, provider, model, temperature, context_turns, thinking_level, assistant),
    )
    if not assistant_message:
        raise HTTPException(status_code=404, detail="无法创建编辑后的助手消息")
    return StreamingResponse(
        stream_assistant(
            repository,
            payload.conversation_id,
            assistant_message,
            context,
            provider,
            model,
            temperature,
            thinking_level,
            build_runtime_context(payload),
            thread.get("title", ""),
            assistant,
            memory_service,
            memory_service.core_memory(payload.user_id, assistant),
            bundle["summary"],
            get_music_client(request),
            BilibiliClient(),
            image_generation_service=getattr(request.app.state, "image_generation_service", None),
            video_generation_service=getattr(request.app.state, "video_generation_service", None),
            asset_service=getattr(request.app.state, "studio_asset_service", None),
        ),
        media_type="text/event-stream",
    )
