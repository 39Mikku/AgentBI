from __future__ import annotations

from typing import Any

from AgentBI.src.repositories.sqlite_test_repository import (
    SqliteTestRepository,
    TestAttemptConflictError,
    TestSessionConflictError,
)
from AgentBI.src.schemas.test_schema import (
    AnswerSelection,
    CompletedFunResult,
    CompletedKnowledgeQuestion,
    CompletedKnowledgeResult,
    CreateAttemptRequest,
    CreateTestRequest,
    FunAnalysisInput,
    FunQuestionnaire,
    KnowledgeAnalysisInput,
    KnowledgeQuestionnaire,
    RetryAnalysisRequest,
    SaveAnswersRequest,
    SubmitAttemptRequest,
    TestMode,
    TestPreferencesUpdateRequest,
    to_public_questionnaire,
)
from AgentBI.src.services.test_model_service import TestModelService
from AgentBI.src.services.test_scoring import score_knowledge_test


class TestServiceError(RuntimeError):
    pass


class TestNotFoundError(TestServiceError):
    pass


class TestConflictError(TestServiceError):
    pass


def _private_questionnaire(document: dict[str, Any]):
    model = KnowledgeQuestionnaire if document["mode"] == TestMode.KNOWLEDGE.value else FunQuestionnaire
    return model.model_validate(document["questionnaire"])


