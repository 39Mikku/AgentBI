from typing import Any

from pymongo import MongoClient


class MongoUserDirectory:
    """Read-only bridge to the existing login user directory, outside chat persistence."""

    def __init__(self, mongo_uri: str | None, database_name: str, users: Any | None = None):
        self._client = None
        self.users = users
        if self.users is None and mongo_uri:
            self._client = MongoClient(mongo_uri)
            self.users = self._client[database_name]["users"]

    def find_user(self, user_id: str) -> dict[str, Any] | None:
        if self.users is None:
            return None
        return self.users.find_one({"email": user_id}) or self.users.find_one({"username": user_id})

    def close(self) -> None:
        if self._client:
            self._client.close()
