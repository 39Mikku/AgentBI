from fastapi import APIRouter, HTTPException, Request, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.provider_schema import ProviderProfileCreate, ProviderProfileResponse, ProviderProfileUpdate
from AgentBI.src.services.provider_service import ProviderService

router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=list[ProviderProfileResponse])
def list_providers(request: Request):
    repository = get_chat_repository(request)
    return [ProviderProfileResponse.from_document(item) for item in repository.list_providers()]


@router.post("/providers", response_model=ProviderProfileResponse, status_code=status.HTTP_201_CREATED)
def create_provider(request: Request, payload: ProviderProfileCreate):
    repository = get_chat_repository(request)
    return ProviderProfileResponse.from_document(repository.create_provider(payload.model_dump()))


@router.patch("/providers/{provider_id}", response_model=ProviderProfileResponse)
def update_provider(provider_id: str, request: Request, payload: ProviderProfileUpdate):
    repository = get_chat_repository(request)
    updated = repository.update_provider(provider_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="提供商不存在")
    return ProviderProfileResponse.from_document(updated)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: str, request: Request):
    if not get_chat_repository(request).delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="提供商不存在")


@router.post("/providers/{provider_id}/refresh-models", response_model=ProviderProfileResponse)
async def refresh_models(provider_id: str, request: Request):
    service = ProviderService(get_chat_repository(request))
    try:
        provider = await service.refresh_models(provider_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"模型列表获取失败: {error}") from error
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")
    return ProviderProfileResponse.from_document(provider)
