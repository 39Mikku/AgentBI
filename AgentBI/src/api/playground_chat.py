from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from AgentBI.src.api.dependencies import get_chat_repository, get_playground_repository
from AgentBI.src.logging.logging import Logger
from AgentBI.src.schemas.playground_schema import (
    PlaygroundChatStreamRequest,
    PlaygroundEditStreamRequest,
    PlaygroundRetryStreamRequest,
)
from AgentBI.src.services.chat_service import append_timeline_event, encode_sse_event, format_model_error
from AgentBI.src.services.memory_service import MemoryService
from AgentBI.src.services.playground.prompt_composer import PlaygroundPromptComposer
from AgentBI.src.services.playground.runtime import PlaygroundRuntime
from AgentBI.src.services.playground.structured_output import StructuredTailResult
from AgentBI.src.services.playground.summarizer import PlaygroundSummarizer


router = APIRouter(prefix="/playground", tags=["playground-chat"])
logger = Logger.get_logger(__name__)


def _resolve(request: Request, payload: Any):
    chat = get_chat_repository(request)
    playground = get_playground_repository(request)
    thread = chat.get_workspace_conversation(
        payload.conversation_id, payload.user_id, "playground"
    )
    profile = playground.get_profile(payload.profile_id, payload.user_id)
    if (
        thread is None
        or profile is None
        or thread.get("owner_id") != payload.profile_id
        or thread.get("owner_type") != profile.get("profile_type")
    ):
        raise HTTPException(status_code=404, detail="Playground 会话或资料不存在")
    preferences = playground.get_preferences(payload.user_id)
    provider = chat.get_provider(preferences.get("provider_id"))
    if provider is None:
        raise HTTPException(status_code=400, detail="请先配置 Playground 模型提供商")
    model = preferences.get("model") or provider.get("default_model")
    if not model:
        raise HTTPException(status_code=400, detail="请先配置 Playground 聊天模型")
    return chat, playground, thread, profile, preferences, provider, str(model)


def _clear_terminal_options(chat, thread: dict[str, Any], user_id: str) -> None:
    path = chat.get_active_path(thread["_id"], user_id)
    leaf = path[-1] if path else None
    if leaf and leaf.get("role") == "assistant":
        metadata = leaf.get("metadata") or {}
        if metadata.get("action_options"):
            chat.update_message_metadata(leaf["_id"], user_id, {"action_options": []})


