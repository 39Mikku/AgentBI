import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HomeQuote(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=1000)
    speaker: str = Field(default="", max_length=100)


class HomeQuotesUpdate(BaseModel):
    home_quotes: list[HomeQuote] | None = Field(default=None, min_length=1, max_length=100)


class UserAvatarUpdate(BaseModel):
    avatar_data_url: str = Field(min_length=24, max_length=2_000_000, pattern=r"^data:image/(png|jpeg|webp|gif);base64,")


class UserNameUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r".*\S.*")


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    avatar_data_url: str | None = None
    home_quotes: list[HomeQuote] | None = None

    @classmethod
    def from_documents(
        cls,
        user_id: str,
        user: dict[str, Any] | None,
        profile: dict[str, Any] | None,
    ) -> "UserProfileResponse":
        user = user or {}
        profile = profile or {}
        email = user.get("email") or (user_id if "@" in user_id else None)
        username = user.get("username") or (email.split("@", 1)[0] if email else user_id)
        return cls(
            user_id=user_id,
            username=username,
            email=email,
            avatar_data_url=profile.get("avatar_data_url"),
            home_quotes=json.loads(user["home_quotes"]) if user.get("home_quotes") else None,
        )