class TestService:
    def __init__(
        self,
        repository: SqliteTestRepository,
        chat_repository: Any,
        model_service: TestModelService,
    ):
        self.repository = repository
        self.chat_repository = chat_repository
        self.model_service = model_service

    @staticmethod
    def _preferences(document: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": document["user_id"],
            "generation_provider_id": document.get("generation_provider_id"),
            "generation_model": document.get("generation_model"),
            "analysis_provider_id": document.get("analysis_provider_id"),
            "analysis_model": document.get("analysis_model"),
        }

    def get_or_initialize_preferences(self, user_id: str) -> dict[str, Any]:
        stored = self.repository.get_preferences(user_id)
        if stored is not None:
            return self._preferences(stored)
        studio = self.chat_repository.get_preferences(user_id)
        stored = self.repository.save_preferences(
            user_id,
            {
                "generation_provider_id": studio.get("provider_id"),
                "generation_model": studio.get("model"),
                "analysis_provider_id": studio.get("provider_id"),
                "analysis_model": studio.get("model"),
            },
        )
        return self._preferences(stored)

    def update_preferences(self, request: TestPreferencesUpdateRequest) -> dict[str, Any]:
        self.get_or_initialize_preferences(request.user_id)
        return self._preferences(self.repository.save_preferences(request.user_id, request))

    @staticmethod
    def _summary(document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": document["id"],
            "title": document["title"],
            "description": document.get("description", ""),
            "mode": document["mode"],
            "question_count": document["question_count"],
            "updated_at": document["updated_at"],
        }

    def _session_detail(self, document: dict[str, Any]) -> dict[str, Any]:
        questionnaire = _private_questionnaire(document)
        payload = self._summary(document)
        payload["questionnaire"] = to_public_questionnaire(questionnaire).model_dump(mode="json")
        payload["attempts"] = [
            {
                "id": attempt["id"],
                "status": attempt["status"],
                "created_at": attempt["started_at"],
                "updated_at": attempt["updated_at"],
                "score": attempt.get("score"),
            }
            for attempt in document.get("attempts", [])
        ]
        return payload

    def _attempt_detail(self, document: dict[str, Any]) -> dict[str, Any]:
        questionnaire = _private_questionnaire(document)
        public = to_public_questionnaire(questionnaire).model_dump(mode="json")
        payload: dict[str, Any] = {
            "id": document["id"],
            "status": document["status"],
            "questionnaire": public,
            "answers": document.get("answers", []),
        }
        if document["status"] == "failed":
            payload["error_message"] = document.get("error_message") or "分析失败"
        elif document["status"] == "completed":
            payload["mode"] = document["mode"]
            payload["result"] = document["result"]
        return payload

    async def create_test(self, request: CreateTestRequest) -> dict[str, Any]:
        self.get_or_initialize_preferences(request.user_id)
        reservation = self.repository.reserve_generation(
            request.user_id, str(request.request_id), request.retry_failed
        )
        if not reservation.acquired:
            if reservation.state == "completed":
                session = self.repository.get_session(reservation.test_id, request.user_id)
                if session is None:
                    raise TestNotFoundError("测试不存在")
                return {"state": "completed", "created": False, "session": self._session_detail(session)}
            return {
                "state": "generating" if reservation.state == "in_progress" else "failed",
                "request_id": str(request.request_id),
                "test_id": reservation.test_id,
                "error_message": reservation.error_message,
            }
        try:
            questionnaire, snapshot = await self.model_service.generate_questionnaire(
                request.user_id, request
            )
            bundle = {
                "mode": request.mode.value,
                "topic": request.topic,
                "requirements": request.requirements,
                "title": questionnaire.title,
                "description": questionnaire.description,
                "question_count": request.question_count,
                "difficulty": request.difficulty.value if request.difficulty else None,
                "questionnaire": questionnaire,
                "generation_provider_id": snapshot.provider_id,
                "generation_model": snapshot.model,
                "generation_snapshot": snapshot,
            }
            if not self.repository.complete_generation(
                request.user_id, str(request.request_id), reservation.lease_id, bundle
            ):
                return {"state": "generating", "request_id": str(request.request_id)}
            status = self.repository.get_generation_status(request.user_id, str(request.request_id))
            session = self.repository.get_session(status.test_id if status else None, request.user_id)
            if session is None:
                raise TestNotFoundError("测试生成结果不存在")
            return {"state": "completed", "created": True, "session": self._session_detail(session)}
        except Exception as exc:
            self.repository.fail_generation(
                request.user_id, str(request.request_id), reservation.lease_id, str(exc)
            )
            raise

    def get_generation_status(self, user_id: str, request_id: str) -> dict[str, Any]:
        reservation = self.repository.get_generation_status(user_id, request_id)
        if reservation is None:
            raise TestNotFoundError("生成请求不存在")
        state = {"in_progress": "generating", "completed": "completed", "failed": "failed"}[reservation.state]
        return {
            "state": state,
            "request_id": request_id,
            "test_id": reservation.test_id,
            "error_message": reservation.error_message,
            "retry_after_ms": 1000,
        }

    def list_tests(self, user_id: str, mode: str | None, cursor: str | None, limit: int) -> dict[str, Any]:
        page = self.repository.list_sessions(user_id, mode=mode, cursor=cursor, limit=limit)
        return {"items": [self._summary(item) for item in page.items], "next_cursor": page.next_cursor}

    def get_test(self, test_id: str, user_id: str) -> dict[str, Any]:
        document = self.repository.get_session(test_id, user_id)
        if document is None:
            raise TestNotFoundError("测试不存在")
        return self._session_detail(document)

    def delete_test(self, test_id: str, user_id: str) -> None:
        try:
            deleted = self.repository.delete_session(test_id, user_id)
        except TestSessionConflictError as exc:
            raise TestConflictError(str(exc)) from exc
        if not deleted:
            raise TestNotFoundError("测试不存在")

    def create_or_resume_attempt(self, test_id: str, request: CreateAttemptRequest) -> dict[str, Any]:
        try:
            document = self.repository.create_or_resume_attempt(
                test_id, request.user_id, str(request.request_id)
            )
        except TestAttemptConflictError as exc:
            raise TestConflictError(str(exc)) from exc
        if document is None:
            raise TestNotFoundError("测试不存在")
        return self._attempt_detail(document)

    def get_attempt(self, attempt_id: str, user_id: str) -> dict[str, Any]:
        document = self.repository.get_attempt(attempt_id, user_id)
        if document is None:
            raise TestNotFoundError("作答记录不存在")
        return self._attempt_detail(document)

    def save_answers(self, attempt_id: str, request: SaveAnswersRequest) -> dict[str, Any]:
        try:
            document = self.repository.save_answers(attempt_id, request.user_id, request.answers)
        except KeyError as exc:
            raise TestNotFoundError("作答记录不存在") from exc
        except TestAttemptConflictError as exc:
            raise TestConflictError(str(exc)) from exc
        return self._attempt_detail(document)

    async def _analyze(
        self,
        attempt_id: str,
        user_id: str,
        request_id: str,
        answers: list[AnswerSelection],
    ) -> dict[str, Any]:
        current = self.repository.get_attempt(attempt_id, user_id)
        if current is None:
            raise TestNotFoundError("作答记录不存在")
        questionnaire = _private_questionnaire(current)
        route = self.model_service.prepare_analysis_route(user_id)
        answer_map = {item.question_id: item.selected_option_id for item in answers}
        score = score_knowledge_test(questionnaire, answer_map) if isinstance(questionnaire, KnowledgeQuestionnaire) else None
        try:
            reservation = self.repository.begin_analysis(
                attempt_id, user_id, request_id, answers, route.snapshot, score
            )
        except KeyError as exc:
            raise TestNotFoundError("作答记录不存在") from exc
        except (TestAttemptConflictError, ValueError) as exc:
            raise TestConflictError(str(exc)) from exc
        if not reservation.acquired:
            return self._attempt_detail(reservation.attempt)
        try:
            if isinstance(questionnaire, KnowledgeQuestionnaire):
                analysis, _ = await self.model_service.analyze_knowledge(
                    user_id,
                    KnowledgeAnalysisInput(questionnaire=questionnaire, answers=answers, score=score),
                    prepared_route=route,
                )
                result = CompletedKnowledgeResult(
                    questions=[
                        CompletedKnowledgeQuestion(
                            **question.model_dump(),
                            selected_option_id=answer_map[question.id],
                            is_correct=answer_map[question.id] == question.correct_option_id,
                        )
                        for question in questionnaire.questions
                    ],
                    correct_count=score.correct_count,
                    question_count=score.question_count,
                    score=score.score,
                    max_score=score.max_score,
                    knowledge_points=score.knowledge_points,
                    analysis=analysis,
                )
            else:
                analysis, _ = await self.model_service.analyze_fun(
                    user_id,
                    FunAnalysisInput(questionnaire=questionnaire, answers=answers),
                    prepared_route=route,
                )
                result = CompletedFunResult(answers=answers, analysis=analysis)
            self.repository.complete_analysis(attempt_id, reservation.lease_id, result)
        except Exception as exc:
            self.repository.fail_analysis(attempt_id, reservation.lease_id, str(exc))
        document = self.repository.get_attempt(attempt_id, user_id)
        if document is None:
            raise TestNotFoundError("作答记录不存在")
        return self._attempt_detail(document)

    async def submit_attempt(self, attempt_id: str, request: SubmitAttemptRequest) -> dict[str, Any]:
        return await self._analyze(
            attempt_id, request.user_id, str(request.request_id), request.answers
        )

    async def retry_analysis(self, attempt_id: str, request: RetryAnalysisRequest) -> dict[str, Any]:
        current = self.repository.get_attempt(attempt_id, request.user_id)
        if current is None:
            raise TestNotFoundError("作答记录不存在")
        if current["status"] != "failed":
            raise TestConflictError("仅失败的分析可以重试")
        answers = [AnswerSelection.model_validate(item) for item in current["answers"]]
        return await self._analyze(attempt_id, request.user_id, str(request.request_id), answers)

    def recover_stale_work(self) -> dict[str, int]:
        return {
            "generations": self.repository.recover_stale_generations(),
            "analyses": self.repository.recover_stale_analyses(),
        }
