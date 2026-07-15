from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from AgentBI.src.agents.assistant_registry import SUBAGENTS
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.subagent_settings_schema import (
    SUBAGENT_CONFIG_FIELDS,
    SubagentSettingsResponse,
    SubagentSettingsUpdate,
    resolve_subagent_config,
)

router = APIRouter(tags=["subagent-settings"])


def _registration(capability_id: str):
    return next((item for item in SUBAGENTS if item.capability_id == capability_id), None)


def validate_subagent_config(capability_id: str, config: dict[str, Any]) -> dict[str, Any]:
    if not _registration(capability_id):
        raise HTTPException(status_code=404, detail="子代理不存在")
    try:
        return resolve_subagent_config(capability_id, config)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error


def _response(repository: Any, user_id: str, capability_id: str) -> SubagentSettingsResponse:
    registration = _registration(capability_id)
    if not registration:
        raise HTTPException(status_code=404, detail="子代理不存在")
    config = validate_subagent_config(
        capability_id,
        repository.get_subagent_config(user_id, capability_id) or {},
    )
    return SubagentSettingsResponse(
        capability_id=capability_id,
        display_name=registration.display_name,
        description=registration.description,
        config=config,
        fields=SUBAGENT_CONFIG_FIELDS.get(capability_id, []),
    )


@router.get("/subagents/settings", response_model=list[SubagentSettingsResponse])
def list_subagent_settings(request: Request, user_id: str = Query(min_length=1)):
    repository = get_chat_repository(request)
    return [_response(repository, user_id, item.capability_id) for item in SUBAGENTS]


@router.put("/subagents/{capability_id}/settings", response_model=SubagentSettingsResponse)
def save_subagent_settings(
    capability_id: str,
    request: Request,
    payload: SubagentSettingsUpdate,
    user_id: str = Query(min_length=1),
):
    repository = get_chat_repository(request)
    config = validate_subagent_config(capability_id, payload.config)
    repository.save_subagent_config(user_id, capability_id, config)
    return _response(repository, user_id, capability_id)
