from fastapi import HTTPException, Request

from AgentBI.src.repositories.chat_repository import ChatRepository


def get_chat_repository(request: Request) -> ChatRepository:
    repository = getattr(request.app.state, "chat_repository", None)
    if not repository:
        raise HTTPException(status_code=503, detail="聊天数据库尚未初始化")
    return repository
