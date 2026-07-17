from fastapi import HTTPException, Request

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository


def get_chat_repository(request: Request) -> SqliteChatRepository:
    repository = getattr(request.app.state, "chat_repository", None)
    if not repository:
        raise HTTPException(status_code=503, detail="聊天数据库尚未初始化")
    return repository


def get_playground_repository(request: Request) -> SqlitePlaygroundRepository:
    repository = getattr(request.app.state, "playground_repository", None)
    if repository is None:
        raise HTTPException(status_code=503, detail="Playground 数据库尚未初始化")
    return repository
