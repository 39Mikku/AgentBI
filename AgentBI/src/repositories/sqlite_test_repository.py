from __future__ import annotations

import base64
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterator, Literal, Mapping
from uuid import uuid4


GENERATION_LEASE_DURATION = timedelta(minutes=10)
ANALYSIS_LEASE_DURATION = timedelta(minutes=10)
MAX_SAFE_ERROR_LENGTH = 500


class TestRepositoryConflictError(RuntimeError):
    """A requested Test state transition conflicts with the current state."""


class TestAttemptConflictError(TestRepositoryConflictError):
    pass


class TestSessionConflictError(TestRepositoryConflictError):
    pass


@dataclass(frozen=True)
class GenerationReservation:
    state: Literal["acquired", "in_progress", "completed", "failed"]
    acquired: bool
    lease_id: str | None
    test_id: str | None
    error_message: str | None


@dataclass(frozen=True)
class AnalysisReservation:
    state: Literal["acquired", "in_progress", "completed", "failed"]
    acquired: bool
    lease_id: str | None
    attempt: dict[str, object]


@dataclass(frozen=True)
class TestSessionPage:
    items: list[dict[str, object]]
    next_cursor: str | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _mapping(value: Any) -> dict[str, Any]:
    plain = _jsonable(value)
    if not isinstance(plain, dict):
        raise TypeError("repository payload must be a mapping or Pydantic model")
    return plain


def _dump_json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, separators=(",", ":"))


def _decode_json(value: str | None) -> Any:
    return None if value is None else json.loads(value)


def _safe_error(value: object) -> str:
    return " ".join(str(value).split())[:MAX_SAFE_ERROR_LENGTH]


def _safe_model_snapshot(value: Any) -> dict[str, Any]:
    snapshot = _mapping(value)
    return {
        "provider_id": snapshot["provider_id"],
        "provider_name": snapshot["provider_name"],
        "model": snapshot["model"],
        "temperature": snapshot.get("temperature", 1.0),
        "captured_at": snapshot["captured_at"],
    }


