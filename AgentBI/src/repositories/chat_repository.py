from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatRepository:
    def __init__(self, db: Database):
        self.db = db
        self.providers = db["provider_profiles"]
        self.preferences = db["chat_preferences"]
        self.conversations = db["conversations"]
        self.messages = db["messages"]

    def ensure_indexes(self) -> None:
        self.preferences.create_index("user_id", unique=True)
        self.conversations.create_index([("user_id", 1), ("last_message_at", -1)])
        self.messages.create_index([("conversation_id", 1), ("created_at", 1)])

    def create_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        document = {**payload, "available_models": [], "created_at": now, "updated_at": now}
        result = self.providers.insert_one(document)
        return self.providers.find_one({"_id": result.inserted_id})

    def list_providers(self) -> list[dict[str, Any]]:
        return list(self.providers.find().sort("updated_at", -1))

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(provider_id):
            return None
        return self.providers.find_one({"_id": ObjectId(provider_id)})

    def update_provider(self, provider_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        if not ObjectId.is_valid(provider_id):
            return None
        self.providers.update_one({"_id": ObjectId(provider_id)}, {"$set": {**fields, "updated_at": utc_now()}})
        return self.get_provider(provider_id)

    def delete_provider(self, provider_id: str) -> bool:
        return bool(ObjectId.is_valid(provider_id) and self.providers.delete_one({"_id": ObjectId(provider_id)}).deleted_count)

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        return self.preferences.find_one({"user_id": user_id}) or {
            "user_id": user_id,
            "provider_id": None,
            "model": None,
            "temperature": 0.7,
            "context_turns": 8,
        }

    def save_preferences(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        self.preferences.update_one(
            {"user_id": user_id},
            {"$set": {**fields, "updated_at": now}, "$setOnInsert": {"user_id": user_id, "created_at": now}},
            upsert=True,
        )
        return self.get_preferences(user_id)

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        document = {**payload, "created_at": now, "updated_at": now, "last_message_at": now}
        result = self.conversations.insert_one(document)
        return self.conversations.find_one({"_id": result.inserted_id})

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        return list(self.conversations.find({"user_id": user_id}).sort("last_message_at", -1))

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(conversation_id):
            return None
        return self.conversations.find_one({"_id": ObjectId(conversation_id), "user_id": user_id})

    def update_conversation(self, conversation_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        if not ObjectId.is_valid(conversation_id):
            return None
        self.conversations.update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {"$set": {**fields, "updated_at": utc_now()}},
        )
        return self.get_conversation(conversation_id, user_id)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        if not ObjectId.is_valid(conversation_id):
            return False
        result = self.conversations.delete_one({"_id": ObjectId(conversation_id), "user_id": user_id})
        if result.deleted_count:
            self.messages.delete_many({"conversation_id": ObjectId(conversation_id), "user_id": user_id})
        return bool(result.deleted_count)

    def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        if not ObjectId.is_valid(conversation_id):
            return []
        return list(
            self.messages.find({"conversation_id": ObjectId(conversation_id), "user_id": user_id}).sort("created_at", 1)
        )

    def append_message(self, conversation_id: str, user_id: str, role: str, content: str, **extra: Any) -> dict[str, Any]:
        now = utc_now()
        document = {
            "conversation_id": ObjectId(conversation_id),
            "user_id": user_id,
            "role": role,
            "content": content,
            "status": "complete",
            "created_at": now,
            **extra,
        }
        result = self.messages.insert_one(document)
        self.conversations.update_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id},
            {"$set": {"updated_at": now, "last_message_at": now}},
        )
        return self.messages.find_one({"_id": result.inserted_id})
