from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from AgentBI.src.schemas.image_generation_schema import validate_image_data_url


StickerNamingStrategy = Literal["batch", "individual"]


class StickerNamingImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    data_url: str = Field(min_length=1, max_length=14_000_000)

    @field_validator("data_url")
    @classmethod
    def validate_data_url(cls, value: str) -> str:
        return validate_image_data_url(value)


class StickerNamingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=320)
    strategy: StickerNamingStrategy = "batch"
    images: list[StickerNamingImage] = Field(min_length=1, max_length=16)


class StickerName(BaseModel):
    id: str
    name: str


class StickerNamingResponse(BaseModel):
    names: list[StickerName]
    strategy: StickerNamingStrategy
    model: str
