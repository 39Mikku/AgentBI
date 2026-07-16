from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from AgentBI.src.schemas.toolbox_emoji_schema import (
    StickerName,
    StickerNamingResponse,
    StickerNamingStrategy,
)


_CHINESE = re.compile(r"[\u3400-\u9fff]")
_SAFE_NAME = re.compile(r"[^\u3400-\u9fffA-Za-z0-9]+")
_SYSTEM = "你是表情包图片命名助手。只识别画面中可见的动作、情绪和文字，不猜测角色身份。"
_TEXT_FIRST_RULE = (
    "如果画面中有清晰可读的文字，必须直接使用该文字作为名称，不要改写或另行推断；"
    "只有没有可读文字时，才按情绪或动作命名。"
)


def _json_payload(text: str) -> Any:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    return json.loads(value)


def _safe_chinese_name(value: Any, fallback: str) -> str:
    cleaned = _SAFE_NAME.sub("", str(value or "").strip())[:12]
    return cleaned if cleaned and _CHINESE.search(cleaned) else fallback


class StickerNamingService:
    def __init__(self, model_tasks: Any, max_concurrency: int = 4):
        self.model_tasks = model_tasks
        self.max_concurrency = max(1, min(int(max_concurrency), 6))

    async def name(
        self,
        *,
        user_id: str,
        strategy: StickerNamingStrategy,
        images: list[dict[str, str]],
    ) -> StickerNamingResponse:
        if strategy == "individual":
            return await self._name_individual(user_id, images)
        return await self._name_batch(user_id, images)

    async def _name_batch(
        self, user_id: str, images: list[dict[str, str]]
    ) -> StickerNamingResponse:
        labels = "、".join(image["id"] for image in images)
        result = await self.model_tasks.complete_vision(
            user_id,
            _SYSTEM,
            (
                f"按图片输入顺序分别对应这些 id：{labels}。为每张表情命名，"
                f"只使用简短中文，2 到 6 个汉字。{_TEXT_FIRST_RULE}"
                '只返回 JSON：{"names":[{"id":"原 id","name":"中文名"}]}。'
            ),
            images,
        )
        try:
            payload = _json_payload(result.text)
            rows = payload.get("names", []) if isinstance(payload, dict) else payload
            names = {
                str(row.get("id")): row.get("name")
                for row in rows
                if isinstance(row, dict) and row.get("id")
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            names = {}
        return StickerNamingResponse(
            names=[
                StickerName(
                    id=image["id"],
                    name=_safe_chinese_name(names.get(image["id"]), f"表情{index:02d}"),
                )
                for index, image in enumerate(images, 1)
            ],
            strategy="batch",
            model=result.model,
        )

    async def _name_individual(
        self, user_id: str, images: list[dict[str, str]]
    ) -> StickerNamingResponse:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def one(index: int, image: dict[str, str]):
            async with semaphore:
                result = await self.model_tasks.complete_vision(
                    user_id,
                    _SYSTEM,
                    (
                        "为这一张表情命名，只使用简短中文，2 到 6 个汉字。"
                        f"{_TEXT_FIRST_RULE}"
                        '只返回 JSON：{"name":"中文名"}。'
                    ),
                    [image],
                )
            try:
                payload = _json_payload(result.text)
                raw_name = payload.get("name") if isinstance(payload, dict) else None
            except (json.JSONDecodeError, TypeError, ValueError):
                raw_name = None
            return (
                StickerName(
                    id=image["id"],
                    name=_safe_chinese_name(raw_name, f"表情{index:02d}"),
                ),
                result.model,
            )

        results = await asyncio.gather(
            *(one(index, image) for index, image in enumerate(images, 1))
        )
        return StickerNamingResponse(
            names=[item[0] for item in results],
            strategy="individual",
            model=results[0][1],
        )
