from fastapi import APIRouter, HTTPException, Query, Request, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.assistant_schema import AssistantCreate, AssistantResponse, AssistantUpdate

router = APIRouter(tags=["assistants"])


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
