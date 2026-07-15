from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from AgentBI.src.agents.assistant_registry import CAPABILITIES
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.capability_settings_schema import (
    CAPABILITY_CONFIG_FIELDS,
    CapabilitySettingsResponse,
    CapabilitySettingsUpdate,
    resolve_capability_config,
)

router = APIRouter(tags=["capability-settings"])


def validate_capability_config(capability_id: str, config: dict[str, Any]) -> dict[str, Any]:
    if capability_id not in CAPABILITIES:
        raise HTTPException(status_code=404, detail="能力不存在")
    try:
        return resolve_capability_config(capability_id, config)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error


def _response(repository: Any, user_id: str, capability_id: str) -> CapabilitySettingsResponse:
    capability = CAPABILITIES.get(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="能力不存在")
    config = validate_capability_config(
        capability_id,
        repository.get_capability_config(user_id, capability_id) or {},
    )
    return CapabilitySettingsResponse(
        capability_id=capability_id,
        display_name=capability["name"],
        description=capability["description"],
        kind=capability["kind"],
        config=config,
        fields=CAPABILITY_CONFIG_FIELDS.get(capability_id, []),
    )


@router.get("/capabilities/settings", response_model=list[CapabilitySettingsResponse])
def list_capability_settings(request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    return [_response(repository, user_id, capability_id) for capability_id in CAPABILITIES]


@router.put("/capabilities/{capability_id}/settings", response_model=CapabilitySettingsResponse)
def save_capability_settings(
    capability_id: str,
    request: Request,
    payload: CapabilitySettingsUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    config = validate_capability_config(capability_id, payload.config)
    repository.save_capability_config(user_id, capability_id, config)
    return _response(repository, user_id, capability_id)
