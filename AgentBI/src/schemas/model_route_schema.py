from typing import Literal

from pydantic import BaseModel, Field

ModelRole = Literal["embedding", "compression", "memory", "title"]


class ModelRouteUpdate(BaseModel):
    provider_id: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)


class ModelRouteResponse(ModelRouteUpdate):
    user_id: str
    role: ModelRole