class SqliteTestRepository:
    """SQLite persistence and lease-safe state transitions for the Test product."""

    def __init__(self, path: str, clock: Callable[[], datetime] | None = None):
        if path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._clock = clock or _utc_now
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
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS test_preferences (
                    user_id TEXT PRIMARY KEY,
                    generation_provider_id TEXT NULL,
                    generation_model TEXT NULL,
                    analysis_provider_id TEXT NULL,
                    analysis_model TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS test_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK(mode IN ('knowledge', 'fun')),
                    topic TEXT NOT NULL,
                    requirements TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    question_count INTEGER NOT NULL CHECK(question_count IN (5, 10, 15, 20)),
                    difficulty TEXT NULL CHECK(difficulty IS NULL OR difficulty IN ('beginner', 'intermediate', 'advanced')),
                    questionnaire_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL DEFAULT 1,
                    generation_provider_id TEXT NOT NULL,
                    generation_model TEXT NOT NULL,
                    generation_snapshot_json TEXT NOT NULL,
                    create_request_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, create_request_id),
                    CHECK((mode = 'fun' AND difficulty IS NULL) OR (mode = 'knowledge' AND difficulty IS NOT NULL))
                );

                CREATE TABLE IF NOT EXISTS test_attempts (
                    id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL REFERENCES test_sessions(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('draft', 'analyzing', 'completed', 'failed')),
                    score REAL NULL,
                    max_score REAL NULL,
                    correct_count INTEGER NULL,
                    result_json TEXT NULL,
                    analysis_provider_id TEXT NULL,
                    analysis_model TEXT NULL,
                    analysis_snapshot_json TEXT NULL,
                    submission_token TEXT NULL UNIQUE,
                    create_request_id TEXT NOT NULL,
                    error_message TEXT NULL,
                    analysis_started_at TEXT NULL,
                    analysis_lease_id TEXT NULL,
                    started_at TEXT NOT NULL,
                    submitted_at TEXT NULL,
                    completed_at TEXT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, create_request_id)
                );

                CREATE TABLE IF NOT EXISTS test_answers (
                    attempt_id TEXT NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE,
                    question_id TEXT NOT NULL,
                    selected_option_id TEXT NOT NULL,
                    answered_at TEXT NOT NULL,
                    PRIMARY KEY(attempt_id, question_id)
                );

                CREATE TABLE IF NOT EXISTS test_analysis_runs (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL REFERENCES test_attempts(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    request_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'abandoned')),
                    provider_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NULL,
                    error_message TEXT NULL,
                    UNIQUE(attempt_id, ordinal),
                    UNIQUE(attempt_id, request_id)
                );

                CREATE TABLE IF NOT EXISTS test_creation_requests (
                    user_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('generating', 'completed', 'failed')),
                    test_id TEXT NULL,
                    lease_id TEXT NULL UNIQUE,
                    generation_started_at TEXT NULL,
                    error_message TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(user_id, request_id)
                );

                CREATE INDEX IF NOT EXISTS test_sessions_by_user_updated
                    ON test_sessions(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS test_sessions_by_user_mode_updated
                    ON test_sessions(user_id, mode, updated_at DESC);
                CREATE INDEX IF NOT EXISTS test_attempts_by_test_started
                    ON test_attempts(test_id, started_at DESC);
                CREATE INDEX IF NOT EXISTS test_attempts_by_user_updated
                    ON test_attempts(user_id, updated_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS test_attempts_one_active_per_test
                    ON test_attempts(test_id) WHERE status IN ('draft', 'analyzing');
                """
            )

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def _now(self, value: datetime | None = None) -> datetime:
        current = value or self._clock()
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc)

    def _now_text(self, value: datetime | None = None) -> str:
        return self._now(value).isoformat()

    def get_preferences(self, user_id: str) -> dict[str, object] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM test_preferences WHERE user_id = ?", (user_id,)
            ).fetchone()
        return dict(row) if row else None

    def save_preferences(self, user_id: str, fields: Any) -> dict[str, object]:
        payload = (
            fields.model_dump(mode="json", exclude_unset=True)
            if hasattr(fields, "model_dump")
            else _mapping(fields)
        )
        allowed = (
            "generation_provider_id",
            "generation_model",
            "analysis_provider_id",
            "analysis_model",
        )
        now = self._now_text()
        with self._transaction():
            existing = self._connection.execute(
                "SELECT * FROM test_preferences WHERE user_id = ?", (user_id,)
            ).fetchone()
            values = {
                key: payload[key] if key in payload else (existing[key] if existing else None)
                for key in allowed
            }
            self._connection.execute(
                """
                INSERT INTO test_preferences(
                    user_id, generation_provider_id, generation_model,
                    analysis_provider_id, analysis_model, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    generation_provider_id = excluded.generation_provider_id,
                    generation_model = excluded.generation_model,
                    analysis_provider_id = excluded.analysis_provider_id,
                    analysis_model = excluded.analysis_model,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    values["generation_provider_id"],
                    values["generation_model"],
                    values["analysis_provider_id"],
                    values["analysis_model"],
                    existing["created_at"] if existing else now,
                    now,
                ),
            )
        stored = self.get_preferences(user_id)
        assert stored is not None
        return stored

    def reserve_generation(
        self, user_id: str, request_id: str, retry_failed: bool = False
    ) -> GenerationReservation:
        self.recover_stale_generations(request_id=request_id, user_id=user_id)
        now = self._now_text()
        with self._transaction():
            row = self._connection.execute(
                "SELECT * FROM test_creation_requests WHERE user_id = ? AND request_id = ?",
                (user_id, str(request_id)),
            ).fetchone()
            if row is None:
                lease_id = str(uuid4())
                self._connection.execute(
                    """
                    INSERT INTO test_creation_requests(
                        user_id, request_id, status, test_id, lease_id,
                        generation_started_at, error_message, created_at, updated_at
                    ) VALUES (?, ?, 'generating', NULL, ?, ?, NULL, ?, ?)
                    """,
                    (user_id, str(request_id), lease_id, now, now, now),
                )
                return GenerationReservation("acquired", True, lease_id, None, None)
            if row["status"] == "completed":
                return GenerationReservation("completed", False, None, row["test_id"], None)
            if row["status"] == "generating":
                return GenerationReservation("in_progress", False, None, row["test_id"], None)
            if not retry_failed:
                return GenerationReservation("failed", False, None, row["test_id"], row["error_message"])
            lease_id = str(uuid4())
            changed = self._connection.execute(
                """
                UPDATE test_creation_requests
                SET status = 'generating', test_id = NULL, lease_id = ?,
                    generation_started_at = ?, error_message = NULL, updated_at = ?
                WHERE user_id = ? AND request_id = ? AND status = 'failed'
                """,
                (lease_id, now, now, user_id, str(request_id)),
            ).rowcount
            if changed == 1:
                return GenerationReservation("acquired", True, lease_id, None, None)
            return GenerationReservation("in_progress", False, None, None, None)

    def get_generation_status(
        self, user_id: str, request_id: str
    ) -> GenerationReservation | None:
        self.recover_stale_generations(request_id=request_id, user_id=user_id)
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM test_creation_requests WHERE user_id = ? AND request_id = ?",
                (user_id, str(request_id)),
            ).fetchone()
        if row is None:
            return None
        state = {
            "generating": "in_progress",
            "completed": "completed",
            "failed": "failed",
        }[row["status"]]
        return GenerationReservation(state, False, None, row["test_id"], row["error_message"])

    def complete_generation(
        self,
        user_id: str,
        request_id: str,
        lease_id: str | None,
        bundle: Any,
    ) -> bool:
        if not lease_id:
            return False
        payload = _mapping(bundle)
        questionnaire = _mapping(payload["questionnaire"])
        snapshot = _safe_model_snapshot(payload["generation_snapshot"])
        now = self._now_text()
        test_id = str(uuid4())
        attempt_id = str(uuid4())
        with self._transaction():
            current = self._connection.execute(
                """
                SELECT 1 FROM test_creation_requests
                WHERE user_id = ? AND request_id = ? AND status = 'generating' AND lease_id = ?
                """,
                (user_id, str(request_id), lease_id),
            ).fetchone()
            if current is None:
                return False
            self._connection.execute(
                """
                INSERT INTO test_sessions(
                    id, user_id, mode, topic, requirements, title, description,
                    question_count, difficulty, questionnaire_json, schema_version,
                    generation_provider_id, generation_model, generation_snapshot_json,
                    create_request_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_id,
                    user_id,
                    payload["mode"],
                    payload["topic"],
                    payload.get("requirements", ""),
                    payload["title"],
                    payload.get("description", ""),
                    payload["question_count"],
                    payload.get("difficulty"),
                    _dump_json(questionnaire),
                    payload["generation_provider_id"],
                    payload["generation_model"],
                    _dump_json(snapshot),
                    str(request_id),
                    now,
                    now,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO test_attempts(
                    id, test_id, user_id, status, create_request_id, started_at, updated_at
                ) VALUES (?, ?, ?, 'draft', ?, ?, ?)
                """,
                (attempt_id, test_id, user_id, str(request_id), now, now),
            )
            changed = self._connection.execute(
                """
                UPDATE test_creation_requests
                SET status = 'completed', test_id = ?, lease_id = NULL,
                    generation_started_at = NULL, error_message = NULL, updated_at = ?
                WHERE user_id = ? AND request_id = ? AND status = 'generating' AND lease_id = ?
                """,
                (test_id, now, user_id, str(request_id), lease_id),
            ).rowcount
            if changed != 1:
                raise RuntimeError("generation lease changed during transaction")
        return True

    def fail_generation(
        self, user_id: str, request_id: str, lease_id: str | None, safe_error: object
    ) -> bool:
        if not lease_id:
            return False
        now = self._now_text()
        with self._transaction():
            changed = self._connection.execute(
                """
                UPDATE test_creation_requests
                SET status = 'failed', lease_id = NULL, generation_started_at = NULL,
                    error_message = ?, updated_at = ?
                WHERE user_id = ? AND request_id = ? AND status = 'generating' AND lease_id = ?
                """,
                (_safe_error(safe_error), now, user_id, str(request_id), lease_id),
            ).rowcount
        return changed == 1

    def recover_stale_generations(
        self,
        now: datetime | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        cutoff = (self._now(now) - GENERATION_LEASE_DURATION).isoformat()
        current = self._now_text(now)
        clauses = ["status = 'generating'", "generation_started_at <= ?"]
        args: list[object] = [cutoff]
        if request_id is not None:
            clauses.append("request_id = ?")
            args.append(str(request_id))
        if user_id is not None:
            clauses.append("user_id = ?")
            args.append(user_id)
        with self._transaction():
            changed = self._connection.execute(
                f"""
                UPDATE test_creation_requests
                SET status = 'failed', lease_id = NULL, generation_started_at = NULL,
                    error_message = 'Generation timed out.', updated_at = ?
                WHERE {' AND '.join(clauses)}
                """,
                (current, *args),
            ).rowcount
        return changed

    @staticmethod
    def _encode_cursor(updated_at: str, session_id: str) -> str:
        raw = json.dumps([updated_at, session_id], separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[str, str]:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, str) for item in value):
            raise ValueError("invalid Test session cursor")
        return value[0], value[1]

    def list_sessions(
        self,
        user_id: str,
        mode: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> TestSessionPage:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        clauses = ["user_id = ?"]
        args: list[object] = [user_id]
        if mode is not None:
            clauses.append("mode = ?")
            args.append(mode)
        if cursor is not None:
            updated_at, session_id = self._decode_cursor(cursor)
            clauses.append("(updated_at < ? OR (updated_at = ? AND id < ?))")
            args.extend((updated_at, updated_at, session_id))
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT id, title, description, mode, question_count, updated_at
                FROM test_sessions WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC, id DESC LIMIT ?
                """,
                (*args, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        visible = rows[:limit]
        items = [dict(row) for row in visible]
        next_cursor = None
        if has_more and visible:
            next_cursor = self._encode_cursor(visible[-1]["updated_at"], visible[-1]["id"])
        return TestSessionPage(items=items, next_cursor=next_cursor)

    def get_session(self, test_id: str | None, user_id: str) -> dict[str, object] | None:
        if test_id is None:
            return None
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM test_sessions WHERE id = ? AND user_id = ?", (test_id, user_id)
            ).fetchone()
            attempts = self._connection.execute(
                """
                SELECT id, status, started_at, submitted_at, completed_at, updated_at, score
                FROM test_attempts WHERE test_id = ? AND user_id = ?
                ORDER BY started_at DESC, id DESC
                """,
                (test_id, user_id),
            ).fetchall()
        if row is None:
            return None
        document = dict(row)
        document["questionnaire"] = _decode_json(document.pop("questionnaire_json"))
        document["generation_snapshot"] = _decode_json(document.pop("generation_snapshot_json"))
        document["attempts"] = [dict(attempt) for attempt in attempts]
        return document

    def delete_session(self, test_id: str, user_id: str) -> bool:
        self.recover_stale_analyses(user_id=user_id)
        with self._transaction():
            active = self._connection.execute(
                """
                SELECT 1 FROM test_attempts
                WHERE test_id = ? AND user_id = ? AND status = 'analyzing'
                """,
                (test_id, user_id),
            ).fetchone()
            if active is not None:
                raise TestSessionConflictError("an actively analyzed Test session cannot be deleted")
            changed = self._connection.execute(
                "DELETE FROM test_sessions WHERE id = ? AND user_id = ?", (test_id, user_id)
            ).rowcount
        return changed == 1

    def create_or_resume_attempt(
        self, test_id: str, user_id: str, request_id: str
    ) -> dict[str, object] | None:
        now = self._now_text()
        with self._transaction():
            session = self._connection.execute(
                "SELECT 1 FROM test_sessions WHERE id = ? AND user_id = ?", (test_id, user_id)
            ).fetchone()
            if session is None:
                return None
            existing = self._connection.execute(
                """
                SELECT id FROM test_attempts
                WHERE test_id = ? AND user_id = ? AND status IN ('draft', 'analyzing')
                """,
                (test_id, user_id),
            ).fetchone()
            if existing is None:
                existing = self._connection.execute(
                    """
                    SELECT id FROM test_attempts
                    WHERE test_id = ? AND user_id = ? AND create_request_id = ?
                    """,
                    (test_id, user_id, str(request_id)),
                ).fetchone()
            if existing is not None:
                attempt_id = existing["id"]
            else:
                collision = self._connection.execute(
                    """
                    SELECT 1 FROM test_attempts
                    WHERE user_id = ? AND create_request_id = ? AND test_id <> ?
                    """,
                    (user_id, str(request_id), test_id),
                ).fetchone()
                if collision is not None:
                    raise TestAttemptConflictError(
                        "attempt request id is already bound to another Test session"
                    )
                attempt_id = str(uuid4())
                self._connection.execute(
                    """
                    INSERT INTO test_attempts(
                        id, test_id, user_id, status, create_request_id, started_at, updated_at
                    ) VALUES (?, ?, ?, 'draft', ?, ?, ?)
                    """,
                    (attempt_id, test_id, user_id, str(request_id), now, now),
                )
                self._connection.execute(
                    "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                    (now, test_id, user_id),
                )
        return self.get_attempt(attempt_id, user_id)

    def get_attempt(self, attempt_id: str, user_id: str) -> dict[str, object] | None:
        self.recover_stale_analyses(attempt_id=attempt_id, user_id=user_id)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT a.*, s.mode, s.questionnaire_json
                FROM test_attempts a
                JOIN test_sessions s ON s.id = a.test_id AND s.user_id = a.user_id
                WHERE a.id = ? AND a.user_id = ?
                """,
                (attempt_id, user_id),
            ).fetchone()
            answers = self._connection.execute(
                """
                SELECT question_id, selected_option_id FROM test_answers
                WHERE attempt_id = ? ORDER BY question_id
                """,
                (attempt_id,),
            ).fetchall()
        if row is None:
            return None
        document = dict(row)
        document["questionnaire"] = _decode_json(document.pop("questionnaire_json"))
        document["result"] = _decode_json(document.pop("result_json"))
        document["analysis_snapshot"] = _decode_json(document.pop("analysis_snapshot_json"))
        document["answers"] = [dict(answer) for answer in answers]
        return document

    def save_answers(self, attempt_id: str, user_id: str, answers: Any) -> dict[str, object]:
        selections = [_mapping(answer) for answer in answers]
        now = self._now_text()
        with self._transaction():
            attempt = self._connection.execute(
                """
                SELECT a.test_id, a.status, s.questionnaire_json
                FROM test_attempts a
                JOIN test_sessions s ON s.id = a.test_id AND s.user_id = a.user_id
                WHERE a.id = ? AND a.user_id = ?
                """,
                (attempt_id, user_id),
            ).fetchone()
            if attempt is None:
                raise KeyError("unknown Test attempt")
            if attempt["status"] != "draft":
                raise TestAttemptConflictError("answers can only be saved to a draft attempt")
            questionnaire = _decode_json(attempt["questionnaire_json"])
            questions = questionnaire.get("questions", [])
            options = {
                question["id"]: {option["id"] for option in question.get("options", [])}
                for question in questions
            }
            question_ids = [answer.get("question_id") for answer in selections]
            if len(question_ids) != len(set(question_ids)) or any(
                question_id not in options for question_id in question_ids
            ):
                raise ValueError("answers must identify questionnaire questions at most once")
            if any(
                answer.get("selected_option_id") not in options[answer["question_id"]]
                for answer in selections
            ):
                raise ValueError("selected option must belong to its questionnaire question")
            for answer in selections:
                self._connection.execute(
                    """
                    INSERT INTO test_answers(attempt_id, question_id, selected_option_id, answered_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(attempt_id, question_id) DO UPDATE SET
                        selected_option_id = excluded.selected_option_id,
                        answered_at = excluded.answered_at
                    """,
                    (attempt_id, answer["question_id"], answer["selected_option_id"], now),
                )
            self._connection.execute(
                "UPDATE test_attempts SET updated_at = ? WHERE id = ?", (now, attempt_id)
            )
            self._connection.execute(
                "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (now, attempt["test_id"], user_id),
            )
        stored = self.get_attempt(attempt_id, user_id)
        assert stored is not None
        return stored

    @staticmethod
    def _validate_answer_snapshot(
        questionnaire: dict[str, Any], answers: list[dict[str, Any]]
    ) -> None:
        questions = questionnaire.get("questions")
        if not isinstance(questions, list):
            raise ValueError("questionnaire questions are invalid")
        expected = {question["id"] for question in questions}
        actual = [answer.get("question_id") for answer in answers]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("final answers must contain each questionnaire question exactly once")
        options = {
            question["id"]: {option["id"] for option in question.get("options", [])}
            for question in questions
        }
        if any(
            answer.get("selected_option_id") not in options[answer["question_id"]]
            for answer in answers
        ):
            raise ValueError("selected option must belong to its questionnaire question")

    def begin_analysis(
        self,
        attempt_id: str,
        user_id: str,
        request_id: str,
        answers: Any,
        model_snapshot: Any,
        knowledge_score: Any | None = None,
    ) -> AnalysisReservation:
        self.recover_stale_analyses(attempt_id=attempt_id, user_id=user_id)
        selections = [_mapping(answer) for answer in answers]
        snapshot = _safe_model_snapshot(model_snapshot)
        score = _mapping(knowledge_score) if knowledge_score is not None else None
        request_text = str(request_id)
        now = self._now_text()
        with self._transaction():
            attempt = self._connection.execute(
                """
                SELECT a.*, s.mode, s.questionnaire_json
                FROM test_attempts a
                JOIN test_sessions s ON s.id = a.test_id AND s.user_id = a.user_id
                WHERE a.id = ? AND a.user_id = ?
                """,
                (attempt_id, user_id),
            ).fetchone()
            if attempt is None:
                raise KeyError("unknown Test attempt")

            existing_run = self._connection.execute(
                """
                SELECT status FROM test_analysis_runs
                WHERE attempt_id = ? AND request_id = ?
                """,
                (attempt_id, request_text),
            ).fetchone()
            if existing_run is not None:
                state = {
                    "running": "in_progress",
                    "completed": "completed",
                    "failed": "failed",
                    "abandoned": "failed",
                }[existing_run["status"]]
                document = self._attempt_document_in_transaction(attempt_id, user_id)
                return AnalysisReservation(state, False, None, document)

            if attempt["status"] == "completed":
                document = self._attempt_document_in_transaction(attempt_id, user_id)
                return AnalysisReservation("completed", False, None, document)
            if attempt["status"] == "analyzing":
                document = self._attempt_document_in_transaction(attempt_id, user_id)
                return AnalysisReservation("in_progress", False, None, document)
            if attempt["status"] not in {"draft", "failed"}:
                document = self._attempt_document_in_transaction(attempt_id, user_id)
                return AnalysisReservation("failed", False, None, document)

            questionnaire = _decode_json(attempt["questionnaire_json"])
            self._validate_answer_snapshot(questionnaire, selections)
            lease_id = str(uuid4())
            run_id = str(uuid4())
            ordinal = self._connection.execute(
                "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM test_analysis_runs WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()[0]

            self._connection.execute("DELETE FROM test_answers WHERE attempt_id = ?", (attempt_id,))
            self._connection.executemany(
                """
                INSERT INTO test_answers(attempt_id, question_id, selected_option_id, answered_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (attempt_id, answer["question_id"], answer["selected_option_id"], now)
                    for answer in selections
                ],
            )
            is_knowledge = attempt["mode"] == "knowledge"
            changed = self._connection.execute(
                """
                UPDATE test_attempts
                SET status = 'analyzing',
                    score = ?, max_score = ?, correct_count = ?,
                    result_json = NULL,
                    analysis_provider_id = ?, analysis_model = ?, analysis_snapshot_json = ?,
                    submission_token = ?, error_message = NULL,
                    analysis_started_at = ?, analysis_lease_id = ?,
                    submitted_at = COALESCE(submitted_at, ?), completed_at = NULL, updated_at = ?
                WHERE id = ? AND user_id = ? AND status IN ('draft', 'failed')
                """,
                (
                    score.get("score") if is_knowledge and score else None,
                    score.get("max_score") if is_knowledge and score else None,
                    score.get("correct_count") if is_knowledge and score else None,
                    snapshot["provider_id"],
                    snapshot["model"],
                    _dump_json(snapshot),
                    _dump_json([user_id, attempt_id, request_text]),
                    now,
                    lease_id,
                    now,
                    now,
                    attempt_id,
                    user_id,
                ),
            ).rowcount
            if changed != 1:
                raise TestAttemptConflictError("attempt state changed before analysis could start")
            self._connection.execute(
                """
                INSERT INTO test_analysis_runs(
                    id, attempt_id, ordinal, request_id, lease_id, status,
                    provider_id, model, snapshot_json, started_at
                ) VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?, ?)
                """,
                (
                    run_id,
                    attempt_id,
                    ordinal,
                    request_text,
                    lease_id,
                    snapshot["provider_id"],
                    snapshot["model"],
                    _dump_json(snapshot),
                    now,
                ),
            )
            self._connection.execute(
                "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (now, attempt["test_id"], user_id),
            )
            document = self._attempt_document_in_transaction(attempt_id, user_id)
            return AnalysisReservation("acquired", True, lease_id, document)

    def _attempt_document_in_transaction(
        self, attempt_id: str, user_id: str
    ) -> dict[str, object]:
        row = self._connection.execute(
            """
            SELECT a.*, s.mode, s.questionnaire_json
            FROM test_attempts a
            JOIN test_sessions s ON s.id = a.test_id AND s.user_id = a.user_id
            WHERE a.id = ? AND a.user_id = ?
            """,
            (attempt_id, user_id),
        ).fetchone()
        if row is None:
            return {}
        answers = self._connection.execute(
            """
            SELECT question_id, selected_option_id FROM test_answers
            WHERE attempt_id = ? ORDER BY question_id
            """,
            (attempt_id,),
        ).fetchall()
        document = dict(row)
        document["questionnaire"] = _decode_json(document.pop("questionnaire_json"))
        document["result"] = _decode_json(document.pop("result_json"))
        document["analysis_snapshot"] = _decode_json(document.pop("analysis_snapshot_json"))
        document["answers"] = [dict(answer) for answer in answers]
        return document

    def complete_analysis(
        self, attempt_id: str, lease_id: str | None, result: Any
    ) -> bool:
        if not lease_id:
            return False
        result_json = _dump_json(result)
        now = self._now_text()
        with self._transaction():
            attempt = self._connection.execute(
                """
                SELECT test_id, user_id FROM test_attempts
                WHERE id = ? AND status = 'analyzing' AND analysis_lease_id = ?
                """,
                (attempt_id, lease_id),
            ).fetchone()
            run = self._connection.execute(
                """
                SELECT id FROM test_analysis_runs
                WHERE attempt_id = ? AND lease_id = ? AND status = 'running'
                """,
                (attempt_id, lease_id),
            ).fetchone()
            if attempt is None or run is None:
                return False
            run_changed = self._connection.execute(
                """
                UPDATE test_analysis_runs
                SET status = 'completed', finished_at = ?, error_message = NULL
                WHERE id = ? AND status = 'running' AND lease_id = ?
                """,
                (now, run["id"], lease_id),
            ).rowcount
            attempt_changed = self._connection.execute(
                """
                UPDATE test_attempts
                SET status = 'completed', result_json = ?, error_message = NULL,
                    analysis_started_at = NULL, analysis_lease_id = NULL,
                    completed_at = ?, updated_at = ?
                WHERE id = ? AND status = 'analyzing' AND analysis_lease_id = ?
                """,
                (result_json, now, now, attempt_id, lease_id),
            ).rowcount
            if run_changed != 1 or attempt_changed != 1:
                raise RuntimeError("analysis lease changed during completion transaction")
            self._connection.execute(
                "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (now, attempt["test_id"], attempt["user_id"]),
            )
        return True

    def fail_analysis(
        self, attempt_id: str, lease_id: str | None, safe_error: object
    ) -> bool:
        if not lease_id:
            return False
        error_message = _safe_error(safe_error)
        now = self._now_text()
        with self._transaction():
            attempt = self._connection.execute(
                """
                SELECT test_id, user_id FROM test_attempts
                WHERE id = ? AND status = 'analyzing' AND analysis_lease_id = ?
                """,
                (attempt_id, lease_id),
            ).fetchone()
            run = self._connection.execute(
                """
                SELECT id FROM test_analysis_runs
                WHERE attempt_id = ? AND lease_id = ? AND status = 'running'
                """,
                (attempt_id, lease_id),
            ).fetchone()
            if attempt is None or run is None:
                return False
            run_changed = self._connection.execute(
                """
                UPDATE test_analysis_runs
                SET status = 'failed', finished_at = ?, error_message = ?
                WHERE id = ? AND status = 'running' AND lease_id = ?
                """,
                (now, error_message, run["id"], lease_id),
            ).rowcount
            attempt_changed = self._connection.execute(
                """
                UPDATE test_attempts
                SET status = 'failed', error_message = ?,
                    analysis_started_at = NULL, analysis_lease_id = NULL, updated_at = ?
                WHERE id = ? AND status = 'analyzing' AND analysis_lease_id = ?
                """,
                (error_message, now, attempt_id, lease_id),
            ).rowcount
            if run_changed != 1 or attempt_changed != 1:
                raise RuntimeError("analysis lease changed during failure transaction")
            self._connection.execute(
                "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (now, attempt["test_id"], attempt["user_id"]),
            )
        return True

    def recover_stale_analyses(
        self,
        now: datetime | None = None,
        attempt_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        cutoff = (self._now(now) - ANALYSIS_LEASE_DURATION).isoformat()
        current = self._now_text(now)
        clauses = ["status = 'analyzing'", "analysis_started_at <= ?"]
        args: list[object] = [cutoff]
        if attempt_id is not None:
            clauses.append("id = ?")
            args.append(attempt_id)
        if user_id is not None:
            clauses.append("user_id = ?")
            args.append(user_id)
        recovered = 0
        with self._transaction():
            rows = self._connection.execute(
                f"""
                SELECT id, test_id, user_id, analysis_lease_id
                FROM test_attempts WHERE {' AND '.join(clauses)}
                """,
                args,
            ).fetchall()
            for row in rows:
                changed = self._connection.execute(
                    """
                    UPDATE test_attempts
                    SET status = 'failed', error_message = 'Analysis timed out.',
                        analysis_started_at = NULL, analysis_lease_id = NULL, updated_at = ?
                    WHERE id = ? AND user_id = ? AND status = 'analyzing'
                        AND analysis_lease_id = ? AND analysis_started_at <= ?
                    """,
                    (
                        current,
                        row["id"],
                        row["user_id"],
                        row["analysis_lease_id"],
                        cutoff,
                    ),
                ).rowcount
                if changed != 1:
                    continue
                self._connection.execute(
                    """
                    UPDATE test_analysis_runs
                    SET status = 'abandoned', finished_at = ?, error_message = 'Analysis timed out.'
                    WHERE attempt_id = ? AND lease_id = ? AND status = 'running'
                    """,
                    (current, row["id"], row["analysis_lease_id"]),
                )
                self._connection.execute(
                    "UPDATE test_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                    (current, row["test_id"], row["user_id"]),
                )
                recovered += 1
        return recovered
