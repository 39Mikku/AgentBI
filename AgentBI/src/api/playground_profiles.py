from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from AgentBI.src.api.dependencies import get_chat_repository, get_playground_repository
from AgentBI.src.schemas.playground_schema import (
    ContextEntryList,
    ContextEntryResponse,
    PersonaResponse,
    PersonaUpsert,
    PlaygroundPreferencesResponse,
    PlaygroundPreferencesUpdate,
    PlaygroundProfileCreate,
    PlaygroundProfileResponse,
    PlaygroundProfileUpdate,
    ProfileType,
    PromptModuleList,
    PromptModuleResponse,
)
from AgentBI.src.services.playground.state_templates import list_state_templates


router = APIRouter(prefix="/playground", tags=["playground-profiles"])


def _owned_profile(request: Request, profile_id: str, user_id: str) -> dict[str, Any]:
    profile = get_playground_repository(request).get_profile(profile_id, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="角色或世界不存在")
    return profile


def _validate_image_assets(request: Request, user_id: str, *asset_ids: str | None) -> None:
    repository = get_chat_repository(request)
    for asset_id in asset_ids:
        if not asset_id:
            continue
        asset = repository.get_asset(asset_id, user_id)
        if not asset or asset.get("deleted_at") or asset.get("kind") != "image":
            raise HTTPException(status_code=400, detail="头像或背景必须是当前用户未删除的图片附件")


def _profile_response(document: dict[str, Any]) -> PlaygroundProfileResponse:
    return PlaygroundProfileResponse.from_document(document)


@router.get("/preferences", response_model=PlaygroundPreferencesResponse)
def get_preferences(request: Request, user_id: str = Query(min_length=1, max_length=320)):
    return get_playground_repository(request).get_preferences(user_id)


@router.put("/preferences", response_model=PlaygroundPreferencesResponse)
def save_preferences(
    request: Request,
    payload: PlaygroundPreferencesUpdate,
    user_id: str = Query(min_length=1, max_length=320),
):
    return get_playground_repository(request).save_preferences(user_id, payload.model_dump())


@router.get("/state-templates")
def get_state_templates():
    return {"templates": list_state_templates()}


@router.get("/profiles", response_model=list[PlaygroundProfileResponse])
def list_profiles(
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
    profile_type: ProfileType | None = None,
):
    documents = get_playground_repository(request).list_profiles(user_id, profile_type)
    return [_profile_response(item) for item in documents]


@router.post(
    "/profiles",
    response_model=PlaygroundProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(request: Request, payload: PlaygroundProfileCreate):
    _validate_image_assets(
        request,
        payload.user_id,
        payload.avatar_attachment_id,
        payload.background_attachment_id,
    )
    document = get_playground_repository(request).create_profile(payload.model_dump())
    return _profile_response(document)


@router.get("/profiles/{profile_id}", response_model=PlaygroundProfileResponse)
def get_profile(
    profile_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    return _profile_response(_owned_profile(request, profile_id, user_id))


@router.put("/profiles/{profile_id}", response_model=PlaygroundProfileResponse)
def update_profile(
    profile_id: str,
    request: Request,
    payload: PlaygroundProfileUpdate,
    user_id: str = Query(min_length=1, max_length=320),
):
    current = _owned_profile(request, profile_id, user_id)
    changes = payload.model_dump(exclude_unset=True)
    candidate = {**current, **changes, "user_id": user_id}
    candidate.pop("_id", None)
    candidate.pop("created_at", None)
    candidate.pop("updated_at", None)
    validated = PlaygroundProfileCreate.model_validate(candidate)
    _validate_image_assets(
        request,
        user_id,
        validated.avatar_attachment_id,
        validated.background_attachment_id,
    )
    updated = get_playground_repository(request).update_profile(
        profile_id,
        user_id,
        validated.model_dump(exclude={"user_id"}),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="角色或世界不存在")
    return _profile_response(updated)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    if not get_playground_repository(request).delete_profile_with_conversations(profile_id, user_id):
        raise HTTPException(status_code=404, detail="角色或世界不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profiles/{profile_id}/persona", response_model=PersonaResponse | None)
def get_persona(
    profile_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    return get_playground_repository(request).get_persona(profile_id, user_id)


@router.put("/profiles/{profile_id}/persona", response_model=PersonaResponse)
def save_persona(
    profile_id: str,
    request: Request,
    payload: PersonaUpsert,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    _validate_image_assets(request, user_id, payload.avatar_attachment_id)
    return get_playground_repository(request).upsert_persona(
        profile_id, user_id, payload.model_dump()
    )


@router.get(
    "/profiles/{profile_id}/prompt-modules",
    response_model=list[PromptModuleResponse],
)
def list_prompt_modules(
    profile_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    return [
        PromptModuleResponse.from_document(item)
        for item in get_playground_repository(request).list_prompt_modules(profile_id, user_id)
    ]


@router.put(
    "/profiles/{profile_id}/prompt-modules",
    response_model=list[PromptModuleResponse],
)
def replace_prompt_modules(
    profile_id: str,
    request: Request,
    payload: PromptModuleList,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    documents = get_playground_repository(request).replace_prompt_modules(
        profile_id,
        user_id,
        [item.model_dump(exclude_none=True) for item in payload.items],
    )
    return [PromptModuleResponse.from_document(item) for item in documents]


@router.get(
    "/profiles/{profile_id}/context-entries",
    response_model=list[ContextEntryResponse],
)
def list_context_entries(
    profile_id: str,
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    return [
        ContextEntryResponse.from_document(item)
        for item in get_playground_repository(request).list_context_entries(profile_id, user_id)
    ]


@router.put(
    "/profiles/{profile_id}/context-entries",
    response_model=list[ContextEntryResponse],
)
def replace_context_entries(
    profile_id: str,
    request: Request,
    payload: ContextEntryList,
    user_id: str = Query(min_length=1, max_length=320),
):
    _owned_profile(request, profile_id, user_id)
    documents = get_playground_repository(request).replace_context_entries(
        profile_id,
        user_id,
        [item.model_dump(exclude_none=True) for item in payload.items],
    )
    return [ContextEntryResponse.from_document(item) for item in documents]
