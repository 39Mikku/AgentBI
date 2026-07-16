from fastapi import APIRouter, HTTPException, Query, Request

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.model_capability_schema import (
    ModelCapabilityResponse,
    ModelCapabilityUpdate,
)


router = APIRouter(prefix="/model-capabilities", tags=["model-capabilities"])


@router.get("", response_model=list[ModelCapabilityResponse])
def list_model_capabilities(request: Request, user_id: str = Query(min_length=1)):
    return get_chat_repository(request).list_model_capabilities(user_id)


@router.put("", response_model=ModelCapabilityResponse)
def save_model_capability(
    request: Request,
    payload: ModelCapabilityUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    if not repository.get_provider(payload.provider_id):
        raise HTTPException(status_code=404, detail="模型提供商不存在")
    return repository.set_model_capability(
        user_id,
        payload.provider_id,
        payload.model,
        supports_vision=payload.supports_vision,
    )
