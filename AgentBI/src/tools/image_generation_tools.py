from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from AgentBI.src.services.image_generation.service import ImageGenerationService


@dataclass(slots=True, frozen=True)
class AtomicToolResult:
    content: str
    card: dict[str, Any] | None = None


async def generate_image(
    service: ImageGenerationService,
    *,
    user_id: str,
    scope_id: str | None,
    prompt: str,
    aspect_ratio: str,
    provider: dict[str, Any] | None,
) -> AtomicToolResult:
    image = await service.generate(
        user_id=user_id,
        scope_id=scope_id,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        provider=provider,
    )
    compact = {
        "status": "generated",
        "image_id": image.id,
        "image_attached": True,
        "mode": image.mode,
        "model": image.model,
        "aspect_ratio": image.aspect_ratio,
        "display_instruction": "图片已由界面卡片展示，不要再次输出图片链接或 Markdown 图片。",
    }
    payload = image.model_dump(exclude={"relative_path", "media_type"})
    return AtomicToolResult(
        content=json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        card={"kind": "image.generated", "payload": payload},
    )