def _previous_state(path: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(path):
        if item.get("role") != "assistant":
            continue
        snapshot = (item.get("metadata") or {}).get("state_snapshot")
        if isinstance(snapshot, dict):
            return snapshot
    return None


def _model_snapshot(
    provider: dict[str, Any],
    model: str,
    preferences: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    return {
        "workspace_type": "playground",
        "profile_id": profile["_id"],
        "profile_type": profile["profile_type"],
        "provider_id": provider["_id"],
        "provider_name": provider.get("name"),
        "model": model,
        "temperature": preferences.get("temperature", 1.0),
        "context_turns": preferences.get("context_turns", 24),
        "thinking_level": preferences.get("thinking_level", "medium"),
    }


async def _prepare_generation(
    request: Request,
    payload: PlaygroundChatStreamRequest | PlaygroundRetryStreamRequest | PlaygroundEditStreamRequest,
    operation: Literal["send", "retry", "edit"],
):
    chat, playground, thread, profile, preferences, provider, model = _resolve(request, payload)
    _clear_terminal_options(chat, thread, payload.user_id)

    if operation == "send":
        user_message = chat.create_user_message(
            payload.conversation_id, payload.user_id, payload.content
        )
        if user_message is None:
            raise HTTPException(status_code=404, detail="无法创建用户消息")
        assistant_message = chat.create_assistant_message(
            payload.conversation_id,
            payload.user_id,
            user_message["_id"],
            _model_snapshot(provider, model, preferences, profile),
        )
    elif operation == "edit":
        user_message = chat.edit_user_message(
            payload.conversation_id,
            payload.user_id,
            payload.message_id,
            payload.content,
        )
        if user_message is None:
            raise HTTPException(status_code=404, detail="用户消息不存在")
        assistant_message = chat.create_assistant_message(
            payload.conversation_id,
            payload.user_id,
            user_message["_id"],
            _model_snapshot(provider, model, preferences, profile),
        )
    else:
        source_path = chat.get_path_to_message(
            payload.conversation_id, payload.user_id, payload.message_id
        )
        source = source_path[-1] if source_path else None
        if not source or source.get("role") != "assistant" or not source.get("parent_id"):
            raise HTTPException(status_code=404, detail="助手消息不存在")
        assistant_message = chat.retry_assistant_message(
            payload.conversation_id,
            payload.user_id,
            payload.message_id,
            _model_snapshot(provider, model, preferences, profile),
        )

    if assistant_message is None:
        raise HTTPException(status_code=404, detail="无法创建助手消息版本")
    generation_path = chat.get_path_to_message(
        payload.conversation_id,
        payload.user_id,
        str(assistant_message["parent_id"]),
    )
    latest_thread = chat.get_workspace_conversation(
        payload.conversation_id, payload.user_id, "playground"
    )
    summarizer = PlaygroundSummarizer(chat, playground)
    summary = await summarizer.ensure_current(latest_thread, profile, preferences)
    modules = playground.list_prompt_modules(profile["_id"], payload.user_id)
    persona = playground.get_persona(profile["_id"], payload.user_id)
    context_entries = playground.list_context_entries(profile["_id"], payload.user_id)
    previous_state = _previous_state(generation_path)
    assembly = PlaygroundPromptComposer().compose(
        profile=profile,
        active_path=generation_path,
        modules=modules,
        persona=persona,
        context_entries=context_entries,
        summary=summary,
        previous_state=previous_state,
        context_turns=int(preferences.get("context_turns", 24)),
    )
    return {
        "chat": chat,
        "playground": playground,
        "thread": latest_thread,
        "profile": profile,
        "preferences": preferences,
        "provider": provider,
        "model": model,
        "assistant_message": assistant_message,
        "messages": assembly.messages,
        "matched_context_entry_ids": assembly.matched_context_entry_ids,
        "previous_state": previous_state,
        "summarizer": summarizer,
    }


def _message_start_payload(context: dict[str, Any]) -> dict[str, Any]:
    message = context["assistant_message"]
    created_at = message.get("created_at")
    return {
        "conversation_id": context["thread"]["_id"],
        "message_id": message["_id"],
        "parent_message_id": message["parent_id"],
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else "",
        "conversation_title": context["thread"].get("title", ""),
        "conversation_active_message_id": message["_id"],
    }


def _stream_response(context: dict[str, Any]) -> AsyncIterator[str]:
    async def event_stream():
        chat = context["chat"]
        message = context["assistant_message"]
        profile = context["profile"]
        preferences = context["preferences"]
        settings = profile.get("settings") or {}
        state_settings = settings.get("state") or {}
        options_settings = settings.get("action_options") or {}
        answer: list[str] = []
        reasoning: list[str] = []
        timeline: list[dict[str, Any]] = []
        structured: StructuredTailResult | None = None
        yield encode_sse_event("message_start", _message_start_payload(context))
        try:
            async for event in PlaygroundRuntime().stream(
                messages=context["messages"],
                provider=context["provider"],
                model=context["model"],
                temperature=float(preferences.get("temperature", 1.0)),
                thinking_level=str(preferences.get("thinking_level", "medium")),
                expect_state=bool(state_settings.get("enabled")),
                expect_options=bool(options_settings.get("enabled")),
                variable_definitions=state_settings.get("variables", []),
                previous_state=context["previous_state"],
            ):
                if event["type"] == "delta":
                    answer.append(event["content"])
                    append_timeline_event(timeline, "delta", event)
                    yield encode_sse_event("delta", event)
                elif event["type"] == "reasoning_summary":
                    reasoning.append(event["content"])
                    append_timeline_event(timeline, "reasoning_summary", event)
                    yield encode_sse_event("reasoning_summary", event)
                elif event["type"] == "structured":
                    structured = event["result"]

            state_snapshot = (
                structured.state_snapshot if structured and structured.state_snapshot is not None
                else context["previous_state"] if state_settings.get("enabled")
                else None
            )
            action_options = structured.action_options if structured else None
            structured_errors = structured.errors if structured else []
            metadata = {
                "state_snapshot": state_snapshot,
                "action_options": action_options or [],
                "structured_errors": structured_errors,
                "matched_context_entry_ids": context["matched_context_entry_ids"],
            }
            completed = chat.complete_assistant_message(
                message["_id"],
                "".join(answer),
                reasoning_summary="".join(reasoning) or None,
                timeline=timeline,
                metadata=metadata,
            )
            if state_snapshot is not None:
                yield encode_sse_event("state_snapshot", {"snapshot": state_snapshot})
            if action_options:
                yield encode_sse_event("action_options", {"options": action_options})
            yield encode_sse_event(
                "done",
                {
                    "message_id": completed["_id"],
                    "conversation_id": context["thread"]["_id"],
                },
            )

            latest_thread = chat.get_workspace_conversation(
                context["thread"]["_id"], message["user_id"], "playground"
            )
            try:
                title = await MemoryService(chat).generate_title(latest_thread)
                if title:
                    yield encode_sse_event(
                        "conversation_title_updated",
                        {"conversation_id": latest_thread["_id"], "title": title},
                    )
            except Exception:
                logger.exception("Playground 会话标题生成失败: %s", latest_thread["_id"])

            if context["summarizer"].begin_after_reply(
                latest_thread, profile, preferences
            ):
                asyncio.create_task(
                    _maintain_summary(
                        context["summarizer"], latest_thread, profile, preferences
                    )
                )
                yield encode_sse_event(
                    "summary_status",
                    {"status": "running", "conversation_id": latest_thread["_id"]},
                )
        except Exception as error:
            message_text = format_model_error(error)
            logger.exception(
                "Playground 模型流式调用失败: provider=%s model=%s",
                context["provider"].get("name"),
                context["model"],
            )
            failed = chat.fail_assistant_message(message["_id"], message_text)
            yield encode_sse_event(
                "error",
                {
                    "message": message_text,
                    "message_id": failed["_id"] if failed else None,
                    "conversation_id": context["thread"]["_id"],
                },
            )

    return event_stream()


async def _maintain_summary(summarizer, thread, profile, preferences) -> None:
    try:
        await summarizer.maintain_acquired_after_reply(thread, profile, preferences)
    except Exception:
        logger.exception("Playground 后台大总结失败: conversation_id=%s", thread.get("_id"))


@router.post("/chat/stream")
async def stream_chat(request: Request, payload: PlaygroundChatStreamRequest):
    context = await _prepare_generation(request, payload, "send")
    return StreamingResponse(_stream_response(context), media_type="text/event-stream")


async def retry_stream(request: Request, payload: PlaygroundRetryStreamRequest):
    context = await _prepare_generation(request, payload, "retry")
    return StreamingResponse(_stream_response(context), media_type="text/event-stream")


async def edit_stream(request: Request, payload: PlaygroundEditStreamRequest):
    context = await _prepare_generation(request, payload, "edit")
    return StreamingResponse(_stream_response(context), media_type="text/event-stream")
