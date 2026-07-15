from fastapi import APIRouter, HTTPException, Query, Request, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.assistant_schema import (
    AssistantCreate,
    AssistantMemoryResponse,
    AssistantMemoryUpdate,
    AssistantResponse,
    AssistantUpdate,
)
from AgentBI.src.services.memory_service import MemoryService

router = APIRouter(tags=["assistants"])


def owned_assistant(repository, assistant_id: str, user_id: str):
    assistant = repository.get_assistant(assistant_id, user_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="助手不存在")
    return assistant


@router.get("/assistants", response_model=list[AssistantResponse])
def list_assistants(request: Request, user_id: str = Query(min_length=1)):
    return [AssistantResponse.from_document(item) for item in get_chat_repository(request).list_assistants(user_id)]


@router.post("/assistants", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
def create_assistant(request: Request, payload: AssistantCreate):
    return AssistantResponse.from_document(get_chat_repository(request).create_assistant(payload.model_dump()))


@router.patch("/assistants/{assistant_id}", response_model=AssistantResponse)
def update_assistant(assistant_id: str, request: Request, user_id: str, payload: AssistantUpdate):
    assistant = get_chat_repository(request).update_assistant(assistant_id, user_id, payload.model_dump(exclude_unset=True))
    if not assistant:
        raise HTTPException(status_code=404, detail="助手不存在或默认助手不可编辑")
    return AssistantResponse.from_document(assistant)


@router.delete("/assistants/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant(assistant_id: str, request: Request, user_id: str = Query(min_length=1)):
    if not get_chat_repository(request).delete_assistant(assistant_id, user_id):
        raise HTTPException(status_code=409, detail="助手不存在、为默认助手，或仍有关联会话")


@router.get("/assistants/{assistant_id}/memory", response_model=AssistantMemoryResponse)
def get_assistant_memory(assistant_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    owned_assistant(repository, assistant_id, user_id)
    return repository.get_assistant_memory(user_id, assistant_id)


@router.put("/assistants/{assistant_id}/memory", response_model=AssistantMemoryResponse)
def save_assistant_memory(
    assistant_id: str,
    request: Request,
    payload: AssistantMemoryUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    owned_assistant(repository, assistant_id, user_id)
    current = repository.get_assistant_memory(user_id, assistant_id)
    return repository.save_assistant_memory(
        user_id,
        assistant_id,
        payload.summary,
        current.get("last_summarized_message_id"),
    )


@router.delete("/assistants/{assistant_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
def clear_assistant_memory(assistant_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    owned_assistant(repository, assistant_id, user_id)
    repository.clear_assistant_memory(user_id, assistant_id)


@router.post("/assistants/{assistant_id}/memory/refresh", response_model=AssistantMemoryResponse)
async def refresh_assistant_memory(assistant_id: str, request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    assistant = owned_assistant(repository, assistant_id, user_id)
    if not assistant.get("memory_enabled"):
        raise HTTPException(status_code=400, detail="请先启用跨会话记忆")
    await MemoryService(repository).update_memory_if_due(user_id, assistant, force=True)
    return repository.get_assistant_memory(user_id, assistant_id)
