from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import ValidationError

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.toolbox_tts_schema import (
    LiveVoiceEnrollmentRequest,
    TtsCapabilityResponse,
    TtsSynthesisRequest,
    TtsVoiceCreate,
    TtsVoiceResponse,
    TtsVoiceUpdate,
    VoiceScriptGenerateRequest,
    VoiceScriptGenerateResponse,
)
from AgentBI.src.services.model_task_service import (
    ModelTaskConfigurationError,
    ModelTaskEmptyResponseError,
    ModelTaskService,
)
from AgentBI.src.services.toolbox.tts.bailian_voice_enrollment import (
    BailianLiveVoiceEnrollmentAdapter,
)
from AgentBI.src.services.toolbox.tts.base import (
    TtsConfigurationError,
    TtsProviderError,
    TtsValidationError,
)
from AgentBI.src.services.toolbox.tts.registry import TtsProviderRegistry


router = APIRouter(prefix="/toolbox/tts", tags=["toolbox-tts"])

VOICE_SCRIPT_SYSTEM_PROMPT = """你是专业的中文配音文案作者。根据用户要求直接生成可朗读的最终正文。
只输出正文，不要标题、解释、分析、Markdown、代码块、引号包裹，也不要使用“好的”“以下是”等开场语。"""


def get_tts_provider_registry(request: Request) -> TtsProviderRegistry:
    registry = getattr(request.app.state, "tts_provider_registry", None)
    if registry is None:
        registry = TtsProviderRegistry.from_environment()
        request.app.state.tts_provider_registry = registry
    return registry


def get_live_voice_enrollment_adapter(request: Request) -> BailianLiveVoiceEnrollmentAdapter:
    adapter = getattr(request.app.state, "live_voice_enrollment_adapter", None)
    if adapter is None:
        registry = get_tts_provider_registry(request)
        adapter = BailianLiveVoiceEnrollmentAdapter(
            api_key=registry.environment.get("DASHSCOPE_API_KEY", ""),
            workspace_id=registry.environment.get("DASHSCOPE_WORKSPACE_ID", ""),
        )
        request.app.state.live_voice_enrollment_adapter = adapter
    return adapter


def get_model_task_service(request: Request) -> ModelTaskService:
    service = getattr(request.app.state, "model_task_service", None)
    if service is None:
        service = ModelTaskService(get_chat_repository(request))
        request.app.state.model_task_service = service
    return service


@router.get("/capabilities", response_model=TtsCapabilityResponse)
def list_tts_capabilities(request: Request):
    return {"providers": get_tts_provider_registry(request).capabilities()}


@router.post("/script/generate", response_model=VoiceScriptGenerateResponse)
async def generate_voice_script(request: Request, payload: VoiceScriptGenerateRequest):
    try:
        result = await get_model_task_service(request).complete_with_chat_preferences(
            payload.user_id,
            VOICE_SCRIPT_SYSTEM_PROMPT,
            payload.instruction,
        )
    except ModelTaskConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelTaskEmptyResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"文案生成失败：{exc}") from exc

    return VoiceScriptGenerateResponse(
        text=result.text.strip()[:10000],
        provider_name=result.provider_name,
        model=result.model,
    )


@router.get("/voices", response_model=list[TtsVoiceResponse])
def list_tts_voices(request: Request, user_id: str = Query(min_length=1, max_length=320)):
    return get_chat_repository(request).list_toolbox_tts_voices(user_id)


@router.post("/voices", response_model=TtsVoiceResponse, status_code=status.HTTP_201_CREATED)
def create_tts_voice(request: Request, payload: TtsVoiceCreate):
    return get_chat_repository(request).create_toolbox_tts_voice(payload.model_dump())


@router.post(
    "/voices/enroll-live",
    response_model=TtsVoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_live_voice(request: Request, payload: LiveVoiceEnrollmentRequest):
    try:
        result = await get_live_voice_enrollment_adapter(request).enroll(payload)
    except TtsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TtsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TtsProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return get_chat_repository(request).create_toolbox_tts_voice(
        {
            "user_id": payload.user_id,
            "provider": "bailian",
            "display_name": payload.display_name,
            "external_voice_id": result.voice_id,
            "voice_kind": "cloned",
            "bound_model": payload.target_model,
            "provider_metadata": {
                "usage": "live",
                "prefix": payload.prefix,
                "request_id": result.request_id,
            },
        }
    )


@router.put("/voices/{voice_id}", response_model=TtsVoiceResponse)
def update_tts_voice(
    request: Request,
    voice_id: str,
    payload: TtsVoiceUpdate,
    user_id: str = Query(min_length=1, max_length=320),
):
    repository = get_chat_repository(request)
    current = repository.get_toolbox_tts_voice(voice_id, user_id)
    if current is None:
        raise HTTPException(status_code=404, detail="音色不存在")
    changes = payload.model_dump(exclude_unset=True)
    candidate = {**current, **changes}
    try:
        TtsVoiceCreate.model_validate(
            {
                key: candidate[key]
                for key in (
                    "user_id",
                    "provider",
                    "display_name",
                    "external_voice_id",
                    "voice_kind",
                    "bound_model",
                    "provider_metadata",
                )
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="音色与绑定模型不兼容") from exc
    updated = repository.update_toolbox_tts_voice(voice_id, user_id, changes)
    if updated is None:
        raise HTTPException(status_code=404, detail="音色不存在")
    return updated


@router.delete("/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tts_voice(
    request: Request,
    voice_id: str,
    user_id: str = Query(min_length=1, max_length=320),
):
    if not get_chat_repository(request).delete_toolbox_tts_voice(voice_id, user_id):
        raise HTTPException(status_code=404, detail="音色不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _validate_saved_voice_binding(request: Request, payload: TtsSynthesisRequest) -> None:
    voices = get_chat_repository(request).list_toolbox_tts_voices(payload.user_id)
    matching = [
        voice
        for voice in voices
        if voice["provider"] == payload.provider and voice["external_voice_id"] == payload.voice_id
    ]
    if matching and not any(not voice.get("bound_model") or voice["bound_model"] == payload.model for voice in matching):
        raise TtsValidationError("该音色绑定了其他模型，不能用于当前模型")


@router.post("/synthesize")
async def synthesize_tts(request: Request, payload: TtsSynthesisRequest):
    try:
        _validate_saved_voice_binding(request, payload)
        adapter = get_tts_provider_registry(request).get(payload.provider)
        result = await adapter.synthesize(payload)
    except TtsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TtsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TtsProviderError as exc:
        if exc.code == "validation_error":
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    metadata = json.dumps(result.metadata, ensure_ascii=True, separators=(",", ":"))
    return Response(
        content=result.audio,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'inline; filename="tts-result.{result.extension}"',
            "X-TTS-Elapsed-Ms": str(result.elapsed_ms),
            "X-TTS-Provider": payload.provider,
            "X-TTS-Model": payload.model,
            "X-TTS-Metadata": metadata,
        },
    )
