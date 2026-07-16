from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Any, Callable

from AgentBI.src.services.openai_compatible_client import create_openai_compatible_client


_DATA_URL = re.compile(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)")
_ASPECT_RATIOS = {"square": "1:1", "landscape": "16:9", "portrait": "9:16"}


class ImageGenerationError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ImageBinary:
    image_bytes: bytes
    media_type: str
    model: str


def _as_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        value = model_dump()
        return value if isinstance(value, dict) else {}
    return {}


def _candidate_strings(value: Any, key: str = ""):
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _candidate_strings(child, str(child_key))
        return
    if isinstance(value, list):
        for child in value:
            yield from _candidate_strings(child, key)
        return
    if not isinstance(value, str):
        return
    for match in _DATA_URL.finditer(value):
        yield match.group(1), match.group(2)
    if key in {"b64_json", "base64", "image_base64"}:
        yield "image/png", value


def _valid_signature(image_bytes: bytes, media_type: str) -> bool:
    if media_type == "image/png":
        return image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/jpeg":
        return image_bytes.startswith(b"\xff\xd8\xff")
    if media_type == "image/webp":
        return len(image_bytes) >= 12 and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
    return False


def extract_image_data(payload: Any) -> tuple[bytes, str]:
    document = _as_dict(payload)
    found_candidate = False
    for media_type, encoded in _candidate_strings(document):
        found_candidate = True
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(image_bytes) > 40 * 1024 * 1024:
            raise ImageGenerationError("图片数据过大")
        if _valid_signature(image_bytes, media_type):
            return image_bytes, media_type
    if found_candidate:
        raise ImageGenerationError("图片数据无效")
    raise ImageGenerationError("上游未返回可解析图片")


class LiteChatImageAdapter:
    def __init__(self, client_factory: Callable[[dict[str, Any]], Any] = create_openai_compatible_client):
        self.client_factory = client_factory

    async def generate(
        self,
        *,
        provider: dict[str, Any],
        model: str,
        prompt: str,
        aspect_ratio: str,
        reference_image_data_url: str | None = None,
    ) -> ImageBinary:
        if not model.strip():
            raise ImageGenerationError("请先在能力配置中填写 Lite 生图模型")
        client = self.client_factory(provider)
        content: str | list[dict[str, Any]] = prompt
        if reference_image_data_url:
            content = [
                {"type": "image_url", "image_url": {"url": reference_image_data_url}},
                {"type": "text", "text": prompt},
            ]
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            extra_body={
                "modalities": ["text", "image"],
                "image_config": {"aspect_ratio": _ASPECT_RATIOS.get(aspect_ratio, "1:1")},
            },
        )
        image_bytes, media_type = extract_image_data(response)
        return ImageBinary(image_bytes=image_bytes, media_type=media_type, model=model)
