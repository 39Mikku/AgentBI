import sqlite3

from fastapi import APIRouter, HTTPException, Query, Request

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.user_profile_schema import HomeQuotesUpdate, UserAvatarUpdate, UserNameUpdate, UserProfileResponse

router = APIRouter(prefix="/user-profile", tags=["user-profile"])


@router.put("/quotes", response_model=UserProfileResponse)
def save_home_quotes(
    request: Request,
    payload: HomeQuotesUpdate,
    user_id: str = Query(min_length=1, max_length=200),
):
    repository = get_chat_repository(request)
    user = repository.update_user(user_id, payload.model_dump())
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserProfileResponse.from_documents(user_id, user, user)


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


@router.put("", response_model=UserProfileResponse)
def save_user_name(
    request: Request,
    payload: UserNameUpdate,
    user_id: str = Query(min_length=1, max_length=200),
):
    repository = get_chat_repository(request)
    try:
        user = repository.update_user(user_id, {"username": payload.username.strip()})
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="用户名已被使用") from error
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserProfileResponse.from_documents(user_id, user, user)
