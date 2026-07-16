from __future__ import annotations

from typing import Any

from AgentBI.src.schemas.capability_settings_schema import resolve_capability_config
from AgentBI.src.schemas.image_generation_schema import GeneratedImage
from AgentBI.src.services.image_generation.artifact_store import ImageArtifactStore
from AgentBI.src.services.image_generation.codex_adapter import CodexImageAdapter
from AgentBI.src.services.image_generation.codex_oauth import CodexOAuthTokenStore
from AgentBI.src.services.image_generation.lite_adapter import (
    ImageGenerationError,
    LiteChatImageAdapter,
)


_DIMENSIONS = {
    "square": (1024, 1024),
    "landscape": (1536, 1024),
    "portrait": (1024, 1536),
}


class ImageGenerationService:
    def __init__(
        self,
        *,
        repository: Any,
        artifact_store: ImageArtifactStore,
        oauth_store: CodexOAuthTokenStore,
        lite_adapter: LiteChatImageAdapter | None = None,
        pro_adapter: CodexImageAdapter | None = None,
        asset_service: Any | None = None,
    ):
        self.repository = repository
        self.artifact_store = artifact_store
        self.oauth_store = oauth_store
        self.lite_adapter = lite_adapter or LiteChatImageAdapter()
        self.pro_adapter = pro_adapter or CodexImageAdapter()
        self.asset_service = asset_service

    async def generate(
        self,
        *,
        user_id: str,
        scope_id: str | None,
        prompt: str,
        aspect_ratio: str,
        provider: dict[str, Any] | None = None,
    ) -> GeneratedImage:
        stored = self.repository.get_capability_config(user_id, "tool.image_generation")
        config = resolve_capability_config("tool.image_generation", stored)
        if config["mode"] == "lite":
            if not provider:
                raise ImageGenerationError("Lite 生图需要先选择一个模型提供商")
            binary = await self.lite_adapter.generate(
                provider=provider,
                model=config["lite_model"],
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )
        else:
            access_token = await self.oauth_store.valid_access_token()
            binary = await self.pro_adapter.generate(
                access_token=access_token,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                quality=config["pro_quality"],
            )
        width, height = _DIMENSIONS.get(aspect_ratio, _DIMENSIONS["square"])
        image = self.artifact_store.save(
            user_id=user_id,
            scope_id=scope_id,
            image_bytes=binary.image_bytes,
            media_type=binary.media_type,
            metadata={
                "mode": config["mode"],
                "model": binary.model,
                "aspect_ratio": aspect_ratio,
                "width": width,
                "height": height,
                "prompt": prompt,
            },
        )
        if self.asset_service:
            self.asset_service.register_generated(user_id, image)
        return image
