from __future__ import annotations

from datetime import datetime
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


DEFAULT_PLAYGROUND_PREFERENCES: dict[str, Any] = {
    "provider_id": None,
    "model": None,
    "temperature": 1.0,
    "context_turns": 24,
    "thinking_level": "medium",
    "summary_provider_id": None,
    "summary_model": None,
    "summary_trigger_messages": 24,
    "summary_retain_messages": 8,
}


class SqlitePlaygroundRepository:
    """Playground-owned records sharing the chat repository transaction boundary."""

    def __init__(self, chat_repository: SqliteChatRepository):
        self.chat_repository = chat_repository
        self._connection = chat_repository._connection
        self._lock = chat_repository._lock
        self.ensure_schema()

    @classmethod
    def from_connection_owner(
        cls, chat_repository: SqliteChatRepository
    ) -> "SqlitePlaygroundRepository":
        return cls(chat_repository)

    def ensure_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS playground_preferences (
                    user_id TEXT PRIMARY KEY, provider_id TEXT, model TEXT,
                    temperature REAL NOT NULL DEFAULT 1.0,
                    context_turns INTEGER NOT NULL DEFAULT 24,
                    thinking_level TEXT NOT NULL DEFAULT 'medium',
                    summary_provider_id TEXT, summary_model TEXT,
                    summary_trigger_messages INTEGER NOT NULL DEFAULT 24,
                    summary_retain_messages INTEGER NOT NULL DEFAULT 8,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS playground_profiles (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    profile_type TEXT NOT NULL, name TEXT NOT NULL,
                    avatar_attachment_id TEXT, background_attachment_id TEXT,
                    main_prompt TEXT NOT NULL, opening_message TEXT NOT NULL,
                    settings_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS playground_profiles_by_user_type
                    ON playground_profiles(user_id, profile_type, updated_at DESC);
                CREATE TABLE IF NOT EXISTS playground_prompt_modules (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES playground_profiles(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, name TEXT NOT NULL, content TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    injection_position TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS playground_prompt_modules_by_profile
                    ON playground_prompt_modules(user_id, profile_id, injection_position, sort_order);
                CREATE TABLE IF NOT EXISTS playground_personas (
                    profile_id TEXT PRIMARY KEY REFERENCES playground_profiles(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
                    avatar_attachment_id TEXT, identity_text TEXT NOT NULL DEFAULT '',
                    background TEXT NOT NULL DEFAULT '', personality TEXT NOT NULL DEFAULT '',
                    initial_relationship TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1,
                    injection_position TEXT NOT NULL DEFAULT 'system_end', updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS playground_context_entries (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES playground_profiles(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                    activation_mode TEXT NOT NULL, keywords_json TEXT NOT NULL DEFAULT '[]',
                    scan_depth INTEGER NOT NULL DEFAULT 8,
                    injection_position TEXT NOT NULL DEFAULT 'system_end',
                    priority INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS playground_context_entries_by_profile
                    ON playground_context_entries(user_id, profile_id, injection_position, priority DESC);
                CREATE TABLE IF NOT EXISTS playground_conversation_summaries (
                    conversation_id TEXT PRIMARY KEY REFERENCES chat_threads(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL, content TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'idle',
                    summarized_through_message_id TEXT,
                    last_trigger_message_id TEXT,
                    trigger_new_message_count INTEGER NOT NULL DEFAULT 24,
                    retain_recent_message_count INTEGER NOT NULL DEFAULT 8,
                    provider_id TEXT, model TEXT,
                    injection_position TEXT NOT NULL DEFAULT 'system_end',
                    last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                """
            )

    def _one(self, sql: str, args: tuple[Any, ...] = ()):
        return self._connection.execute(sql, args).fetchone()

    def _all(self, sql: str, args: tuple[Any, ...] = ()):
        return self._connection.execute(sql, args).fetchall()

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    def _profile_document(self, row) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        item["settings"] = self.chat_repository._json_load(item.pop("settings_json"), {})
        item["created_at"] = self._parse_time(item.get("created_at"))
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def _prompt_module_document(self, row) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        item["enabled"] = bool(item["enabled"])
        item["created_at"] = self._parse_time(item.get("created_at"))
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def _persona_document(self, row) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def _context_entry_document(self, row) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["_id"] = item.pop("id")
        item["enabled"] = bool(item["enabled"])
        item["keywords"] = self.chat_repository._json_load(item.pop("keywords_json"), [])
        item["created_at"] = self._parse_time(item.get("created_at"))
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def _summary_document(self, row, conversation_id: str, user_id: str) -> dict[str, Any]:
        if row is None:
            return {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "content": "",
                "status": "idle",
                "summarized_through_message_id": None,
                "last_trigger_message_id": None,
                "trigger_new_message_count": DEFAULT_PLAYGROUND_PREFERENCES["summary_trigger_messages"],
                "retain_recent_message_count": DEFAULT_PLAYGROUND_PREFERENCES["summary_retain_messages"],
                "provider_id": None,
                "model": None,
                "injection_position": "system_end",
                "last_error": None,
                "created_at": None,
                "updated_at": None,
            }
        item = dict(row)
        item["created_at"] = self._parse_time(item.get("created_at"))
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._one("SELECT * FROM playground_preferences WHERE user_id = ?", (user_id,))
        if row is None:
            return {"user_id": user_id, **DEFAULT_PLAYGROUND_PREFERENCES, "created_at": None, "updated_at": None}
        item = dict(row)
        item["created_at"] = self._parse_time(item.get("created_at"))
        item["updated_at"] = self._parse_time(item.get("updated_at"))
        return item

    def save_preferences(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        values = {**self.get_preferences(user_id), **fields}
        now = self.chat_repository._time()
        created_at = values.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        created_at = created_at or now
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO playground_preferences(
                    user_id, provider_id, model, temperature, context_turns, thinking_level,
                    summary_provider_id, summary_model, summary_trigger_messages,
                    summary_retain_messages, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    provider_id=excluded.provider_id, model=excluded.model,
                    temperature=excluded.temperature, context_turns=excluded.context_turns,
                    thinking_level=excluded.thinking_level,
                    summary_provider_id=excluded.summary_provider_id,
                    summary_model=excluded.summary_model,
                    summary_trigger_messages=excluded.summary_trigger_messages,
                    summary_retain_messages=excluded.summary_retain_messages,
                    updated_at=excluded.updated_at""",
                (
                    user_id,
                    values.get("provider_id"),
                    values.get("model"),
                    float(values.get("temperature", 1.0)),
                    int(values.get("context_turns", 24)),
                    values.get("thinking_level", "medium"),
                    values.get("summary_provider_id"),
                    values.get("summary_model"),
                    int(values.get("summary_trigger_messages", 24)),
                    int(values.get("summary_retain_messages", 8)),
                    created_at,
                    now,
                ),
            )
        return self.get_preferences(user_id)

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile_id = payload.get("id") or self.chat_repository._id()
        now = self.chat_repository._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO playground_profiles(
                    id, user_id, profile_type, name, avatar_attachment_id,
                    background_attachment_id, main_prompt, opening_message,
                    settings_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile_id,
                    payload["user_id"],
                    payload["profile_type"],
                    payload["name"],
                    payload.get("avatar_attachment_id"),
                    payload.get("background_attachment_id"),
                    payload.get("main_prompt", ""),
                    payload.get("opening_message", ""),
                    self.chat_repository._json_dump(payload.get("settings", {})),
                    now,
                    now,
                ),
            )
        result = self.get_profile(profile_id, payload["user_id"])
        if result is None:
            raise RuntimeError("创建 Playground 资料失败")
        return result

    def get_profile(self, profile_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._one(
                "SELECT * FROM playground_profiles WHERE id = ? AND user_id = ?",
                (profile_id, user_id),
            )
        return self._profile_document(row)

    def list_profiles(self, user_id: str, profile_type: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if profile_type:
                rows = self._all(
                    """SELECT * FROM playground_profiles
                    WHERE user_id = ? AND profile_type = ? ORDER BY updated_at DESC""",
                    (user_id, profile_type),
                )
            else:
                rows = self._all(
                    "SELECT * FROM playground_profiles WHERE user_id = ? ORDER BY updated_at DESC",
                    (user_id,),
                )
        return [self._profile_document(row) for row in rows]  # type: ignore[list-item]

    def update_profile(self, profile_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {
            "profile_type", "name", "avatar_attachment_id", "background_attachment_id",
            "main_prompt", "opening_message", "settings",
        }
        values = {key: value for key, value in fields.items() if key in allowed}
        if not values:
            return self.get_profile(profile_id, user_id)
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in values.items():
            column = "settings_json" if key == "settings" else key
            assignments.append(f"{column} = ?")
            params.append(self.chat_repository._json_dump(value) if key == "settings" else value)
        params.extend([self.chat_repository._time(), profile_id, user_id])
        with self._lock, self._connection:
            self._connection.execute(
                f"UPDATE playground_profiles SET {', '.join(assignments)}, updated_at = ? WHERE id = ? AND user_id = ?",
                tuple(params),
            )
        return self.get_profile(profile_id, user_id)

    def delete_profile(self, profile_id: str, user_id: str) -> bool:
        with self._lock, self._connection:
            return bool(
                self._connection.execute(
                    "DELETE FROM playground_profiles WHERE id = ? AND user_id = ?",
                    (profile_id, user_id),
                ).rowcount
            )

    def delete_profile_with_conversations(self, profile_id: str, user_id: str) -> bool:
        """Delete one owned profile and only its owned Playground conversations."""

        profile = self.get_profile(profile_id, user_id)
        if profile is None:
            return False
        with self._lock, self._connection:
            self._connection.execute(
                """DELETE FROM chat_threads
                WHERE user_id = ? AND workspace_type = 'playground'
                  AND owner_type = ? AND owner_id = ?""",
                (user_id, profile["profile_type"], profile_id),
            )
            deleted = self._connection.execute(
                "DELETE FROM playground_profiles WHERE id = ? AND user_id = ?",
                (profile_id, user_id),
            ).rowcount
        return bool(deleted)

    def replace_prompt_modules(
        self, profile_id: str, user_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        now = self.chat_repository._time()
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM playground_prompt_modules WHERE profile_id = ? AND user_id = ?",
                (profile_id, user_id),
            )
            for item in items:
                self._connection.execute(
                    """INSERT INTO playground_prompt_modules(
                        id, profile_id, user_id, name, content, enabled,
                        injection_position, sort_order, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("id") or self.chat_repository._id(), profile_id, user_id,
                        item["name"], item["content"], int(bool(item.get("enabled", True))),
                        item.get("injection_position", "system_end"), int(item.get("sort_order", 0)),
                        now, now,
                    ),
                )
        return self.list_prompt_modules(profile_id, user_id)

    def list_prompt_modules(self, profile_id: str, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._all(
                """SELECT * FROM playground_prompt_modules
                WHERE profile_id = ? AND user_id = ? ORDER BY injection_position, sort_order, created_at""",
                (profile_id, user_id),
            )
        return [self._prompt_module_document(row) for row in rows]  # type: ignore[list-item]

    def upsert_persona(
        self, profile_id: str, user_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        now = self.chat_repository._time()
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO playground_personas(
                    profile_id, user_id, name, avatar_attachment_id, identity_text,
                    background, personality, initial_relationship, enabled,
                    injection_position, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    user_id=excluded.user_id, name=excluded.name,
                    avatar_attachment_id=excluded.avatar_attachment_id,
                    identity_text=excluded.identity_text, background=excluded.background,
                    personality=excluded.personality,
                    initial_relationship=excluded.initial_relationship,
                    enabled=excluded.enabled,
                    injection_position=excluded.injection_position,
                    updated_at=excluded.updated_at""",
                (
                    profile_id, user_id, payload.get("name", ""), payload.get("avatar_attachment_id"),
                    payload.get("identity_text", ""), payload.get("background", ""),
                    payload.get("personality", ""), payload.get("initial_relationship", ""),
                    int(bool(payload.get("enabled", True))),
                    payload.get("injection_position", "system_end"), now,
                ),
            )
        result = self.get_persona(profile_id, user_id)
        if result is None:
            raise RuntimeError("保存用户人设失败")
        return result

    def get_persona(self, profile_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._one(
                "SELECT * FROM playground_personas WHERE profile_id = ? AND user_id = ?",
                (profile_id, user_id),
            )
        return self._persona_document(row)

    def replace_context_entries(
        self, profile_id: str, user_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        now = self.chat_repository._time()
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM playground_context_entries WHERE profile_id = ? AND user_id = ?",
                (profile_id, user_id),
            )
            for item in items:
                self._connection.execute(
                    """INSERT INTO playground_context_entries(
                        id, profile_id, user_id, name, category, content, enabled,
                        activation_mode, keywords_json, scan_depth, injection_position,
                        priority, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("id") or self.chat_repository._id(), profile_id, user_id,
                        item["name"], item.get("category", ""), item["content"],
                        int(bool(item.get("enabled", True))), item.get("activation_mode", "constant"),
                        self.chat_repository._json_dump(item.get("keywords", [])),
                        int(item.get("scan_depth", 8)), item.get("injection_position", "system_end"),
                        int(item.get("priority", 0)), now, now,
                    ),
                )
        return self.list_context_entries(profile_id, user_id)

    def list_context_entries(self, profile_id: str, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._all(
                """SELECT * FROM playground_context_entries
                WHERE profile_id = ? AND user_id = ?
                ORDER BY injection_position, priority DESC, created_at""",
                (profile_id, user_id),
            )
        return [self._context_entry_document(row) for row in rows]  # type: ignore[list-item]

    def get_summary(self, conversation_id: str, user_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._one(
                """SELECT * FROM playground_conversation_summaries
                WHERE conversation_id = ? AND user_id = ?""",
                (conversation_id, user_id),
            )
        return self._summary_document(row, conversation_id, user_id)

    def save_summary(
        self, conversation_id: str, user_id: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        values = {**self.get_summary(conversation_id, user_id), **fields}
        now = self.chat_repository._time()
        created_at = values.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        created_at = created_at or now
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO playground_conversation_summaries(
                    conversation_id, user_id, content, status,
                    summarized_through_message_id, last_trigger_message_id,
                    trigger_new_message_count, retain_recent_message_count,
                    provider_id, model, injection_position, last_error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    user_id=excluded.user_id, content=excluded.content, status=excluded.status,
                    summarized_through_message_id=excluded.summarized_through_message_id,
                    last_trigger_message_id=excluded.last_trigger_message_id,
                    trigger_new_message_count=excluded.trigger_new_message_count,
                    retain_recent_message_count=excluded.retain_recent_message_count,
                    provider_id=excluded.provider_id, model=excluded.model,
                    injection_position=excluded.injection_position,
                    last_error=excluded.last_error, updated_at=excluded.updated_at""",
                (
                    conversation_id, user_id, values.get("content", ""), values.get("status", "idle"),
                    values.get("summarized_through_message_id"), values.get("last_trigger_message_id"),
                    int(values.get("trigger_new_message_count", 24)),
                    int(values.get("retain_recent_message_count", 8)),
                    values.get("provider_id"), values.get("model"),
                    values.get("injection_position", "system_end"), values.get("last_error"),
                    created_at, now,
                ),
            )
        return self.get_summary(conversation_id, user_id)

    def try_mark_summary_running(
        self,
        conversation_id: str,
        user_id: str,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Atomically acquire one conversation's summary maintenance slot."""

        values = {**self.get_summary(conversation_id, user_id), **(fields or {})}
        now = self.chat_repository._time()
        with self._lock, self._connection:
            row = self._one(
                """SELECT status FROM playground_conversation_summaries
                WHERE conversation_id = ? AND user_id = ?""",
                (conversation_id, user_id),
            )
            if row is not None and row["status"] == "running":
                return None
            if row is None:
                self._connection.execute(
                    """INSERT INTO playground_conversation_summaries(
                        conversation_id, user_id, content, status,
                        summarized_through_message_id, last_trigger_message_id,
                        trigger_new_message_count, retain_recent_message_count,
                        provider_id, model, injection_position, last_error,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
                    (
                        conversation_id,
                        user_id,
                        values.get("content", ""),
                        values.get("summarized_through_message_id"),
                        values.get("last_trigger_message_id"),
                        int(values.get("trigger_new_message_count", 24)),
                        int(values.get("retain_recent_message_count", 8)),
                        values.get("provider_id"),
                        values.get("model"),
                        values.get("injection_position", "system_end"),
                        now,
                        now,
                    ),
                )
            else:
                self._connection.execute(
                    """UPDATE playground_conversation_summaries SET
                        status = 'running', trigger_new_message_count = ?,
                        retain_recent_message_count = ?, provider_id = ?, model = ?,
                        injection_position = ?, last_error = NULL, updated_at = ?
                    WHERE conversation_id = ? AND user_id = ?""",
                    (
                        int(values.get("trigger_new_message_count", 24)),
                        int(values.get("retain_recent_message_count", 8)),
                        values.get("provider_id"),
                        values.get("model"),
                        values.get("injection_position", "system_end"),
                        now,
                        conversation_id,
                        user_id,
                    ),
                )
        return self.get_summary(conversation_id, user_id)
