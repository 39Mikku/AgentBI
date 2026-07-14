from fastapi import APIRouter, Query, Request

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.user_profile_schema import UserAvatarUpdate, UserProfileResponse

router = APIRouter(prefix="/user-profile", tags=["user-profile"])


@router.get("", response_model=UserProfileResponse)
def get_user_profile(request: Request, user_id: str = Query(min_length=1, max_length=200)):
    repository = get_chat_repository(request)
    user, profile = repository.get_user_profile(user_id)
    return UserProfileResponse.from_documents(user_id, user, profile)


@router.put("/avatar", response_model=UserProfileResponse)
def save_user_avatar(
    request: Request,
    payload: UserAvatarUpdate,
    user_id: str = Query(min_length=1, max_length=200),
):
    repository = get_chat_repository(request)
    user, profile = repository.save_user_avatar(user_id, payload.avatar_data_url)
    return UserProfileResponse.from_documents(user_id, user, profile)
