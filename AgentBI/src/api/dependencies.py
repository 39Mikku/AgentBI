from fastapi import HTTPException, Request

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.user_directory import MongoUserDirectory


def get_chat_repository(request: Request) -> SqliteChatRepository:
    repository = getattr(request.app.state, "chat_repository", None)
    if not repository:
        raise HTTPException(status_code=503, detail="聊天数据库尚未初始化")
    return repository


def get_user_directory(request: Request) -> MongoUserDirectory:
    return request.app.state.user_directory
