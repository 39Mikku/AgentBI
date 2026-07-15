import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from AgentBI.src.agents.assistant_registry import DEFAULT_ASSISTANT_CAPABILITIES, DEFAULT_ASSISTANT_PROMPT


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteChatRepository:
    """Local-first persistence for chat threads, message DAGs, and user workspace settings."""

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")
        self.ensure_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def ensure_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_profiles (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, base_url TEXT NOT NULL, api_key TEXT NOT NULL,
                    default_model TEXT, available_models TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_preferences (
                    user_id TEXT PRIMARY KEY, provider_id TEXT, model TEXT, temperature REAL NOT NULL,
                    context_turns INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
                    avatar_data_url TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS users_username_nocase ON users(username COLLATE NOCASE);
                CREATE TABLE IF NOT EXISTS login_codes (
                    identity TEXT PRIMARY KEY, code TEXT NOT NULL, target_email TEXT NOT NULL,
                    expires_at TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assistants (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, system_prompt TEXT NOT NULL,
                    capability_ids TEXT NOT NULL DEFAULT '[]', avatar_data_url TEXT,
                    include_runtime_context INTEGER NOT NULL DEFAULT 1, is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS assistants_one_default_per_user
                    ON assistants(user_id) WHERE is_default = 1;
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL, provider_id TEXT,
                    model TEXT, temperature REAL NOT NULL, context_turns INTEGER NOT NULL,
                    assistant_id TEXT, active_message_id TEXT, root_message_id TEXT,
                    source_thread_id TEXT, source_message_id TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_message_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY, thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, parent_id TEXT REFERENCES chat_messages(id) ON DELETE CASCADE,
                    role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL, depth INTEGER NOT NULL,
                    sibling_group_id TEXT, reasoning_summary TEXT, tool_events TEXT NOT NULL DEFAULT '[]',
                    timeline TEXT NOT NULL DEFAULT '[]', model_snapshot TEXT NOT NULL DEFAULT '{}', run_id TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_runs (
                    id TEXT PRIMARY KEY, thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
                    message_id TEXT NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, config_snapshot TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL,
                    started_at TEXT NOT NULL, finished_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS threads_by_user_updated ON chat_threads(user_id, last_message_at DESC);
                CREATE INDEX IF NOT EXISTS thread_message_parent ON chat_messages(thread_id, parent_id, created_at);
                CREATE INDEX IF NOT EXISTS thread_message_siblings ON chat_messages(thread_id, sibling_group_id, created_at);
                CREATE UNIQUE INDEX IF NOT EXISTS runs_by_message ON chat_runs(thread_id, message_id);
                """
            )

    @staticmethod
    def _json_dump(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _json_load(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback

    @staticmethod
    def _time(value: datetime | None = None) -> str:
        return (value or utc_now()).isoformat()

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    @staticmethod
    def _id() -> str:
        return uuid4().hex

    def _one(self, sql: str, args: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self._connection.execute(sql, args).fetchone()

    def _all(self, sql: str, args: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self._connection.execute(sql, args).fetchall()

    def _provider_document(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        item["available_models"] = self._json_load(item.pop("available_models"), [])
        item["created_at"] = self._parse_time(item["created_at"])
        item["updated_at"] = self._parse_time(item["updated_at"])
        return item

    def _assistant_document(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        item["capability_ids"] = self._json_load(item.pop("capability_ids"), [])
        item["include_runtime_context"] = bool(item["include_runtime_context"])
        item["is_default"] = bool(item["is_default"])
        item["created_at"] = self._parse_time(item["created_at"])
        item["updated_at"] = self._parse_time(item["updated_at"])
        return item

    def _thread_document(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        for name in ("created_at", "updated_at", "last_message_at"):
            item[name] = self._parse_time(item[name])
        return item

    def _message_document(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        for name, fallback in (("tool_events", []), ("timeline", []), ("model_snapshot", {})):
            item[name] = self._json_load(item[name], fallback)
        item["created_at"] = self._parse_time(item["created_at"])
        item["updated_at"] = self._parse_time(item["updated_at"])
        return item

    def _user_document(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        item = dict(row)
        item["created_at"] = self._parse_time(item["created_at"])
        item["updated_at"] = self._parse_time(item["updated_at"])
        return item

    # Provider, preference, and profile persistence ---------------------------------

    def create_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_id, now = self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO provider_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (provider_id, payload["name"], payload["base_url"], payload["api_key"], payload.get("default_model"), "[]", now, now),
            )
        return self.get_provider(provider_id)  # type: ignore[return-value]

    def list_providers(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._provider_document(row) for row in self._all("SELECT * FROM provider_profiles ORDER BY updated_at DESC")]  # type: ignore[list-item]

    def get_provider(self, provider_id: str | None) -> dict[str, Any] | None:
        if not provider_id:
            return None
        with self._lock:
            return self._provider_document(self._one("SELECT * FROM provider_profiles WHERE id = ?", (provider_id,)))

    def update_provider(self, provider_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"name", "base_url", "api_key", "default_model", "available_models"}
        values = {key: value for key, value in fields.items() if key in allowed}
        if not values or not self.get_provider(provider_id):
            return self.get_provider(provider_id)
        assignments, params = [], []
        for key, value in values.items():
            assignments.append(f"{key} = ?")
            params.append(self._json_dump(value) if key == "available_models" else value)
        assignments.append("updated_at = ?")
        params.extend([self._time(), provider_id])
        with self._lock, self._connection:
            self._connection.execute(f"UPDATE provider_profiles SET {', '.join(assignments)} WHERE id = ?", tuple(params))
        return self.get_provider(provider_id)

    def delete_provider(self, provider_id: str) -> bool:
        with self._lock, self._connection:
            return bool(self._connection.execute("DELETE FROM provider_profiles WHERE id = ?", (provider_id,)).rowcount)

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._one("SELECT * FROM chat_preferences WHERE user_id = ?", (user_id,))
        return dict(row) if row else {"user_id": user_id, "provider_id": None, "model": None, "temperature": 0.7, "context_turns": 8}

    def save_preferences(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        values = {**self.get_preferences(user_id), **fields}
        now = self._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO chat_preferences(user_id, provider_id, model, temperature, context_turns, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET
                provider_id=excluded.provider_id, model=excluded.model, temperature=excluded.temperature,
                context_turns=excluded.context_turns, updated_at=excluded.updated_at""",
                (user_id, values.get("provider_id"), values.get("model"), values["temperature"], values["context_turns"], now, now),
            )
        return self.get_preferences(user_id)

    def find_user(self, identity: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._one("SELECT * FROM users WHERE email = ? COLLATE NOCASE OR username = ? COLLATE NOCASE", (identity.strip(), identity.strip()))
        return self._user_document(row)

    def create_user(self, email: str, username: str | None = None) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        existing = self.find_user(normalized_email)
        if existing:
            return existing
        base = (username or normalized_email.split("@", 1)[0]).strip() or "user"
        candidate, suffix = base, 2
        with self._lock:
            while self._one("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (candidate,)):
                candidate = f"{base}-{suffix}"
                suffix += 1
        now = self._time()
        with self._lock, self._connection:
            self._connection.execute("INSERT INTO users VALUES (?, ?, ?, NULL, ?, ?)", (normalized_email, candidate, normalized_email, now, now))
        return self.find_user(normalized_email)  # type: ignore[return-value]

    def update_user(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"username", "avatar_data_url"}
        values = {key: value for key, value in fields.items() if key in allowed}
        if not values:
            return self.find_user(user_id)
        assignments = [f"{key} = ?" for key in values]
        params = [*values.values(), self._time(), user_id]
        with self._lock, self._connection:
            self._connection.execute(f"UPDATE users SET {', '.join(assignments)}, updated_at = ? WHERE user_id = ?", tuple(params))
        return self.find_user(user_id)

    def create_login_code(self, identity: str, code: str, target_email: str, expires_seconds: int = 300) -> None:
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO login_codes(identity, code, target_email, expires_at, created_at) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(identity) DO UPDATE SET code=excluded.code, target_email=excluded.target_email,
                expires_at=excluded.expires_at, created_at=excluded.created_at""",
                (identity.strip(), code, target_email, self._time(now + timedelta(seconds=expires_seconds)), self._time(now)),
            )

    def consume_login_code(self, identity: str, code: str) -> dict[str, str] | None:
        now = self._time()
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM login_codes WHERE expires_at <= ?", (now,))
            row = self._one("SELECT identity, target_email FROM login_codes WHERE identity = ? AND code = ?", (identity.strip(), code.strip()))
            if not row:
                return None
            self._connection.execute("DELETE FROM login_codes WHERE identity = ?", (identity.strip(),))
        return dict(row)

    def get_user_profile(self, user_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        user = self.find_user(user_id)
        return user, user

    def save_user_avatar(self, user_id: str, avatar_data_url: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        user = self.update_user(user_id, {"avatar_data_url": avatar_data_url})
        return user, user

    # Thread and DAG persistence ----------------------------------------------------

    def ensure_default_assistant(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            existing = self._assistant_document(self._one("SELECT * FROM assistants WHERE user_id = ? AND is_default = 1", (user_id,)))
        if existing:
            return existing
        assistant_id, now = self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO assistants(id, user_id, name, system_prompt, capability_ids, avatar_data_url,
                include_runtime_context, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, NULL, 1, 1, ?, ?)""",
                (assistant_id, user_id, "默认助手", DEFAULT_ASSISTANT_PROMPT, self._json_dump(DEFAULT_ASSISTANT_CAPABILITIES), now, now),
            )
            row = self._one("SELECT * FROM assistants WHERE user_id = ? AND is_default = 1", (user_id,))
        return self._assistant_document(row)  # type: ignore[return-value]

    def list_assistants(self, user_id: str) -> list[dict[str, Any]]:
        self.ensure_default_assistant(user_id)
        with self._lock:
            rows = self._all("SELECT * FROM assistants WHERE user_id = ? ORDER BY is_default DESC, created_at ASC", (user_id,))
        return [self._assistant_document(row) for row in rows]  # type: ignore[list-item]

    def get_assistant(self, assistant_id: str | None, user_id: str) -> dict[str, Any] | None:
        if not assistant_id:
            return None
        with self._lock:
            return self._assistant_document(self._one("SELECT * FROM assistants WHERE id = ? AND user_id = ?", (assistant_id, user_id)))

    def create_assistant(self, payload: dict[str, Any]) -> dict[str, Any]:
        assistant_id, now = self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO assistants VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (assistant_id, payload["user_id"], payload["name"], payload.get("system_prompt", ""),
                 self._json_dump(payload.get("capability_ids", [])), payload.get("avatar_data_url"),
                 int(payload.get("include_runtime_context", True)), now, now),
            )
        return self.get_assistant(assistant_id, payload["user_id"])  # type: ignore[return-value]

    def update_assistant(self, assistant_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        assistant = self.get_assistant(assistant_id, user_id)
        if not assistant or assistant["is_default"]:
            return None
        allowed = {"name", "system_prompt", "capability_ids", "avatar_data_url", "include_runtime_context"}
        values = {key: value for key, value in fields.items() if key in allowed}
        if values:
            assignments, params = [], []
            for key, value in values.items():
                assignments.append(f"{key} = ?")
                if key == "capability_ids":
                    value = self._json_dump(value)
                if key == "include_runtime_context":
                    value = int(bool(value))
                params.append(value)
            params.extend([self._time(), assistant_id, user_id])
            with self._lock, self._connection:
                self._connection.execute(f"UPDATE assistants SET {', '.join(assignments)}, updated_at = ? WHERE id = ? AND user_id = ?", tuple(params))
        return self.get_assistant(assistant_id, user_id)

    def delete_assistant(self, assistant_id: str, user_id: str) -> bool:
        assistant = self.get_assistant(assistant_id, user_id)
        if not assistant or assistant["is_default"]:
            return False
        with self._lock:
            used = self._one("SELECT 1 FROM chat_threads WHERE user_id = ? AND assistant_id = ? LIMIT 1", (user_id, assistant_id))
        if used:
            return False
        with self._lock, self._connection:
            return bool(self._connection.execute("DELETE FROM assistants WHERE id = ? AND user_id = ?", (assistant_id, user_id)).rowcount)

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        thread_id, root_id, now = self._id(), self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO chat_threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)""",
                (thread_id, payload["user_id"], payload["title"], payload.get("provider_id"), payload.get("model"),
                 payload.get("temperature", 0.7), payload.get("context_turns", 8), payload.get("assistant_id"), root_id,
                 payload.get("source_thread_id"), payload.get("source_message_id"), now, now, now),
            )
            self._connection.execute(
                """INSERT INTO chat_messages(id, thread_id, user_id, parent_id, role, content, status, depth, sibling_group_id,
                reasoning_summary, tool_events, timeline, model_snapshot, run_id, created_at, updated_at)
                VALUES (?, ?, ?, NULL, 'root', '', 'complete', 0, NULL, NULL, '[]', '[]', '{}', NULL, ?, ?)""",
                (root_id, thread_id, payload["user_id"], now, now),
            )
        return self.get_conversation(thread_id, payload["user_id"])  # type: ignore[return-value]

    def list_conversations(self, user_id: str, assistant_id: str | None = None) -> list[dict[str, Any]]:
        selected = assistant_id or self.ensure_default_assistant(user_id)["_id"]
        with self._lock:
            rows = self._all("SELECT * FROM chat_threads WHERE user_id = ? AND assistant_id = ? ORDER BY last_message_at DESC", (user_id, selected))
        return [self._thread_document(row) for row in rows]  # type: ignore[list-item]

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._thread_document(self._one("SELECT * FROM chat_threads WHERE id = ? AND user_id = ?", (conversation_id, user_id)))

    def update_conversation(self, conversation_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"title", "provider_id", "model", "temperature", "context_turns", "assistant_id", "active_message_id"}
        values = {key: value for key, value in fields.items() if key in allowed}
        if values:
            assignments = [f"{key} = ?" for key in values]
            params = [*values.values(), self._time(), conversation_id, user_id]
            with self._lock, self._connection:
                self._connection.execute(f"UPDATE chat_threads SET {', '.join(assignments)}, updated_at = ? WHERE id = ? AND user_id = ?", tuple(params))
        return self.get_conversation(conversation_id, user_id)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        with self._lock, self._connection:
            return bool(self._connection.execute("DELETE FROM chat_threads WHERE id = ? AND user_id = ?", (conversation_id, user_id)).rowcount)

    def _get_message(self, message_id: str | None, thread_id: str, user_id: str) -> dict[str, Any] | None:
        if not message_id:
            return None
        return self._message_document(self._one("SELECT * FROM chat_messages WHERE id = ? AND thread_id = ? AND user_id = ?", (message_id, thread_id, user_id)))

    def _get_path(self, thread: dict[str, Any], head_id: str | None) -> list[dict[str, Any]]:
        head = head_id or thread.get("root_message_id")
        if not head:
            return []
        with self._lock:
            rows = self._all(
                """WITH RECURSIVE path AS (
                    SELECT * FROM chat_messages WHERE id = ? AND thread_id = ? AND user_id = ?
                    UNION ALL
                    SELECT parent.* FROM chat_messages parent JOIN path child ON parent.id = child.parent_id
                    WHERE parent.thread_id = ? AND parent.user_id = ?
                ) SELECT * FROM path ORDER BY depth ASC""",
                (head, thread["_id"], thread["user_id"], thread["_id"], thread["user_id"]),
            )
        return [self._message_document(row) for row in rows]  # type: ignore[list-item]

    def get_active_path(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        thread = self.get_conversation(conversation_id, user_id)
        return self._get_path(thread, thread.get("active_message_id")) if thread else []

    def get_path_to_message(self, conversation_id: str, user_id: str, message_id: str) -> list[dict[str, Any]]:
        thread = self.get_conversation(conversation_id, user_id)
        message = self._get_message(message_id, thread["_id"], user_id) if thread else None
        return self._get_path(thread, message["_id"]) if thread and message else []

    def _touch_thread(self, thread_id: str, active_message_id: str | None = None) -> None:
        now = self._time()
        with self._lock, self._connection:
            if active_message_id:
                self._connection.execute("UPDATE chat_threads SET active_message_id = ?, updated_at = ?, last_message_at = ? WHERE id = ?", (active_message_id, now, now, thread_id))
            else:
                self._connection.execute("UPDATE chat_threads SET updated_at = ?, last_message_at = ? WHERE id = ?", (now, now, thread_id))

    def _insert_message(self, thread: dict[str, Any], parent: dict[str, Any], role: str, content: str, *, status: str = "complete", sibling_group_id: str | None = None, **extra: Any) -> dict[str, Any]:
        if parent["thread_id"] != thread["_id"] or parent["user_id"] != thread["user_id"]:
            raise ValueError("Parent message does not belong to this thread")
        message_id, now = self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
                (message_id, thread["_id"], thread["user_id"], parent["_id"], role, content, status, parent.get("depth", 0) + 1,
                 sibling_group_id, extra.get("reasoning_summary"), self._json_dump(extra.get("tool_events", [])),
                 self._json_dump(extra.get("timeline", [])), self._json_dump(extra.get("model_snapshot", {})), now, now),
            )
            self._connection.execute("UPDATE chat_threads SET active_message_id = ?, updated_at = ?, last_message_at = ? WHERE id = ?", (message_id, now, now, thread["_id"]))
        return self._get_message(message_id, thread["_id"], thread["user_id"])  # type: ignore[return-value]

    def create_user_message(self, conversation_id: str, user_id: str, content: str, parent_message_id: str | None = None) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        if not thread:
            return None
        parent = self._get_message(parent_message_id or thread.get("active_message_id") or thread.get("root_message_id"), thread["_id"], user_id)
        return self._insert_message(thread, parent, "user", content) if parent else None

    def _create_run(self, thread: dict[str, Any], message_id: str, snapshot: dict[str, Any] | None) -> str:
        run_id, now = self._id(), self._time()
        with self._lock, self._connection:
            self._connection.execute("INSERT INTO chat_runs VALUES (?, ?, ?, ?, ?, 'streaming', ?, NULL, ?, ?)", (run_id, thread["_id"], message_id, thread["user_id"], self._json_dump(snapshot or {}), now, now, now))
        return run_id

    def create_assistant_message(self, conversation_id: str, user_id: str, parent_message_id: str, model_snapshot: dict[str, Any] | None = None) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        parent = self._get_message(parent_message_id, thread["_id"], user_id) if thread else None
        if not thread or not parent or parent.get("role") != "user":
            return None
        message = self._insert_message(thread, parent, "assistant", "", status="streaming", model_snapshot=model_snapshot or {})
        run_id = self._create_run(thread, message["_id"], model_snapshot)
        with self._lock, self._connection:
            self._connection.execute("UPDATE chat_messages SET run_id = ? WHERE id = ?", (run_id, message["_id"]))
        return self._get_message(message["_id"], thread["_id"], user_id)

    def _create_sibling(self, source: dict[str, Any], content: str, *, status: str, **extra: Any) -> dict[str, Any]:
        if source.get("role") == "root" or not source.get("parent_id"):
            raise ValueError("The virtual root cannot have siblings")
        group_id = source.get("sibling_group_id") or self._id()
        if not source.get("sibling_group_id"):
            with self._lock, self._connection:
                self._connection.execute("UPDATE chat_messages SET sibling_group_id = ? WHERE id = ?", (group_id, source["_id"]))
        thread = self.get_conversation(source["thread_id"], source["user_id"])
        parent = self._get_message(source["parent_id"], source["thread_id"], source["user_id"])
        if not thread or not parent:
            raise ValueError("Source message has no valid thread parent")
        return self._insert_message(thread, parent, source["role"], content, status=status, sibling_group_id=group_id, **extra)

    def edit_user_message(self, conversation_id: str, user_id: str, message_id: str, content: str) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        source = self._get_message(message_id, thread["_id"], user_id) if thread else None
        return self._create_sibling(source, content, status="complete") if source and source.get("role") == "user" else None

    def retry_assistant_message(self, conversation_id: str, user_id: str, message_id: str, model_snapshot: dict[str, Any] | None = None) -> dict[str, Any] | None:
        thread = self.get_conversation(conversation_id, user_id)
        source = self._get_message(message_id, thread["_id"], user_id) if thread else None
        if not thread or not source or source.get("role") != "assistant":
            return None
        message = self._create_sibling(source, "", status="streaming", model_snapshot=model_snapshot or {})
        run_id = self._create_run(thread, message["_id"], model_snapshot)
        with self._lock, self._connection:
            self._connection.execute("UPDATE chat_messages SET run_id = ? WHERE id = ?", (run_id, message["_id"]))
        return self._get_message(message["_id"], thread["_id"], user_id)

    def _finish_assistant_message(self, message_id: str, content: str, status: str, **extra: Any) -> dict[str, Any] | None:
        now = self._time()
        assignments, params = ["content = ?", "status = ?", "updated_at = ?"], [content, status, now]
        for key in ("reasoning_summary", "tool_events", "timeline", "model_snapshot"):
            if key in extra:
                assignments.append(f"{key} = ?")
                params.append(self._json_dump(extra[key]) if key in {"tool_events", "timeline", "model_snapshot"} else extra[key])
        params.append(message_id)
        with self._lock, self._connection:
            self._connection.execute(f"UPDATE chat_messages SET {', '.join(assignments)} WHERE id = ? AND role = 'assistant'", tuple(params))
            message = self._message_document(self._one("SELECT * FROM chat_messages WHERE id = ?", (message_id,)))
            if message and message.get("run_id"):
                self._connection.execute("UPDATE chat_runs SET status = ?, finished_at = ?, updated_at = ? WHERE id = ?", ("complete" if status == "complete" else "error", now, now, message["run_id"]))
        return message

    def complete_assistant_message(self, message_id: str, content: str, **extra: Any) -> dict[str, Any] | None:
        return self._finish_assistant_message(message_id, content, "complete", **extra)

    def fail_assistant_message(self, message_id: str, content: str) -> dict[str, Any] | None:
        return self._finish_assistant_message(message_id, content, "error")

    def _latest_descendant_leaf(self, message: dict[str, Any]) -> dict[str, Any]:
        current = message
        while True:
            with self._lock:
                child = self._message_document(self._one("SELECT * FROM chat_messages WHERE thread_id = ? AND parent_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1", (current["thread_id"], current["_id"], current["user_id"])))
            if not child:
                return current
            current = child

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
        with self._lock:
            rows = self._all("SELECT * FROM chat_messages WHERE thread_id = ? AND parent_id = ? AND role = ? ORDER BY created_at ASC", (message["thread_id"], message["parent_id"], message["role"]))
        return [self._message_document(row) for row in rows]  # type: ignore[list-item]

    def list_messages(self, conversation_id: str, user_id: str) -> list[dict[str, Any]]:
        active_path = [message for message in self.get_active_path(conversation_id, user_id) if message.get("role") != "root"]
        if not active_path:
            return []
        parent_ids = sorted({message["parent_id"] for message in active_path if message.get("parent_id")})
        placeholders = ",".join("?" for _ in parent_ids)
        with self._lock:
            rows = self._all(f"SELECT * FROM chat_messages WHERE thread_id = ? AND parent_id IN ({placeholders}) ORDER BY created_at ASC", (active_path[0]["thread_id"], *parent_ids))
        versions: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            item = self._message_document(row)
            versions.setdefault((item["parent_id"], item["role"]), []).append(item)
        result: list[dict[str, Any]] = []
        for message in active_path:
            item = dict(message)
            siblings = versions.get((message["parent_id"], message["role"]), [message])
            ids = [sibling["_id"] for sibling in siblings]
            item["version_ids"] = ids
            item["sibling_count"] = len(ids)
            item["sibling_index"] = ids.index(message["_id"]) if message["_id"] in ids else 0
            result.append(item)
        return result

    def create_branch_conversation(self, conversation_id: str, user_id: str, source_message_id: str, title: str | None = None) -> dict[str, Any] | None:
        source_thread = self.get_conversation(conversation_id, user_id)
        source_message = self._get_message(source_message_id, source_thread["_id"], user_id) if source_thread else None
        if not source_thread or not source_message or source_message.get("role") == "root":
            return None
        copied = self.create_conversation({
            "user_id": user_id, "title": title or f"{source_thread.get('title', 'Untitled')} · branch",
            "provider_id": source_thread.get("provider_id"), "model": source_thread.get("model"),
            "temperature": source_thread.get("temperature", 0.7), "context_turns": source_thread.get("context_turns", 8),
            "assistant_id": source_thread.get("assistant_id"), "source_thread_id": source_thread["_id"], "source_message_id": source_message["_id"],
        })
        copied_path = self._get_path(source_thread, source_message["_id"])
        source_to_copy = {source_thread["root_message_id"]: copied["root_message_id"]}
        copied_active: str | None = None
        for source in copied_path:
            if source.get("role") == "root":
                continue
            parent = self._get_message(source_to_copy[source["parent_id"]], copied["_id"], user_id)
            copied_message = self._insert_message(copied, parent, source["role"], source.get("content", ""), status=source.get("status", "complete"), sibling_group_id=source.get("sibling_group_id"), reasoning_summary=source.get("reasoning_summary"), tool_events=source.get("tool_events", []), timeline=source.get("timeline", []), model_snapshot=source.get("model_snapshot", {}))
            source_to_copy[source["_id"]] = copied_message["_id"]
            copied_active = copied_message["_id"]
        if copied_active:
            self._touch_thread(copied["_id"], copied_active)
        return self.get_conversation(copied["_id"], user_id)

    def append_message(self, conversation_id: str, user_id: str, role: str, content: str, **extra: Any) -> dict[str, Any] | None:
        if role == "user":
            return self.create_user_message(conversation_id, user_id, content)
        thread = self.get_conversation(conversation_id, user_id)
        parent_id = thread.get("active_message_id") if thread else None
        message = self.create_assistant_message(conversation_id, user_id, parent_id or "") if parent_id else None
        return self.complete_assistant_message(message["_id"], content, **extra) if message else None
