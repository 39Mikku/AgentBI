from fastapi import APIRouter, HTTPException, Request

from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.schemas.toolbox_emoji_schema import (
    StickerNamingRequest,
    StickerNamingResponse,
)
from AgentBI.src.services.model_task_service import (
    ModelTaskConfigurationError,
    ModelTaskEmptyResponseError,
    ModelTaskService,
)
from AgentBI.src.services.toolbox.emoji_naming import StickerNamingService


router = APIRouter(prefix="/toolbox/emoji", tags=["toolbox-emoji"])


def _service(request: Request) -> StickerNamingService:
    service = getattr(request.app.state, "emoji_naming_service", None)
    if service is None:
        service = StickerNamingService(ModelTaskService(get_chat_repository(request)))
        request.app.state.emoji_naming_service = service
    return service


@router.post("/name", response_model=StickerNamingResponse)
async def name_stickers(request: Request, payload: StickerNamingRequest):
    try:
        return await _service(request).name(
            user_id=payload.user_id,
            strategy=payload.strategy,
            images=[image.model_dump() for image in payload.images],
        )
    except ModelTaskConfigurationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ModelTaskEmptyResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="识图模型命名失败，请稍后重试") from error
