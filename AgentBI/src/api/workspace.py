from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.user_profile_schema import UserProfileResponse

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceSelection(BaseModel):
    user_id: str = Field(min_length=1, max_length=320)


class WorkspaceResponse(BaseModel):
    profile: UserProfileResponse | None
    profiles: list[UserProfileResponse]


def workspace_response(request: Request, user_id: str | None = None) -> WorkspaceResponse:
    try:
        selected, users = get_chat_repository(request).bootstrap_workspace(user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="本地资料不存在，请重新选择") from error
    return WorkspaceResponse(
        profile=UserProfileResponse.from_documents(selected["user_id"], selected, selected) if selected else None,
        profiles=[UserProfileResponse.from_documents(user["user_id"], user, user) for user in users],
    )


@router.get("", response_model=WorkspaceResponse)
def get_workspace(request: Request):
    return workspace_response(request)


@router.put("", response_model=WorkspaceResponse)
def select_workspace(request: Request, payload: WorkspaceSelection):
    return workspace_response(request, payload.user_id)
