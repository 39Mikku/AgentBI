from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from AgentBI.src.agents.chat_agent import ChatAgent
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.logging.logging import Logger
from AgentBI.src.schemas.chat_schema import ChatStreamRequest
from AgentBI.src.services.chat_service import ChatService, append_timeline_event, encode_sse_event, format_model_error

router = APIRouter(tags=["chat"])
logger = Logger.get_logger(__name__)


@router.post("/chat/stream")
async def stream_chat(request: Request, payload: ChatStreamRequest):
    repository = get_chat_repository(request)
    conversation = repository.get_conversation(payload.conversation_id, payload.user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    provider_id = payload.provider_id or conversation.get("provider_id")
    if not provider_id:
        raise HTTPException(status_code=400, detail="请先在设置页选择模型提供商")
    provider = repository.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="模型提供商不存在")
    model = payload.model or conversation.get("model") or provider.get("default_model")
    if not model:
        raise HTTPException(status_code=400, detail="请先选择模型")
    temperature = payload.temperature if payload.temperature is not None else conversation.get("temperature", 0.7)
    context_turns = payload.context_turns or conversation.get("context_turns", 8)
    repository.update_conversation(
        payload.conversation_id,
        payload.user_id,
        {
            "provider_id": provider_id,
            "model": model,
            "temperature": temperature,
            "context_turns": context_turns,
        },
    )
    logger.info("聊天请求: provider=%s model=%s temperature=%s context_turns=%s", provider_id, model, temperature, context_turns)

    repository.append_message(payload.conversation_id, payload.user_id, "user", payload.content)
    if not conversation.get("title") or conversation["title"] == "未命名会话":
        repository.update_conversation(payload.conversation_id, payload.user_id, {"title": payload.content[:36]})
    context = ChatService(repository).build_context(payload.conversation_id, payload.user_id, context_turns)

    async def event_stream() -> AsyncIterator[str]:
        answer: list[str] = []
        reasoning: list[str] = []
        tool_events: list[dict] = []
        timeline: list[dict] = []
        yield encode_sse_event("message_start", {"conversation_id": payload.conversation_id})
        try:
            async for event in ChatAgent().stream(context, provider, model, temperature):
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
            message = repository.append_message(
                payload.conversation_id,
                payload.user_id,
                "assistant",
                "".join(answer) or "工具任务已执行完成。",
                reasoning_summary="".join(reasoning) or None,
                tool_events=tool_events,
                timeline=timeline,
            )
            yield encode_sse_event("done", {"message_id": str(message["_id"]), "conversation_id": payload.conversation_id})
        except Exception as error:
            message = format_model_error(error)
            logger.exception("模型流式调用失败: provider=%s model=%s", provider_id, model)
            repository.append_message(
                payload.conversation_id,
                payload.user_id,
                "assistant",
                message,
                status="error",
            )
            yield encode_sse_event("error", {"message": message, "conversation_id": payload.conversation_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
