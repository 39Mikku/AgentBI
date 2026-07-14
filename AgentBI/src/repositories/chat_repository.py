from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from AgentBI.src.agents.assistant_registry import DEFAULT_ASSISTANT_CAPABILITIES, DEFAULT_ASSISTANT_PROMPT


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_object_id(value: str | ObjectId | None) -> ObjectId | None:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(value) if isinstance(value, str) and ObjectId.is_valid(value) else None


class ChatRepository:
    """Mongo-first persistence for chat threads, message DAGs, and generation runs."""

    def __init__(self, db: Database):
        self.db = db
        self.providers = db["provider_profiles"]
        self.preferences = db["chat_preferences"]
        self.user_profiles = db["user_profiles"]
        self.users = db["users"]
        self.assistants = db["assistants"]

        # Phase-one collections are intentionally retained as untouched historical data.
        self.legacy_conversations = db["conversations"]
        self.legacy_messages = db["messages"]

        self.threads = db["chat_threads"]
        self.message_nodes = db["chat_messages"]
        self.runs = db["chat_runs"]

    def ensure_indexes(self) -> None:
        self.preferences.create_index("user_id", unique=True)
        self.assistants.create_index([("user_id", ASCENDING), ("is_default", ASCENDING)])
        self.user_profiles.create_index("user_id", unique=True)
        self.threads.create_index([("user_id", ASCENDING), ("last_message_at", DESCENDING)])
        self.threads.create_index([("source_thread_id", ASCENDING), ("source_message_id", ASCENDING)])
        self.message_nodes.create_index([("thread_id", ASCENDING), ("parent_id", ASCENDING), ("created_at", ASCENDING)])
        self.message_nodes.create_index([("thread_id", ASCENDING), ("sibling_group_id", ASCENDING), ("created_at", ASCENDING)])
        self.runs.create_index([("thread_id", ASCENDING), ("message_id", ASCENDING)], unique=True)

    # Provider, preference, and profile persistence ---------------------------------

    def create_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        document = {**payload, "available_models": [], "created_at": now, "updated_at": now}
        result = self.providers.insert_one(document)
        return self.providers.find_one({"_id": result.inserted_id})

    def list_providers(self) -> list[dict[str, Any]]:
        return list(self.providers.find().sort("updated_at", DESCENDING))

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        object_id = as_object_id(provider_id)
        return self.providers.find_one({"_id": object_id}) if object_id else None

    def update_provider(self, provider_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        object_id = as_object_id(provider_id)
        if not object_id:
            return None
        self.providers.update_one({"_id": object_id}, {"$set": {**fields, "updated_at": utc_now()}})
        return self.get_provider(provider_id)

    def delete_provider(self, provider_id: str) -> bool:
        object_id = as_object_id(provider_id)
        return bool(object_id and self.providers.delete_one({"_id": object_id}).deleted_count)

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

    def get_user_profile(self, user_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        user = self.users.find_one({"email": user_id}) or self.users.find_one({"username": user_id})
        return user, self.user_profiles.find_one({"user_id": user_id})

    def save_user_avatar(self, user_id: str, avatar_data_url: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        now = utc_now()
        self.user_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {"avatar_data_url": avatar_data_url, "updated_at": now},
                "$setOnInsert": {"user_id": user_id, "created_at": now},
            },
            upsert=True,
        )
        return self.get_user_profile(user_id)

    # Thread and DAG persistence -----------------------------------------------------

    def ensure_default_assistant(self, user_id: str) -> dict[str, Any]:
        assistant = self.assistants.find_one({"user_id": user_id, "is_default": True})
        if not assistant:
            now = utc_now()
            result = self.assistants.insert_one({
                "user_id": user_id,
                "name": "默认助手",
                "system_prompt": DEFAULT_ASSISTANT_PROMPT,
                "capability_ids": DEFAULT_ASSISTANT_CAPABILITIES,
                "avatar_data_url": None,
                "include_runtime_context": True,
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            })
            assistant = self.assistants.find_one({"_id": result.inserted_id})
        self.threads.update_many(
            {"user_id": user_id, "$or": [{"assistant_id": {"$exists": False}}, {"assistant_id": None}]},
            {"$set": {"assistant_id": assistant["_id"]}},
        )
        return assistant

    def list_assistants(self, user_id: str) -> list[dict[str, Any]]:
        self.ensure_default_assistant(user_id)
        return list(self.assistants.find({"user_id": user_id}).sort([("is_default", DESCENDING), ("created_at", ASCENDING)]))

    def get_assistant(self, assistant_id: str | ObjectId | None, user_id: str) -> dict[str, Any] | None:
        object_id = as_object_id(assistant_id)
        return self.assistants.find_one({"_id": object_id, "user_id": user_id}) if object_id else None

    def create_assistant(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        result = self.assistants.insert_one({
            **payload,
            "is_default": False,
            "created_at": now,
            "updated_at": now,
        })
        return self.assistants.find_one({"_id": result.inserted_id})

    def update_assistant(self, assistant_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        assistant = self.get_assistant(assistant_id, user_id)
        if not assistant or assistant.get("is_default"):
            return None
        self.assistants.update_one({"_id": assistant["_id"]}, {"$set": {**fields, "updated_at": utc_now()}})
        return self.get_assistant(assistant_id, user_id)

    def delete_assistant(self, assistant_id: str, user_id: str) -> bool:
        assistant = self.get_assistant(assistant_id, user_id)
        if not assistant or assistant.get("is_default") or self.threads.count_documents({"user_id": user_id, "assistant_id": assistant["_id"]}):
            return False
        return bool(self.assistants.delete_one({"_id": assistant["_id"]}).deleted_count)

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        thread = {
            **payload,
            "active_message_id": None,
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
        }
        result = self.threads.insert_one(thread)
        thread_id = result.inserted_id
        root_result = self.message_nodes.insert_one(
            {
                "thread_id": thread_id,
                "user_id": payload["user_id"],
                "parent_id": None,
                "role": "root",
                "content": "",
                "status": "complete",
                "depth": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        self.threads.update_one({"_id": thread_id}, {"$set": {"root_message_id": root_result.inserted_id}})
        return self.threads.find_one({"_id": thread_id})

    def list_conversations(self, user_id: str, assistant_id: str | None = None) -> list[dict[str, Any]]:
        default_assistant = self.ensure_default_assistant(user_id)
        selected = as_object_id(assistant_id) if assistant_id else default_assistant["_id"]
        return list(self.threads.find({"user_id": user_id, "assistant_id": selected}).sort("last_message_at", DESCENDING))

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        object_id = as_object_id(conversation_id)
        return self.threads.find_one({"_id": object_id, "user_id": user_id}) if object_id else None

    def update_conversation(self, conversation_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        object_id = as_object_id(conversation_id)
        if not object_id:
            return None
        self.threads.update_one(
            {"_id": object_id, "user_id": user_id},
            {"$set": {**fields, "updated_at": utc_now()}},
        )
        return self.get_conversation(conversation_id, user_id)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        thread = self.get_conversation(conversation_id, user_id)
        if not thread:
            return False
        self.runs.delete_many({"thread_id": thread["_id"]})
        self.message_nodes.delete_many({"thread_id": thread["_id"]})
        return bool(self.threads.delete_one({"_id": thread["_id"], "user_id": user_id}).deleted_count)

    def _get_message(self, message_id: str | ObjectId, thread_id: ObjectId, user_id: str) -> dict[str, Any] | None:
        object_id = as_object_id(message_id)
        if not object_id:
            return None
        return self.message_nodes.find_one({"_id": object_id, "thread_id": thread_id, "user_id": user_id})

    def _get_path(self, thread: dict[str, Any], head_id: str | ObjectId | None) -> list[dict[str, Any]]:
        """Read one parent chain. The bounded walk is portable and has one indexed lookup per context node."""
        current_id = as_object_id(head_id)
        if not current_id:
            current_id = thread.get("root_message_id")
        path: list[dict[str, Any]] = []
        seen: set[ObjectId] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            node = self.message_nodes.find_one({"_id": current_id, "thread_id": thread["_id"], "user_id": thread["user_id"]})
            if not node:
                break
            path.append(node)
            current_id = node.get("parent_id")
        return list(reversed(path))

    def get_active_path(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        thread = self.get_conversation(conversation_id, user_id)
        return self._get_path(thread, thread.get("active_message_id")) if thread else []

    def get_path_to_message(self, conversation_id: str, user_id: str, message_id: str) -> list[dict[str, Any]]:
        thread = self.get_conversation(conversation_id, user_id)
        message = self._get_message(message_id, thread["_id"], user_id) if thread else None
        return self._get_path(thread, message["_id"]) if thread and message else []

    def _touch_thread(self, thread_id: ObjectId, active_message_id: ObjectId | None = None) -> None:
        now = utc_now()
        fields: dict[str, Any] = {"updated_at": now, "last_message_at": now}
        if active_message_id is not None:
            fields["active_message_id"] = active_message_id
        self.threads.update_one({"_id": thread_id}, {"$set": fields})

    def _insert_message(
        self,
        thread: dict[str, Any],
        parent: dict[str, Any],
        role: str,
        content: str,
        *,
        status: str = "complete",
        sibling_group_id: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        if parent["thread_id"] != thread["_id"] or parent["user_id"] != thread["user_id"]:
            raise ValueError("Parent message does not belong to this thread")
        now = utc_now()
        document = {
            "thread_id": thread["_id"],
            "user_id": thread["user_id"],
            "parent_id": parent["_id"],
            "role": role,
            "content": content,
            "status": status,
            "depth": parent.get("depth", 0) + 1,
            "sibling_group_id": sibling_group_id,
            "created_at": now,
            "updated_at": now,
            **extra,
        }
        result = self.message_nodes.insert_one(document)
        message = self.message_nodes.find_one({"_id": result.inserted_id})
        self._touch_thread(thread["_id"], message["_id"])
        return message

    def create_user_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        parent_message_id: str | None = None,
    ) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        if not thread:
            return None
        parent_id = parent_message_id or thread.get("active_message_id") or thread.get("root_message_id")
        parent = self._get_message(parent_id, thread["_id"], user_id)
        return self._insert_message(thread, parent, "user", content) if parent else None

    def _create_run(self, thread: dict[str, Any], message_id: ObjectId, snapshot: dict[str, Any] | None) -> ObjectId:
        now = utc_now()
        result = self.runs.insert_one(
            {
                "thread_id": thread["_id"],
                "message_id": message_id,
                "user_id": thread["user_id"],
                "config_snapshot": snapshot or {},
                "status": "streaming",
                "started_at": now,
                "created_at": now,
                "updated_at": now,
            }
        )
        return result.inserted_id

    def create_assistant_message(
        self,
        conversation_id: str,
        user_id: str,
        parent_message_id: str,
        model_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        if not thread:
            return None
        parent = self._get_message(parent_message_id, thread["_id"], user_id)
        if not parent or parent.get("role") != "user":
            return None
        message = self._insert_message(
            thread,
            parent,
            "assistant",
            "",
            status="streaming",
            model_snapshot=model_snapshot or {},
        )
        run_id = self._create_run(thread, message["_id"], model_snapshot)
        self.message_nodes.update_one({"_id": message["_id"]}, {"$set": {"run_id": run_id}})
        return self.message_nodes.find_one({"_id": message["_id"]})

    def _create_sibling(
        self,
        source: dict[str, Any],
        content: str,
        *,
        status: str,
        **extra: Any,
    ) -> dict[str, Any]:
        if source.get("role") == "root" or not source.get("parent_id"):
            raise ValueError("The virtual root cannot have siblings")
        group_id = source.get("sibling_group_id") or str(uuid4())
        if not source.get("sibling_group_id"):
            self.message_nodes.update_one({"_id": source["_id"]}, {"$set": {"sibling_group_id": group_id}})
        thread = self.threads.find_one({"_id": source["thread_id"], "user_id": source["user_id"]})
        parent = self.message_nodes.find_one({"_id": source["parent_id"], "thread_id": source["thread_id"]})
        if not thread or not parent:
            raise ValueError("Source message has no valid thread parent")
        return self._insert_message(
            thread,
            parent,
            source["role"],
            content,
            status=status,
            sibling_group_id=group_id,
            **extra,
        )

    def edit_user_message(self, conversation_id: str, user_id: str, message_id: str, content: str) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        source = self._get_message(message_id, thread["_id"], user_id) if thread else None
        if not source or source.get("role") != "user":
            return None
        return self._create_sibling(source, content, status="complete")

    def retry_assistant_message(
        self,
        conversation_id: str,
        user_id: str,
        message_id: str,
        model_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        source = self._get_message(message_id, thread["_id"], user_id) if thread else None
        if not source or source.get("role") != "assistant":
            return None
        message = self._create_sibling(
            source,
            "",
            status="streaming",
            model_snapshot=model_snapshot or {},
        )
        run_id = self._create_run(thread, message["_id"], model_snapshot)
        self.message_nodes.update_one({"_id": message["_id"]}, {"$set": {"run_id": run_id}})
        return self.message_nodes.find_one({"_id": message["_id"]})

    def complete_assistant_message(self, message_id: str, content: str, **extra: Any) -> dict[str, Any] | None:
        object_id = as_object_id(message_id)
        if not object_id:
            return None
        now = utc_now()
        self.message_nodes.update_one(
            {"_id": object_id, "role": "assistant"},
            {"$set": {"content": content, "status": "complete", "updated_at": now, **extra}},
        )
        message = self.message_nodes.find_one({"_id": object_id})
        if message and message.get("run_id"):
            self.runs.update_one(
                {"_id": message["run_id"]},
                {"$set": {"status": "complete", "finished_at": now, "updated_at": now}},
            )
        return message

    def fail_assistant_message(self, message_id: str, content: str) -> dict[str, Any] | None:
        object_id = as_object_id(message_id)
        if not object_id:
            return None
        now = utc_now()
        self.message_nodes.update_one(
            {"_id": object_id, "role": "assistant"},
            {"$set": {"content": content, "status": "error", "updated_at": now}},
        )
        message = self.message_nodes.find_one({"_id": object_id})
        if message and message.get("run_id"):
            self.runs.update_one(
                {"_id": message["run_id"]},
                {"$set": {"status": "error", "finished_at": now, "updated_at": now}},
            )
        return message

    def _latest_descendant_leaf(self, message: dict[str, Any]) -> dict[str, Any]:
        """Restore a selected version together with its most recently active continuation."""
        current = message
        while True:
            children = list(
                self.message_nodes.find(
                    {"thread_id": current["thread_id"], "parent_id": current["_id"], "user_id": current["user_id"]}
                ).sort("created_at", DESCENDING)
            )
            if not children:
                return current
            current = children[0]

    def set_active_message(self, conversation_id: str, user_id: str, message_id: str) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        message = self._get_message(message_id, thread["_id"], user_id) if thread else None
        if not thread or not message or message.get("role") == "root":
            return None
        self._touch_thread(thread["_id"], self._latest_descendant_leaf(message)["_id"])
        return self.get_conversation(conversation_id, user_id)

    def get_sibling_versions(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        if message.get("role") == "root" or not message.get("parent_id"):
            return [message]
        return list(
            self.message_nodes.find(
                {
                    "thread_id": message["thread_id"],
                    "parent_id": message["parent_id"],
                    "role": message["role"],
                }
            ).sort("created_at", ASCENDING)
        )

    def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        active_path = self.get_active_path(conversation_id, user_id)
        result: list[dict[str, Any]] = []
        for message in active_path:
            if message.get("role") == "root":
                continue
            item = deepcopy(message)
            siblings = self.get_sibling_versions(message)
            ids = [str(sibling["_id"]) for sibling in siblings]
            item["version_ids"] = ids
            item["sibling_count"] = len(ids)
            item["sibling_index"] = ids.index(str(message["_id"])) if str(message["_id"]) in ids else 0
            result.append(item)
        return result

    def create_branch_conversation(
        self,
        conversation_id: str,
        user_id: str,
        source_message_id: str,
        title: str | None = None,
    ) -> dict[str, Any] | None:
        source_thread = self.get_conversation(conversation_id, user_id)
        source_message = self._get_message(source_message_id, source_thread["_id"], user_id) if source_thread else None
        if not source_thread or not source_message or source_message.get("role") == "root":
            return None
        copied = self.create_conversation(
            {
                "user_id": user_id,
                "title": title or f"{source_thread.get('title', 'Untitled')} · branch",
                "provider_id": source_thread.get("provider_id"),
                "model": source_thread.get("model"),
                "temperature": source_thread.get("temperature", 0.7),
                "context_turns": source_thread.get("context_turns", 8),
                "assistant_id": source_thread.get("assistant_id"),
                "source_thread_id": source_thread["_id"],
                "source_message_id": source_message["_id"],
            }
        )
        copied_path = self._get_path(source_thread, source_message["_id"])
        source_to_copy: dict[ObjectId, ObjectId] = {source_thread["root_message_id"]: copied["root_message_id"]}
        copied_active: ObjectId | None = None
        for source in copied_path:
            if source.get("role") == "root":
                continue
            now = utc_now()
            document = {
                "thread_id": copied["_id"],
                "user_id": user_id,
                "parent_id": source_to_copy[source["parent_id"]],
                "role": source["role"],
                "content": source.get("content", ""),
                "status": source.get("status", "complete"),
                "depth": source.get("depth", 1),
                "reasoning_summary": source.get("reasoning_summary"),
                "tool_events": deepcopy(source.get("tool_events", [])),
                "timeline": deepcopy(source.get("timeline", [])),
                "model_snapshot": deepcopy(source.get("model_snapshot", {})),
                "created_at": now,
                "updated_at": now,
            }
            result = self.message_nodes.insert_one(document)
            source_to_copy[source["_id"]] = result.inserted_id
            copied_active = result.inserted_id
        if copied_active:
            self._touch_thread(copied["_id"], copied_active)
        return self.threads.find_one({"_id": copied["_id"]})

    # Compatibility adapter used by the phase-one stream route until it is switched.
    def append_message(self, conversation_id: str, user_id: str, role: str, content: str, **extra: Any) -> dict[str, Any] | None:
        if role == "user":
            return self.create_user_message(conversation_id, user_id, content)
        thread = self.get_conversation(conversation_id, user_id)
        parent_id = str(thread.get("active_message_id")) if thread and thread.get("active_message_id") else None
        message = self.create_assistant_message(conversation_id, user_id, parent_id or "") if parent_id else None
        if not message:
            return None
        return self.complete_assistant_message(str(message["_id"]), content, **extra)
