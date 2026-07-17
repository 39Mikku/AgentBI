import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from AgentBI.src.api.api import router
from AgentBI.src.api.chat import router as chat_router
from AgentBI.src.api.conversations import router as conversation_router
from AgentBI.src.api.providers import router as provider_router
from AgentBI.src.api.user_profile import router as user_profile_router
from AgentBI.src.api.model_routes import router as model_route_router
from AgentBI.src.api.model_capabilities import router as model_capability_router
from AgentBI.src.api.assistants import router as assistant_router
from AgentBI.src.api.music import router as music_router
from AgentBI.src.api.capability_settings import router as capability_settings_router
from AgentBI.src.api.live import router as live_router
from AgentBI.src.api.toolbox_tts import router as toolbox_tts_router
from AgentBI.src.api.toolbox_system import router as toolbox_system_router
from AgentBI.src.api.toolbox_file_time import router as toolbox_file_time_router
from AgentBI.src.api.toolbox_auto_input import router as toolbox_auto_input_router
from AgentBI.src.api.toolbox_moegirl import router as toolbox_moegirl_router
from AgentBI.src.api.toolbox_emoji import router as toolbox_emoji_router
from AgentBI.src.api.tests import router as tests_router
from AgentBI.src.api.image_generation import router as image_generation_router
from AgentBI.src.api.studio_assets import router as studio_asset_router
from AgentBI.src.api.video_generation import router as video_generation_router
from AgentBI.src.api.playground_profiles import router as playground_profiles_router
from AgentBI.src.api.playground_conversations import router as playground_conversations_router
from AgentBI.src.api.playground_chat import router as playground_chat_router
from AgentBI.src.logging.logging import Logger
from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository
from AgentBI.src.repositories.sqlite_test_repository import SqliteTestRepository
from AgentBI.src.services.music_api_process import MusicApiProcessManager
from AgentBI.src.services.test_model_service import TestModelService
from AgentBI.src.services.test_service import TestService
from AgentBI.src.services.toolbox.tts.registry import TtsProviderRegistry
from AgentBI.src.services.toolbox.tts.bailian_voice_enrollment import BailianLiveVoiceEnrollmentAdapter
from AgentBI.src.services.toolbox.directory_picker import NativeDirectoryPicker
from AgentBI.src.services.toolbox.file_time.service import FileTimeService
from AgentBI.src.services.toolbox.auto_input.service import AutoInputService
from AgentBI.src.services.image_generation.artifact_store import ImageArtifactStore
from AgentBI.src.services.image_generation.codex_oauth import CodexOAuthManager, CodexOAuthTokenStore
from AgentBI.src.services.image_generation.service import ImageGenerationService
from AgentBI.src.services.studio_asset_service import StudioAssetService
from AgentBI.src.services.video_generation import (
    AgnesVideoClient,
    ArkVideoClient,
    VideoGenerationService,
)

logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    sqlite_path = os.getenv("CHAT_SQLITE_PATH") or str(Path(__file__).resolve().parent / "data" / "agentbi.sqlite3")
    app.state.chat_repository = SqliteChatRepository(sqlite_path)
    app.state.playground_repository = SqlitePlaygroundRepository.from_connection_owner(
        app.state.chat_repository
    )
    app.state.test_repository = SqliteTestRepository(sqlite_path)
    app.state.test_model_service = TestModelService(
        app.state.test_repository, app.state.chat_repository
    )
    app.state.test_service = TestService(
        app.state.test_repository,
        app.state.chat_repository,
        app.state.test_model_service,
    )
    app.state.test_service.recover_stale_work()
    app.state.tts_provider_registry = TtsProviderRegistry.from_environment()
    app.state.live_voice_enrollment_adapter = BailianLiveVoiceEnrollmentAdapter(
        api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        workspace_id=os.getenv("DASHSCOPE_WORKSPACE_ID", ""),
    )
    app.state.directory_picker = NativeDirectoryPicker()
    app.state.file_time_service = FileTimeService()
    app.state.auto_input_service = AutoInputService()
    image_root = Path(__file__).resolve().parent / "data" / "generated-images"
    app.state.studio_asset_service = StudioAssetService(
        app.state.chat_repository,
        Path(__file__).resolve().parent / "data" / "chat-attachments",
        generated_root=image_root,
    )
    oauth_store = CodexOAuthTokenStore(
        Path(__file__).resolve().parent / "data" / "codex-image-oauth.json"
    )
    app.state.codex_image_oauth = CodexOAuthManager(oauth_store)
    app.state.image_generation_service = ImageGenerationService(
        repository=app.state.chat_repository,
        artifact_store=ImageArtifactStore(image_root, public_prefix="/api/generated-images"),
        oauth_store=oauth_store,
        asset_service=app.state.studio_asset_service,
    )
    app.state.video_generation_service = VideoGenerationService(
        repository=app.state.chat_repository,
        providers={
            "agnes": AgnesVideoClient(
                api_key=os.getenv("AGNES_API_KEY", ""),
                base_url=os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com"),
            ),
            "volcengine": ArkVideoClient(
                api_key=os.getenv("ARK_API_KEY", ""),
                base_url=os.getenv(
                    "ARK_VIDEO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
                ),
            ),
        },
        output_root=image_root,
        asset_service=app.state.studio_asset_service,
    )
    await app.state.video_generation_service.start()
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
        await app.state.video_generation_service.shutdown()
        app.state.test_repository.close()
        app.state.chat_repository.close()
        logger.info("销毁 AgentBI 服务生命周期")


app = FastAPI(lifespan=lifespan)
_generated_image_root = Path(__file__).resolve().parent / "data" / "generated-images"
_generated_image_root.mkdir(parents=True, exist_ok=True)
app.mount("/generated-images", StaticFiles(directory=_generated_image_root), name="generated-images")
app.include_router(router)
app.include_router(provider_router)
app.include_router(user_profile_router)
app.include_router(model_route_router)
app.include_router(model_capability_router)
app.include_router(assistant_router)
app.include_router(conversation_router)
app.include_router(chat_router)
app.include_router(music_router)
app.include_router(capability_settings_router)
app.include_router(live_router)
app.include_router(toolbox_tts_router)
app.include_router(toolbox_system_router)
app.include_router(toolbox_file_time_router)
app.include_router(toolbox_auto_input_router)
app.include_router(toolbox_moegirl_router)
app.include_router(toolbox_emoji_router)
app.include_router(tests_router)
app.include_router(image_generation_router)
app.include_router(studio_asset_router)
app.include_router(video_generation_router)
app.include_router(playground_profiles_router)
app.include_router(playground_conversations_router)
app.include_router(playground_chat_router)


@app.get("/")
def read_root():
    return {"status": "success", "message": "AgentBI 服务已启动，请访问 /docs。"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
