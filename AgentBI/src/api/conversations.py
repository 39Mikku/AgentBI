from fastapi import APIRouter, HTTPException, Query, Request, status

from AgentBI.src.api.chat import edit_stream, retry_stream
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.chat_schema import (
    ActiveMessageUpdate,
    ChatPreferencesResponse,
    ChatPreferencesUpdate,
    ChatMessageResponse,
    ChatEditStreamRequest,
    ChatRetryStreamRequest,
    ConversationBranchCreate,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
)

router = APIRouter(tags=["conversations"])


@router.get("/chat/preferences", response_model=ChatPreferencesResponse)
def get_preferences(request: Request, user_id: str = Query(min_length=1)):
    return ChatPreferencesResponse.from_document(get_chat_repository(request).get_preferences(user_id))


@router.put("/chat/preferences", response_model=ChatPreferencesResponse)
def save_preferences(request: Request, payload: ChatPreferencesUpdate, user_id: str = Query(min_length=1)):
    return ChatPreferencesResponse.from_document(
        get_chat_repository(request).save_preferences(user_id, payload.model_dump())
    )


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(request: Request, user_id: str = Query(min_length=1), assistant_id: str | None = None):
    repository = get_chat_repository(request)
    return [ConversationResponse.from_document(item) for item in repository.list_conversations(user_id, assistant_id)]


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(request: Request, payload: ConversationCreate):
    repository = get_chat_repository(request)
    document = payload.model_dump()
    document["title"] = document["title"] or "未命名会话"
    assistant = repository.get_assistant(document.get("assistant_id"), payload.user_id) if document.get("assistant_id") else repository.ensure_default_assistant(payload.user_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="助手不存在")
    document["assistant_id"] = assistant["_id"]
    return ConversationResponse.from_document(repository.create_conversation(document))


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(conversation_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    conversation = repository.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return [ChatMessageResponse.from_document(item) for item in repository.list_messages(conversation_id, user_id)]


@router.post("/conversations/{conversation_id}/branches", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_branch(conversation_id: str, request: Request, payload: ConversationBranchCreate):
    branch = get_chat_repository(request).create_branch_conversation(
        conversation_id,
        payload.user_id,
        payload.source_message_id,
        payload.title,
    )
    if not branch:
        raise HTTPException(status_code=404, detail="会话或来源消息不存在")
    return ConversationResponse.from_document(branch)


@router.post("/conversations/{conversation_id}/active-message/{message_id}", response_model=ConversationResponse)
def activate_message(conversation_id: str, message_id: str, request: Request, payload: ActiveMessageUpdate):
    thread = get_chat_repository(request).set_active_message(conversation_id, payload.user_id, message_id)
    if not thread:
        raise HTTPException(status_code=404, detail="会话或消息不存在")
    return ConversationResponse.from_document(thread)


@router.post("/conversations/{conversation_id}/messages/{message_id}/edit")
async def edit_message(conversation_id: str, message_id: str, request: Request, payload: ChatEditStreamRequest):
    if payload.conversation_id != conversation_id or payload.message_id != message_id:
        raise HTTPException(status_code=400, detail="请求路径与消息参数不一致")
    return await edit_stream(request, payload)


@router.post("/conversations/{conversation_id}/messages/{message_id}/retry")
async def retry_message(conversation_id: str, message_id: str, request: Request, payload: ChatRetryStreamRequest):
    if payload.conversation_id != conversation_id or payload.message_id != message_id:
        raise HTTPException(status_code=400, detail="请求路径与消息参数不一致")
    return await retry_stream(request, payload)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: str, request: Request, user_id: str, payload: ConversationUpdate):
    updated = get_chat_repository(request).update_conversation(conversation_id, user_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ConversationResponse.from_document(updated)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, request: Request, user_id: str = Query(min_length=1)):
    if not get_chat_repository(request).delete_conversation(conversation_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
