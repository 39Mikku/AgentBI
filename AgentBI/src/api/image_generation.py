from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.image_generation_schema import (
    CodexOAuthStartResponse,
    CodexOAuthStatus,
    GeneratedImage,
    ImageGenerationRequest,
)
from AgentBI.src.services.image_generation.codex_oauth import CodexOAuthError
from AgentBI.src.services.image_generation.lite_adapter import ImageGenerationError


router = APIRouter(prefix="/image-generation", tags=["image-generation"])


def _service(request: Request):
    service = getattr(request.app.state, "image_generation_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="图片生成服务尚未初始化")
    return service


def _oauth(request: Request):
    manager = getattr(request.app.state, "codex_image_oauth", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Codex OAuth 服务尚未初始化")
    return manager


@router.post("/generate", response_model=GeneratedImage)
async def generate_image(request: Request, payload: ImageGenerationRequest):
    repository = get_chat_repository(request)
    provider = None
    if payload.provider_id:
        provider = repository.get_provider(payload.provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="模型提供商不存在")
    try:
        return await _service(request).generate(
            user_id=payload.user_id,
            scope_id=payload.scope_id or "direct",
            prompt=payload.prompt,
            aspect_ratio=payload.aspect_ratio,
            provider=provider,
            reference_image_data_url=payload.reference_image_data_url,
        )
    except (ImageGenerationError, CodexOAuthError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/codex/status", response_model=CodexOAuthStatus)
def codex_status(request: Request):
    return _oauth(request).status()


@router.post("/codex/connect", response_model=CodexOAuthStartResponse)
async def connect_codex(request: Request):
    try:
        return await _oauth(request).start()
    except CodexOAuthError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/codex/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_codex(request: Request):
    _oauth(request).disconnect()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
