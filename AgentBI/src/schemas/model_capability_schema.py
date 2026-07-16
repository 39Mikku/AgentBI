from pydantic import BaseModel, Field


class ModelCapabilityUpdate(BaseModel):
    provider_id: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    supports_vision: bool = False


class ModelCapabilityResponse(ModelCapabilityUpdate):
    user_id: str
