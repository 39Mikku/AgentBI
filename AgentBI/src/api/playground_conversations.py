from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from AgentBI.src.api.dependencies import get_chat_repository, get_playground_repository
from AgentBI.src.schemas.chat_schema import ChatMessageResponse, ConversationResponse
from AgentBI.src.schemas.playground_schema import (
    ConversationSummaryResponse,
    ConversationSummaryUpdate,
    PlaygroundActiveMessageUpdate,
    PlaygroundConversationBranchCreate,
    PlaygroundConversationCreate,
    PlaygroundConversationUpdate,
    PlaygroundEditStreamRequest,
    PlaygroundOpeningMessageUpdate,
    PlaygroundRetryStreamRequest,
    ProfileType,
)
from AgentBI.src.services.playground.summarizer import PlaygroundSummarizer


router = APIRouter(prefix="/playground", tags=["playground-conversations"])


def _owned_thread(request: Request, conversation_id: str, user_id: str):
    thread = get_chat_repository(request).get_workspace_conversation(
        conversation_id, user_id, "playground"
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Playground 会话不存在")
    return thread


def _owned_profile(request: Request, profile_id: str, user_id: str, profile_type: str | None = None):
    profile = get_playground_repository(request).get_profile(profile_id, user_id)
    if profile is None or (profile_type and profile.get("profile_type") != profile_type):
        raise HTTPException(status_code=404, detail="角色或世界不存在")
    return profile


def _assert_thread_profile(thread, profile_id: str, profile_type: str | None = None) -> None:
    if thread.get("owner_id") != profile_id or (
        profile_type and thread.get("owner_type") != profile_type
    ):
        raise HTTPException(status_code=404, detail="会话不属于该角色或世界")


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
    profile_id: str = Query(min_length=1, max_length=100),
    profile_type: ProfileType = Query(),
):
    return [
        ConversationResponse.from_document(item)
        for item in get_chat_repository(request).list_workspace_conversations(
            user_id, "playground", profile_type, profile_id
        )
    ]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(request: Request, payload: PlaygroundConversationCreate):
    profile = _owned_profile(
        request, payload.profile_id, payload.user_id, payload.profile_type
    )
    preferences = get_playground_repository(request).get_preferences(payload.user_id)
    thread = get_chat_repository(request).create_conversation(
        {
            "user_id": payload.user_id,
            "title": payload.title or "未命名会话",
            "provider_id": preferences.get("provider_id"),
            "model": preferences.get("model"),
            "temperature": preferences.get("temperature", 1.0),
            "context_turns": preferences.get("context_turns", 24),
            "workspace_type": "playground",
            "owner_type": payload.profile_type,
            "owner_id": payload.profile_id,
        }
    )
    opening = get_chat_repository(request).create_opening_assistant_message(
        thread["_id"], payload.user_id, profile.get("opening_message", "")
    )
    if opening is None:
        get_chat_repository(request).delete_conversation(thread["_id"], payload.user_id)
        raise HTTPException(status_code=500, detail="无法创建开场消息")
    return ConversationResponse.from_document(
        get_chat_repository(request).get_conversation(thread["_id"], payload.user_id)
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_thread(request, conversation_id, user_id)
    return [
        ChatMessageResponse.from_document(item)
        for item in get_chat_repository(request).list_messages(conversation_id, user_id)
    ]


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    request: Request,
    payload: PlaygroundConversationUpdate,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_thread(request, conversation_id, user_id)
    updated = get_chat_repository(request).update_conversation(
        conversation_id, user_id, payload.model_dump()
    )
    return ConversationResponse.from_document(updated)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_thread(request, conversation_id, user_id)
    get_chat_repository(request).delete_conversation(conversation_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/active-message/{message_id}",
    response_model=ConversationResponse,
)
def activate_message(
    conversation_id: str,
    message_id: str,
    request: Request,
    payload: PlaygroundActiveMessageUpdate,
):
    _owned_thread(request, conversation_id, payload.user_id)
    thread = get_chat_repository(request).set_active_message(
        conversation_id, payload.user_id, message_id
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="会话或消息不存在")
    return ConversationResponse.from_document(thread)


@router.post(
    "/conversations/{conversation_id}/branches",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_branch(
    conversation_id: str,
    request: Request,
    payload: PlaygroundConversationBranchCreate,
):
    _owned_thread(request, conversation_id, payload.user_id)
    result = get_chat_repository(request).create_branch_conversation_with_map(
        conversation_id,
        payload.user_id,
        payload.source_message_id,
        payload.title,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="会话或来源消息不存在")
    branch, message_map = result
    source_summary = get_playground_repository(request).get_summary(
        conversation_id, payload.user_id
    )
    boundary = source_summary.get("summarized_through_message_id")
    if source_summary.get("content") and boundary and str(boundary) in message_map:
        trigger = source_summary.get("last_trigger_message_id")
        mapped_trigger = message_map.get(str(trigger)) or branch.get("active_message_id")
        get_playground_repository(request).save_summary(
            branch["_id"],
            payload.user_id,
            {
                **{
                    key: source_summary.get(key)
                    for key in (
                        "content",
                        "trigger_new_message_count",
                        "retain_recent_message_count",
                        "provider_id",
                        "model",
                        "injection_position",
                    )
                },
                "status": "idle",
                "summarized_through_message_id": message_map[str(boundary)],
                "last_trigger_message_id": mapped_trigger,
                "last_error": None,
            },
        )
    elif source_summary.get("content"):
        get_playground_repository(request).save_summary(
            branch["_id"],
            payload.user_id,
            {
                "content": "",
                "status": "stale",
                "summarized_through_message_id": None,
                "last_trigger_message_id": None,
            },
        )
    return ConversationResponse.from_document(branch)


@router.patch(
    "/conversations/{conversation_id}/opening-message",
    response_model=ChatMessageResponse,
)
def edit_opening_message(
    conversation_id: str,
    request: Request,
    payload: PlaygroundOpeningMessageUpdate,
):
    _owned_thread(request, conversation_id, payload.user_id)
    message = get_chat_repository(request).edit_opening_assistant_message(
        conversation_id, payload.user_id, payload.message_id, payload.content
    )
    if message is None:
        raise HTTPException(status_code=404, detail="开场消息不存在")
    return ChatMessageResponse.from_document(message)


@router.get(
    "/conversations/{conversation_id}/summary",
    response_model=ConversationSummaryResponse,
)
def get_summary(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_thread(request, conversation_id, user_id)
    return get_playground_repository(request).get_summary(conversation_id, user_id)


@router.put(
    "/conversations/{conversation_id}/summary",
    response_model=ConversationSummaryResponse,
)
def update_summary(
    conversation_id: str,
    request: Request,
    payload: ConversationSummaryUpdate,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_thread(request, conversation_id, user_id)
    return get_playground_repository(request).save_summary(
        conversation_id, user_id, payload.model_dump(exclude_unset=True)
    )


@router.post(
    "/conversations/{conversation_id}/summary/refresh",
    response_model=ConversationSummaryResponse,
)
async def refresh_summary(
    conversation_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    thread = _owned_thread(request, conversation_id, user_id)
    profile = _owned_profile(request, str(thread["owner_id"]), user_id, thread["owner_type"])
    return await PlaygroundSummarizer(
        get_chat_repository(request), get_playground_repository(request)
    ).refresh(thread, profile, get_playground_repository(request).get_preferences(user_id))


@router.post("/conversations/{conversation_id}/messages/{message_id}/edit")
async def edit_message(
    conversation_id: str,
    message_id: str,
    request: Request,
    payload: PlaygroundEditStreamRequest,
):
    if payload.conversation_id != conversation_id or payload.message_id != message_id:
        raise HTTPException(status_code=400, detail="请求路径与消息参数不一致")
    from AgentBI.src.api.playground_chat import edit_stream

    return await edit_stream(request, payload)


@router.post("/conversations/{conversation_id}/messages/{message_id}/retry")
async def retry_message(
    conversation_id: str,
    message_id: str,
    request: Request,
    payload: PlaygroundRetryStreamRequest,
):
    if payload.conversation_id != conversation_id or payload.message_id != message_id:
        raise HTTPException(status_code=400, detail="请求路径与消息参数不一致")
    from AgentBI.src.api.playground_chat import retry_stream

    return await retry_stream(request, payload)
