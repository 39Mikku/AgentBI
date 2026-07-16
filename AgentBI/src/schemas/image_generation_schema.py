from __future__ import annotations

import base64
import binascii
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ImageMode = Literal["lite", "pro"]
ImageQuality = Literal["low", "medium", "high"]
ImageAspectRatio = Literal["square", "landscape", "portrait"]
_REFERENCE_IMAGE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)$")


def validate_image_data_url(value: str) -> str:
    match = _REFERENCE_IMAGE.fullmatch(value)
    if not match:
        raise ValueError("参考图必须是 PNG、JPEG 或 WebP Data URL")
    try:
        image = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("参考图 Base64 数据无效") from error
    media_type = match.group(1)
    valid = (
        (media_type == "image/png" and image.startswith(b"\x89PNG\r\n\x1a\n"))
        or (media_type == "image/jpeg" and image.startswith(b"\xff\xd8\xff"))
        or (
            media_type == "image/webp"
            and len(image) >= 12
            and image.startswith(b"RIFF")
            and image[8:12] == b"WEBP"
        )
    )
    if not valid:
        raise ValueError("参考图文件签名无效")
    return value


class ImageGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ImageMode = "lite"
    lite_model: str = Field(default="", max_length=160)
    pro_quality: ImageQuality = "high"


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=320)
    prompt: str = Field(min_length=1, max_length=20_000)
    aspect_ratio: ImageAspectRatio = "square"
    provider_id: str | None = Field(default=None, max_length=160)
    scope_id: str | None = Field(default=None, max_length=160)
    reference_image_data_url: str | None = Field(default=None, max_length=14_000_000)

    @field_validator("reference_image_data_url")
    @classmethod
    def validate_reference_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_image_data_url(value)


class GeneratedImage(BaseModel):
    id: str
    url: str
    relative_path: str
    media_type: str
    mode: ImageMode
    model: str
    aspect_ratio: ImageAspectRatio = "square"
    width: int | None = None
    height: int | None = None
    prompt: str = ""


class CodexOAuthStatus(BaseModel):
    connected: bool
    account_id: str | None = None
    expires_at: int | None = None
    pending: bool = False
    error: str | None = None


class CodexOAuthStartResponse(BaseModel):
    authorization_url: str
    user_code: str
    expires_in: int = 900
