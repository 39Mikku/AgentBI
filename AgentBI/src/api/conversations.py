from fastapi import APIRouter, HTTPException, Query, Request, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.chat_schema import (
    ChatPreferencesResponse,
    ChatPreferencesUpdate,
    ChatMessageResponse,
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
def list_conversations(request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    return [ConversationResponse.from_document(item) for item in repository.list_conversations(user_id)]


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(request: Request, payload: ConversationCreate):
    document = payload.model_dump()
    document["title"] = document["title"] or "未命名会话"
    return ConversationResponse.from_document(get_chat_repository(request).create_conversation(document))


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(conversation_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    conversation = repository.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return [ChatMessageResponse.from_document(item) for item in repository.list_messages(conversation_id, user_id)]


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
