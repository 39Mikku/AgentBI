from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ImageMode = Literal["lite", "pro"]
ImageQuality = Literal["low", "medium", "high"]
ImageAspectRatio = Literal["square", "landscape", "portrait"]


class ImageGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ImageMode = "lite"
    lite_model: str = Field(default="", max_length=160)
    pro_quality: ImageQuality = "high"


class ImageGenerationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=320)
    prompt: str = Field(min_length=1, max_length=20_000)
    aspect_ratio: ImageAspectRatio = "square"
    provider_id: str | None = Field(default=None, max_length=160)
    scope_id: str | None = Field(default=None, max_length=160)


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
