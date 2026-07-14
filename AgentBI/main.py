import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from AgentBI.src.agents.login_agent import LoginAgent
from AgentBI.src.api.api import router
from AgentBI.src.api.chat import router as chat_router
from AgentBI.src.api.conversations import router as conversation_router
from AgentBI.src.api.providers import router as provider_router
from AgentBI.src.logging.logging import Logger
from AgentBI.src.repositories.chat_repository import ChatRepository
from pymongo import MongoClient

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.login_agent = LoginAgent()
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        client = MongoClient(mongo_uri)
        app.state.mongo_client = client
        app.state.chat_repository = ChatRepository(client[os.getenv("MONGO_DATABASE", "chat_bi")])
        app.state.chat_repository.ensure_indexes()
    else:
        app.state.chat_repository = None
    logger.info("创建 AgentBI 服务生命周期")
    yield
    if getattr(app.state, "mongo_client", None):
        app.state.mongo_client.close()
    logger.info("销毁 AgentBI 服务生命周期")


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.include_router(provider_router)
app.include_router(conversation_router)
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"status": "success", "message": "AgentBI 服务已启动，请访问 /docs。"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
