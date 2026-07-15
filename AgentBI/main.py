import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from AgentBI.src.api.api import router
from AgentBI.src.api.chat import router as chat_router
from AgentBI.src.api.conversations import router as conversation_router
from AgentBI.src.api.providers import router as provider_router
from AgentBI.src.api.user_profile import router as user_profile_router
from AgentBI.src.api.model_routes import router as model_route_router
from AgentBI.src.api.assistants import router as assistant_router
from AgentBI.src.api.music import router as music_router
from AgentBI.src.logging.logging import Logger
from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.music_api_process import MusicApiProcessManager

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    sqlite_path = os.getenv("CHAT_SQLITE_PATH") or str(Path(__file__).resolve().parent / "data" / "agentbi.sqlite3")
    app.state.chat_repository = SqliteChatRepository(sqlite_path)
    music_process = MusicApiProcessManager(
        enabled=os.getenv("NCM_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"},
        port=int(os.getenv("NCM_API_PORT", "3300")),
        startup_timeout=float(os.getenv("NCM_STARTUP_TIMEOUT_SECONDS", "15")),
    )
    app.state.music_api_process = music_process
    try:
        await music_process.start()
    except Exception as exc:
        logger.warning("网易云音乐内部服务不可用，主服务继续启动: %s", type(exc).__name__)
    logger.info("创建 AgentBI 服务生命周期")
    try:
        yield
    finally:
        await music_process.stop()
        app.state.chat_repository.close()
        logger.info("销毁 AgentBI 服务生命周期")


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.include_router(provider_router)
app.include_router(user_profile_router)
app.include_router(model_route_router)
app.include_router(assistant_router)
app.include_router(conversation_router)
app.include_router(chat_router)
app.include_router(music_router)


@app.get("/")
def read_root():
    return {"status": "success", "message": "AgentBI 服务已启动，请访问 /docs。"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
