from __future__ import annotations

import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

from AgentBI.src.repositories.sqlite_test_repository import (
    SqliteTestRepository,
    TestAttemptConflictError,
    TestSessionConflictError,
)
from AgentBI.src.schemas.test_schema import (
    AnswerSelection,
    KnowledgeQuestionnaire,
    ModelSnapshot,
    TestPreferencesUpdateRequest,
)


class SqliteTestRepositoryBasicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp_dir.name) / "agentbi.sqlite3")
        self.now = datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)
        self.repository = SqliteTestRepository(self.path, clock=lambda: self.now)

    def tearDown(self) -> None:
        self.repository.close()
        self.temp_dir.cleanup()

    @staticmethod
    def questionnaire(*, title: str = "Python basics") -> KnowledgeQuestionnaire:
        return KnowledgeQuestionnaire.model_validate(
            {
                "mode": "knowledge",
                "title": title,
                "description": "Five small questions.",
                "questions": [
                    {
                        "id": f"q{index}",
                        "prompt": f"Question {index}?",
                        "options": [
                            {"id": "a", "text": "A"},
                            {"id": "b", "text": "B"},
                        ],
                        "correct_option_id": "a",
                        "explanation": "A is correct.",
                        "knowledge_points": ["basics"],
                    }
                    for index in range(1, 6)
                ],
            }
        )

    def preferences(self) -> TestPreferencesUpdateRequest:
        return TestPreferencesUpdateRequest(
            user_id="ignored-by-repository",
            generation_provider_id="generation-provider",
            generation_model="generation-model",
            analysis_provider_id="analysis-provider",
            analysis_model="analysis-model",
        )

    def generated_bundle(self, *, title: str = "Python basics", mode: str = "knowledge") -> dict[str, object]:
        questionnaire = self.questionnaire(title=title)
        return {
            "mode": mode,
            "topic": title,
            "requirements": "Keep it concise.",
            "title": title,
            "description": "Five small questions.",
            "question_count": 5,
            "difficulty": "intermediate" if mode == "knowledge" else None,
            "questionnaire": questionnaire,
            "generation_provider_id": "generation-provider",
            "generation_model": "generation-model",
            "generation_snapshot": ModelSnapshot(
                provider_id="generation-provider",
                provider_name="Generation Provider",
                model="generation-model",
                captured_at=self.now,
            ),
        }

    def create_session(self, request_id: str, *, user_id: str = "alice", title: str | None = None) -> dict[str, object]:
        reservation = self.repository.reserve_generation(user_id, request_id)
        self.assertTrue(reservation.acquired)
        self.assertTrue(
            self.repository.complete_generation(
                user_id,
                request_id,
                reservation.lease_id,
                self.generated_bundle(title=title or request_id),
            )
        )
        status = self.repository.get_generation_status(user_id, request_id)
        session = self.repository.get_session(status.test_id, user_id)
        self.assertIsNotNone(session)
        return session

    @staticmethod
    def answers(selected_option_id: str = "a") -> list[AnswerSelection]:
        return [
            AnswerSelection(question_id=f"q{index}", selected_option_id=selected_option_id)
            for index in range(1, 6)
        ]

    def model_snapshot(self, *, model: str = "analysis-model") -> ModelSnapshot:
        return ModelSnapshot(
            provider_id="analysis-provider",
            provider_name="Analysis Provider",
            model=model,
            captured_at=self.now,
        )

    @staticmethod
    def knowledge_score() -> dict[str, object]:
        return {
            "correct_count": 5,
            "question_count": 5,
            "score": 100.0,
            "max_score": 100.0,
            "knowledge_points": [
                {"label": "basics", "correct": 5, "total": 5, "percentage": 100.0}
            ],
        }

    @staticmethod
    def result() -> dict[str, object]:
        return {"analysis": {"title": "Excellent", "summary": "All correct."}}

    def test_schema_has_exact_test_tables_and_required_pragmas(self) -> None:
        connection = sqlite3.connect(self.path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_%'"
                )
            }
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(
            tables,
            {
                "test_preferences",
                "test_sessions",
                "test_attempts",
                "test_answers",
                "test_analysis_runs",
                "test_creation_requests",
            },
        )
        self.assertEqual(self.repository._connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.repository._connection.execute("PRAGMA synchronous").fetchone()[0], 1)
        self.assertEqual(journal_mode.lower(), "wal")

    def test_schema_is_idempotent_and_records_survive_reopen(self) -> None:
        self.repository.save_preferences("alice", self.preferences())
        self.repository.close()

        self.repository = SqliteTestRepository(self.path, clock=lambda: self.now)
        self.repository.ensure_schema()

        self.assertEqual(
            self.repository.get_preferences("alice")["generation_model"],
            "generation-model",
        )

    def test_preferences_and_sessions_are_scoped_by_user(self) -> None:
        self.repository.save_preferences("alice", self.preferences())
        session = self.create_session("request-1")

        self.assertIsNone(self.repository.get_preferences("bob"))
        self.assertIsNone(self.repository.get_session(session["id"], "bob"))
        self.assertEqual(self.repository.list_sessions("bob").items, [])
        self.assertFalse(self.repository.delete_session(session["id"], "bob"))
        self.assertIsNotNone(self.repository.get_session(session["id"], "alice"))

    def test_save_preferences_updates_generation_and_analysis_routes_independently(self) -> None:
        self.repository.save_preferences("alice", self.preferences())
        self.repository.save_preferences("alice", {"generation_model": "generation-v2"})

        stored = self.repository.get_preferences("alice")

        self.assertEqual(stored["generation_model"], "generation-v2")
        self.assertEqual(stored["analysis_model"], "analysis-model")

    def test_typed_partial_preferences_do_not_clear_the_other_route(self) -> None:
        self.repository.save_preferences("alice", self.preferences())

        self.repository.save_preferences(
            "alice",
            TestPreferencesUpdateRequest(user_id="ignored", analysis_model="analysis-v2"),
        )

        stored = self.repository.get_preferences("alice")
        self.assertEqual(stored["generation_provider_id"], "generation-provider")
        self.assertEqual(stored["generation_model"], "generation-model")
        self.assertEqual(stored["analysis_provider_id"], "analysis-provider")
        self.assertEqual(stored["analysis_model"], "analysis-v2")

    def test_session_json_fields_are_decoded_and_attempts_are_included(self) -> None:
        session = self.create_session("request-json")

        self.assertIsInstance(session["questionnaire"], dict)
        self.assertIsInstance(session["generation_snapshot"], dict)
        self.assertNotIn("questionnaire_json", session)
        self.assertNotIn("generation_snapshot_json", session)
        self.assertEqual(session["attempts"][0]["status"], "draft")

    def test_list_uses_stable_updated_at_and_id_cursor(self) -> None:
        first = self.create_session("a")
        second = self.create_session("b")

        page = self.repository.list_sessions("alice", limit=1)
        next_page = self.repository.list_sessions("alice", cursor=page.next_cursor, limit=1)

        self.assertEqual(page.items[0]["id"], max(first["id"], second["id"]))
        self.assertEqual(len(next_page.items), 1)
        self.assertNotEqual(page.items[0]["id"], next_page.items[0]["id"])
        self.assertIsNone(next_page.next_cursor)

    def test_mode_filter_only_returns_selected_mode(self) -> None:
        knowledge = self.create_session("knowledge")
        fun_bundle = self.generated_bundle(title="Fun", mode="fun")
        fun_bundle["questionnaire"] = {
            **self.questionnaire(title="Fun").model_dump(mode="json"),
            "mode": "fun",
        }
        reservation = self.repository.reserve_generation("alice", "fun")
        self.assertTrue(
            self.repository.complete_generation("alice", "fun", reservation.lease_id, fun_bundle)
        )

        page = self.repository.list_sessions("alice", mode="fun")

        self.assertEqual([item["mode"] for item in page.items], ["fun"])
        self.assertNotEqual(page.items[0]["id"], knowledge["id"])

    def test_create_or_resume_attempt_is_request_idempotent_and_reuses_active_attempt(self) -> None:
        session = self.create_session("base")
        original = session["attempts"][0]

        same_request = self.repository.create_or_resume_attempt(session["id"], "alice", "attempt-1")
        different_request = self.repository.create_or_resume_attempt(session["id"], "alice", "attempt-2")

        self.assertEqual(same_request["id"], original["id"])
        self.assertEqual(different_request["id"], original["id"])

    def test_attempt_lookup_answers_and_delete_are_user_scoped_with_cascades(self) -> None:
        session = self.create_session("answers")
        attempt_id = session["attempts"][0]["id"]
        answers = [AnswerSelection(question_id="q1", selected_option_id="b")]

        saved = self.repository.save_answers(attempt_id, "alice", answers)

        self.assertEqual(saved["answers"], [{"question_id": "q1", "selected_option_id": "b"}])
        self.assertIsNone(self.repository.get_attempt(attempt_id, "bob"))
        self.assertFalse(self.repository.delete_session(session["id"], "bob"))
        self.assertTrue(self.repository.delete_session(session["id"], "alice"))
        connection = sqlite3.connect(self.path)
        try:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM test_answers WHERE attempt_id = ?", (attempt_id,)
                ).fetchone()[0],
                0,
            )
        finally:
            connection.close()

    def test_duplicate_generation_request_does_not_acquire_second_lease(self) -> None:
        first = self.repository.reserve_generation("alice", "request-1")
        duplicate = self.repository.reserve_generation("alice", "request-1")

        self.assertTrue(first.acquired)
        self.assertEqual((duplicate.acquired, duplicate.state), (False, "in_progress"))

    def test_failed_generation_only_reacquires_with_explicit_retry(self) -> None:
        first = self.repository.reserve_generation("alice", "request-1")
        self.assertTrue(
            self.repository.fail_generation("alice", "request-1", first.lease_id, " safe failure ")
        )

        failed = self.repository.reserve_generation("alice", "request-1")
        retry = self.repository.reserve_generation("alice", "request-1", retry_failed=True)

        self.assertEqual((failed.acquired, failed.state), (False, "failed"))
        self.assertEqual(failed.error_message, "safe failure")
        self.assertEqual((retry.acquired, retry.state), (True, "acquired"))

    def test_generation_completion_requires_current_lease(self) -> None:
        old = self.repository.reserve_generation("alice", "request-1")
        self.repository.recover_stale_generations(self.now + timedelta(minutes=11))
        replacement = self.repository.reserve_generation("alice", "request-1", retry_failed=True)

        self.assertFalse(
            self.repository.complete_generation(
                "alice", "request-1", old.lease_id, self.generated_bundle()
            )
        )
        self.assertIsNone(self.repository.get_generation_status("alice", "request-1").test_id)
        self.assertTrue(
            self.repository.complete_generation(
                "alice", "request-1", replacement.lease_id, self.generated_bundle()
            )
        )

    def test_generation_recovery_can_target_one_request_or_sweep_all(self) -> None:
        self.repository.reserve_generation("alice", "one")
        self.repository.reserve_generation("alice", "two")
        future = self.now + timedelta(minutes=11)

        self.assertEqual(
            self.repository.recover_stale_generations(future, request_id="one", user_id="alice"),
            1,
        )
        self.assertEqual(self.repository.get_generation_status("alice", "one").state, "failed")
        self.assertEqual(self.repository.get_generation_status("alice", "two").state, "in_progress")
        self.assertEqual(self.repository.recover_stale_generations(future), 1)

    def test_generation_error_is_normalized_and_capped(self) -> None:
        lease = self.repository.reserve_generation("alice", "request-error")
        self.repository.fail_generation(
            "alice", "request-error", lease.lease_id, "secret\n" + "x" * 900
        )

        error = self.repository.get_generation_status("alice", "request-error").error_message

        self.assertEqual(len(error), 500)
        self.assertNotIn("\n", error)

    def test_unknown_and_cross_user_generation_status_are_indistinguishable(self) -> None:
        self.repository.reserve_generation("alice", "private-request")

        self.assertIsNone(self.repository.get_generation_status("bob", "private-request"))
        self.assertIsNone(self.repository.get_generation_status("bob", "unknown-request"))

    def test_model_snapshots_drop_api_keys_and_unapproved_fields(self) -> None:
        bundle = self.generated_bundle(title="Safe snapshot")
        bundle["generation_snapshot"] = {
            **bundle["generation_snapshot"].model_dump(mode="json"),
            "api_key": "generation-secret",
            "raw_response": "raw",
        }
        generation = self.repository.reserve_generation("alice", "safe-snapshot")
        self.repository.complete_generation(
            "alice", "safe-snapshot", generation.lease_id, bundle
        )
        session = self.repository.get_session(
            self.repository.get_generation_status("alice", "safe-snapshot").test_id,
            "alice",
        )
        attempt_id = session["attempts"][0]["id"]
        analysis_snapshot = {
            **self.model_snapshot().model_dump(mode="json"),
            "api_key": "analysis-secret",
            "validation_payload": {"private": True},
        }

        self.repository.begin_analysis(
            attempt_id,
            "alice",
            "safe-analysis",
            self.answers(),
            analysis_snapshot,
            self.knowledge_score(),
        )
        attempt = self.repository.get_attempt(attempt_id, "alice")

        self.assertEqual(
            set(session["generation_snapshot"]),
            {"provider_id", "provider_name", "model", "temperature", "captured_at"},
        )
        self.assertEqual(
            set(attempt["analysis_snapshot"]),
            {"provider_id", "provider_name", "model", "temperature", "captured_at"},
        )

    def test_autosave_rejects_unknown_questions_and_options(self) -> None:
        session = self.create_session("invalid-autosave")
        attempt_id = session["attempts"][0]["id"]

        with self.assertRaises(ValueError):
            self.repository.save_answers(
                attempt_id,
                "alice",
                [AnswerSelection(question_id="unknown", selected_option_id="a")],
            )
        with self.assertRaises(ValueError):
            self.repository.save_answers(
                attempt_id,
                "alice",
                [AnswerSelection(question_id="q1", selected_option_id="unknown")],
            )

    def test_concurrent_generation_reservation_has_one_winner(self) -> None:
        peer = SqliteTestRepository(self.path, clock=lambda: self.now)
        barrier = Barrier(2)

        def reserve(repository: SqliteTestRepository) -> bool:
            barrier.wait()
            return repository.reserve_generation("alice", "raced").acquired

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(reserve, (self.repository, peer)))
        finally:
            peer.close()

        self.assertEqual(sorted(outcomes), [False, True])

    def test_same_attempt_request_id_is_idempotent_after_prior_attempt_completed(self) -> None:
        session = self.create_session("base")
        original_id = session["attempts"][0]["id"]
        analysis = self.repository.begin_analysis(
            original_id,
            "alice",
            "submit-original",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )
        self.assertTrue(self.repository.complete_analysis(original_id, analysis.lease_id, self.result()))

        first = self.repository.create_or_resume_attempt(session["id"], "alice", "retry-attempt")
        duplicate = self.repository.create_or_resume_attempt(session["id"], "alice", "retry-attempt")

        self.assertNotEqual(first["id"], original_id)
        self.assertEqual(duplicate["id"], first["id"])

    def test_cross_test_attempt_request_replay_raises_typed_conflict(self) -> None:
        first = self.create_session("first-test")
        second = self.create_session("second-test")
        for session, submit_request in (
            (first, "submit-first"),
            (second, "submit-second"),
        ):
            attempt_id = session["attempts"][0]["id"]
            reservation = self.repository.begin_analysis(
                attempt_id,
                "alice",
                submit_request,
                self.answers(),
                self.model_snapshot(),
                self.knowledge_score(),
            )
            self.assertTrue(
                self.repository.complete_analysis(
                    attempt_id, reservation.lease_id, self.result()
                )
            )

        with self.assertRaises(TestAttemptConflictError):
            self.repository.create_or_resume_attempt(
                second["id"], "alice", "first-test"
            )

    def test_partial_unique_index_rejects_second_active_attempt(self) -> None:
        session = self.create_session("active-index")
        now = self.now.isoformat()

        with self.assertRaises(sqlite3.IntegrityError), self.repository._connection:
            self.repository._connection.execute(
                """
                INSERT INTO test_attempts(
                    id, test_id, user_id, status, create_request_id, started_at, updated_at
                ) VALUES ('second-active', ?, 'alice', 'draft', 'second-active', ?, ?)
                """,
                (session["id"], now, now),
            )

    def test_same_analysis_request_is_idempotent(self) -> None:
        session = self.create_session("analysis-idempotency")
        attempt_id = session["attempts"][0]["id"]

        first = self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-1",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )
        duplicate = self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-1",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )

        self.assertTrue(first.acquired)
        self.assertEqual((duplicate.acquired, duplicate.state), (False, "in_progress"))

    def test_same_analysis_request_id_is_independent_across_users(self) -> None:
        alice = self.create_session("alice-test", user_id="alice")
        bob = self.create_session("bob-test", user_id="bob")

        alice_reservation = self.repository.begin_analysis(
            alice["attempts"][0]["id"],
            "alice",
            "shared-submit-id",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )
        bob_reservation = self.repository.begin_analysis(
            bob["attempts"][0]["id"],
            "bob",
            "shared-submit-id",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )

        self.assertTrue(alice_reservation.acquired)
        self.assertTrue(bob_reservation.acquired)
        self.assertNotEqual(alice_reservation.lease_id, bob_reservation.lease_id)

    def test_late_analysis_success_and_failure_cannot_replace_new_run(self) -> None:
        session = self.create_session("late-analysis")
        attempt_id = session["attempts"][0]["id"]
        old = self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-1",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )
        self.repository.recover_stale_analyses(
            self.now + timedelta(minutes=11), attempt_id=attempt_id, user_id="alice"
        )
        new = self.repository.begin_analysis(
            attempt_id,
            "alice",
            "retry-1",
            self.answers(),
            self.model_snapshot(model="analysis-v2"),
            self.knowledge_score(),
        )

        self.assertFalse(self.repository.complete_analysis(attempt_id, old.lease_id, self.result()))
        self.assertFalse(self.repository.fail_analysis(attempt_id, old.lease_id, "late failure"))
        self.assertTrue(self.repository.complete_analysis(attempt_id, new.lease_id, self.result()))
        stored = self.repository.get_attempt(attempt_id, "alice")
        self.assertEqual(stored["status"], "completed")
        self.assertEqual(stored["analysis_model"], "analysis-v2")

    def test_analysis_failure_caps_error_and_preserves_deterministic_score(self) -> None:
        session = self.create_session("analysis-error")
        attempt_id = session["attempts"][0]["id"]
        lease = self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-error",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )

        self.assertTrue(
            self.repository.fail_analysis(
                attempt_id, lease.lease_id, "upstream\n" + "x" * 900
            )
        )
        stored = self.repository.get_attempt(attempt_id, "alice")

        self.assertEqual(len(stored["error_message"]), 500)
        self.assertNotIn("\n", stored["error_message"])
        self.assertEqual(
            (stored["score"], stored["max_score"], stored["correct_count"]),
            (100.0, 100.0, 5),
        )

    def test_submit_final_snapshot_replaces_autosave_and_blocks_late_autosave(self) -> None:
        session = self.create_session("final-snapshot")
        attempt_id = session["attempts"][0]["id"]
        self.repository.save_answers(
            attempt_id,
            "alice",
            [AnswerSelection(question_id="q1", selected_option_id="b")],
        )

        self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-1",
            self.answers("a"),
            self.model_snapshot(),
            self.knowledge_score(),
        )

        stored = self.repository.get_attempt(attempt_id, "alice")
        self.assertEqual({item["selected_option_id"] for item in stored["answers"]}, {"a"})
        with self.assertRaises(TestAttemptConflictError):
            self.repository.save_answers(
                attempt_id,
                "alice",
                [AnswerSelection(question_id="q1", selected_option_id="b")],
            )

    def test_completed_knowledge_scores_persist_and_fun_scores_stay_null(self) -> None:
        knowledge = self.create_session("knowledge-score")
        knowledge_attempt = knowledge["attempts"][0]["id"]
        lease = self.repository.begin_analysis(
            knowledge_attempt,
            "alice",
            "submit-knowledge",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )
        self.repository.complete_analysis(knowledge_attempt, lease.lease_id, self.result())

        fun_bundle = self.generated_bundle(title="Fun", mode="fun")
        fun_bundle["questionnaire"] = {
            **self.questionnaire(title="Fun").model_dump(mode="json"),
            "mode": "fun",
        }
        reservation = self.repository.reserve_generation("alice", "fun-score")
        self.repository.complete_generation("alice", "fun-score", reservation.lease_id, fun_bundle)
        fun_session = self.repository.get_session(
            self.repository.get_generation_status("alice", "fun-score").test_id, "alice"
        )
        fun_attempt = fun_session["attempts"][0]["id"]
        fun_lease = self.repository.begin_analysis(
            fun_attempt,
            "alice",
            "submit-fun",
            self.answers(),
            self.model_snapshot(),
        )
        self.repository.complete_analysis(fun_attempt, fun_lease.lease_id, self.result())

        stored_knowledge = self.repository.get_attempt(knowledge_attempt, "alice")
        stored_fun = self.repository.get_attempt(fun_attempt, "alice")
        self.assertEqual(
            (stored_knowledge["score"], stored_knowledge["max_score"], stored_knowledge["correct_count"]),
            (100.0, 100.0, 5),
        )
        self.assertEqual(
            (stored_fun["score"], stored_fun["max_score"], stored_fun["correct_count"]),
            (None, None, None),
        )

    def test_active_analysis_blocks_delete_but_recovered_session_cascades(self) -> None:
        session = self.create_session("delete-analysis")
        attempt_id = session["attempts"][0]["id"]
        self.repository.begin_analysis(
            attempt_id,
            "alice",
            "submit-delete",
            self.answers(),
            self.model_snapshot(),
            self.knowledge_score(),
        )

        with self.assertRaises(TestSessionConflictError):
            self.repository.delete_session(session["id"], "alice")
        self.repository.recover_stale_analyses(self.now + timedelta(minutes=11))
        self.assertTrue(self.repository.delete_session(session["id"], "alice"))
        self.assertIsNone(self.repository.get_attempt(attempt_id, "alice"))

    def test_analysis_recovery_can_target_one_attempt_or_sweep_all(self) -> None:
        first = self.create_session("analysis-one")
        second = self.create_session("analysis-two")
        first_id = first["attempts"][0]["id"]
        second_id = second["attempts"][0]["id"]
        for attempt_id, request_id in ((first_id, "submit-one"), (second_id, "submit-two")):
            self.repository.begin_analysis(
                attempt_id,
                "alice",
                request_id,
                self.answers(),
                self.model_snapshot(),
                self.knowledge_score(),
            )
        future = self.now + timedelta(minutes=11)

        self.assertEqual(
            self.repository.recover_stale_analyses(
                future, attempt_id=first_id, user_id="alice"
            ),
            1,
        )
        self.assertEqual(self.repository.get_attempt(first_id, "alice")["status"], "failed")
        self.assertEqual(self.repository.get_attempt(second_id, "alice")["status"], "analyzing")
        self.assertEqual(self.repository.recover_stale_analyses(future), 1)


if __name__ == "__main__":
    unittest.main()
