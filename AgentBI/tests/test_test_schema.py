import math
import unittest
from uuid import uuid4

from pydantic import ValidationError

from AgentBI.src.schemas.test_schema import (
    AnswerSelection,
    AnalyzingAttemptDetailResponse,
    ChartData,
    CompletedKnowledgeAttemptDetailResponse,
    CompletedKnowledgeQuestion,
    CompletedKnowledgeResult,
    CompletedFunAttemptDetailResponse,
    CompletedFunResult,
    CreateTestRequest,
    DraftAttemptDetailResponse,
    FunAnalysis,
    FunAnalysisInput,
    FunQuestionnaire,
    KnowledgeAnalysis,
    KnowledgeAnalysisInput,
    KnowledgeQuestionnaire,
    SaveAnswersRequest,
    SubmitAttemptRequest,
    FailedAttemptDetailResponse,
    TestDifficulty,
    TestMode,
    KnowledgeScore,
    to_public_questionnaire,
)


class TestTestSchema(unittest.TestCase):
    @staticmethod
    def knowledge_payload(question_count: int = 5) -> dict:
        return {
            "mode": "knowledge",
            "title": "Python basics",
            "description": "A short test",
            "questions": [
                {
                    "id": f"q{index}",
                    "prompt": f"Question {index}?",
                    "options": [
                        {"id": "a", "text": "Option A"},
                        {"id": "b", "text": "Option B"},
                    ],
                    "correct_option_id": "a",
                    "explanation": "A is correct.",
                    "knowledge_points": ["Python"],
                }
                for index in range(1, question_count + 1)
            ],
        }

    @staticmethod
    def fun_payload(question_count: int = 5) -> dict:
        return {
            "mode": "fun",
            "title": "Which editor are you?",
            "description": "Just for fun",
            "questions": [
                {
                    "id": f"q{index}",
                    "prompt": f"Pick {index}",
                    "options": [
                        {"id": "a", "text": "Option A"},
                        {"id": "b", "text": "Option B"},
                    ],
                }
                for index in range(1, question_count + 1)
            ],
        }

    @classmethod
    def completed_knowledge_payload(cls) -> dict:
        questionnaire = cls.knowledge_payload()
        return {
            "questions": [
                {
                    **question,
                    "selected_option_id": "a",
                    "is_correct": True,
                }
                for question in questionnaire["questions"]
            ],
            "correct_count": 5,
            "question_count": 5,
            "score": 100.0,
            "max_score": 100.0,
            "knowledge_points": [
                {
                    "label": "Python",
                    "correct": 5,
                    "total": 5,
                    "percentage": 100.0,
                }
            ],
            "analysis": {
                "title": "Progress",
                "summary": "Excellent",
                "mastered": [{"heading": "Python", "body": "Strong"}],
                "weaknesses": [],
                "recommendations": [],
                "charts": [],
            },
        }

    def test_mode_and_difficulty_values_are_stable(self):
        self.assertEqual([item.value for item in TestMode], ["knowledge", "fun"])
        self.assertEqual(
            [item.value for item in TestDifficulty],
            ["beginner", "intermediate", "advanced"],
        )

    def test_create_request_trims_text_and_defaults_knowledge_difficulty(self):
        request = CreateTestRequest(
            user_id="  user@example.com  ",
            request_id=uuid4(),
            mode="knowledge",
            topic="  Python  ",
            requirements="  focus on syntax  ",
        )
        self.assertEqual(request.user_id, "user@example.com")
        self.assertEqual(request.topic, "Python")
        self.assertEqual(request.requirements, "focus on syntax")
        self.assertEqual(request.question_count, 10)
        self.assertEqual(request.difficulty, TestDifficulty.INTERMEDIATE)

    def test_fun_request_rejects_difficulty(self):
        with self.assertRaises(ValidationError):
            CreateTestRequest(
                user_id="user",
                request_id=uuid4(),
                mode="fun",
                topic="Topic",
                difficulty="beginner",
            )

    def test_questionnaire_accepts_only_exact_supported_counts(self):
        for count in (5, 10, 15, 20):
            KnowledgeQuestionnaire.model_validate(self.knowledge_payload(count))
        for count in (4, 6, 21):
            with self.subTest(count=count), self.assertRaises(ValidationError):
                KnowledgeQuestionnaire.model_validate(self.knowledge_payload(count))

    def test_fun_question_rejects_correct_answer_and_internal_weights(self):
        for field, value in (
            ("correct_option_id", "a"),
            ("internal_tags", ["introvert"]),
            ("weights", {"introvert": 1}),
        ):
            payload = self.fun_payload()
            payload["questions"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                FunQuestionnaire.model_validate(payload)

    def test_knowledge_question_requires_answer_inside_its_options(self):
        payload = self.knowledge_payload()
        payload["questions"][0]["correct_option_id"] = "missing"
        with self.assertRaises(ValidationError):
            KnowledgeQuestionnaire.model_validate(payload)

    def test_knowledge_points_do_not_add_an_undocumented_uniqueness_rule(self):
        payload = self.knowledge_payload()
        payload["questions"][0]["knowledge_points"] = ["Python", "Python"]
        parsed = KnowledgeQuestionnaire.model_validate(payload)
        self.assertEqual(parsed.questions[0].knowledge_points, ["Python", "Python"])

    def test_question_and_option_ids_must_be_unique_and_ascii_safe(self):
        duplicate_questions = self.knowledge_payload()
        duplicate_questions["questions"][1]["id"] = "q1"
        with self.assertRaises(ValidationError):
            KnowledgeQuestionnaire.model_validate(duplicate_questions)

        duplicate_options = self.knowledge_payload()
        duplicate_options["questions"][0]["options"][1]["id"] = "a"
        with self.assertRaises(ValidationError):
            KnowledgeQuestionnaire.model_validate(duplicate_options)

        invalid_id = self.knowledge_payload()
        invalid_id["questions"][0]["id"] = "题目一"
        with self.assertRaises(ValidationError):
            KnowledgeQuestionnaire.model_validate(invalid_id)

    def test_public_questionnaire_drops_private_answer_fields(self):
        public = to_public_questionnaire(
            KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
        )
        dumped = public.model_dump_json()
        self.assertEqual(public.question_count, 5)
        self.assertNotIn("correct_option_id", dumped)
        self.assertNotIn("explanation", dumped)
        self.assertNotIn("knowledge_points", dumped)

    def test_non_completed_attempt_rejects_nested_private_answer_fields(self):
        public = to_public_questionnaire(
            KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
        )
        payload = {
            "id": "attempt-1",
            "status": "draft",
            "questionnaire": public.model_dump(mode="json"),
            "answers": [],
        }
        payload["questionnaire"]["questions"][0]["correct_option_id"] = "a"
        payload["questionnaire"]["questions"][0]["explanation"] = "private"
        with self.assertRaises(ValidationError):
            DraftAttemptDetailResponse.model_validate(payload)

        draft = DraftAttemptDetailResponse(
            id="attempt-1", status="draft", questionnaire=public, answers=[]
        )
        dumped = draft.model_dump_json()
        self.assertNotIn("correct_option_id", dumped)
        self.assertNotIn("explanation", dumped)

    def test_analysis_schemas_reject_score_fields_and_require_sections(self):
        knowledge = {
            "title": "Progress",
            "summary": "Good start",
            "mastered": [{"heading": "Known", "body": "Basics"}],
            "weaknesses": [],
            "recommendations": [],
            "charts": [],
        }
        KnowledgeAnalysis.model_validate(knowledge)
        with self.assertRaises(ValidationError):
            KnowledgeAnalysis.model_validate({**knowledge, "score": 100})

        with self.assertRaises(ValidationError):
            KnowledgeAnalysis.model_validate(
                {
                    **knowledge,
                    "mastered": [],
                    "weaknesses": [],
                    "recommendations": [],
                }
            )

        with self.assertRaises(ValidationError):
            FunAnalysis.model_validate(
                {"title": "Result", "summary": "Summary", "sections": [], "charts": []}
            )

    def test_chart_data_enforces_kind_dimensions_and_finite_bounds(self):
        valid = {
            "kind": "radar",
            "title": "Traits",
            "items": [
                {"label": "Curiosity", "value": 82, "max_value": 100},
                {"label": "Focus", "value": 60, "max_value": 100},
            ],
        }
        ChartData.model_validate(valid)
        zero_scale = {
            **valid,
            "items": [
                {"label": "A", "value": 0, "max_value": 0},
                {"label": "B", "value": 0, "max_value": 0},
            ],
        }
        ChartData.model_validate(zero_scale)
        for mutation in (
            {**valid, "kind": "line"},
            {**valid, "items": valid["items"][:1]},
            {
                **valid,
                "items": [
                    {"label": "Curiosity", "value": 101, "max_value": 100},
                    valid["items"][1],
                ],
            },
            {
                **valid,
                "items": [
                    {"label": "Curiosity", "value": math.inf, "max_value": 100},
                    valid["items"][1],
                ],
            },
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                ChartData.model_validate(mutation)

    def test_knowledge_score_question_count_is_a_positive_integer(self):
        score = KnowledgeScore(
            correct_count=1,
            question_count=2,
            score=50.0,
            max_score=100.0,
            knowledge_points=[],
        )
        self.assertEqual(score.question_count, 2)
        self.assertIsInstance(score.knowledge_points, list)

    def test_completed_knowledge_question_enforces_single_choice_truth(self):
        base = self.completed_knowledge_payload()["questions"][0]
        mutations = []
        duplicate_options = {**base, "options": [base["options"][0], base["options"][0]]}
        mutations.append(duplicate_options)
        mutations.append({**base, "selected_option_id": "missing"})
        mutations.append({**base, "correct_option_id": "missing"})
        mutations.append({**base, "selected_option_id": "b", "is_correct": True})
        for payload in mutations:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                CompletedKnowledgeQuestion.model_validate(payload)

    def test_completed_knowledge_result_rejects_contradictory_aggregates(self):
        base = self.completed_knowledge_payload()
        mutations = []
        duplicate_questions = {**base, "questions": [dict(q) for q in base["questions"]]}
        duplicate_questions["questions"][1]["id"] = "q1"
        mutations.append(duplicate_questions)
        mutations.append({**base, "question_count": 10})
        mutations.append({**base, "correct_count": 4})
        mutations.append({**base, "score": 80.0})
        mutations.append(
            {
                **base,
                "knowledge_points": [
                    *base["knowledge_points"],
                    dict(base["knowledge_points"][0]),
                ],
            }
        )
        mutations.append(
            {
                **base,
                "knowledge_points": [
                    {**base["knowledge_points"][0], "correct": 0, "percentage": 0.0}
                ],
            }
        )
        for payload in mutations:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                CompletedKnowledgeResult.model_validate(payload)

    def test_completed_knowledge_attempt_is_one_coherent_snapshot(self):
        questionnaire = KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
        public = to_public_questionnaire(questionnaire).model_dump(mode="json")
        answers = [
            {"question_id": question.id, "selected_option_id": "a"}
            for question in questionnaire.questions
        ]
        base = {
            "id": "attempt-1",
            "status": "completed",
            "mode": "knowledge",
            "questionnaire": public,
            "answers": answers,
            "result": self.completed_knowledge_payload(),
        }
        CompletedKnowledgeAttemptDetailResponse.model_validate(base)

        fun_questionnaire = {**public, "mode": "fun"}
        mismatched_answers = [dict(answer) for answer in answers]
        mismatched_answers[0]["selected_option_id"] = "b"
        unrelated_result = self.completed_knowledge_payload()
        unrelated_result["questions"] = [dict(q) for q in unrelated_result["questions"]]
        unrelated_result["questions"][0]["prompt"] = "Different prompt"
        for mutation in (
            {**base, "questionnaire": fun_questionnaire},
            {**base, "answers": mismatched_answers},
            {**base, "result": unrelated_result},
            {**base, "answers": []},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                CompletedKnowledgeAttemptDetailResponse.model_validate(mutation)

    def test_knowledge_analysis_input_rejects_forged_score_components(self):
        questionnaire = KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
        answers = [
            {"question_id": question.id, "selected_option_id": "b"}
            for question in questionnaire.questions
        ]
        valid_score = {
            "correct_count": 0,
            "question_count": 5,
            "score": 0.0,
            "max_score": 100.0,
            "knowledge_points": [
                {
                    "label": "Python",
                    "correct": 0,
                    "total": 5,
                    "percentage": 0.0,
                }
            ],
        }
        base = {
            "questionnaire": questionnaire,
            "answers": answers,
            "score": valid_score,
        }
        KnowledgeAnalysisInput.model_validate(base)
        for forged_score in (
            {**valid_score, "correct_count": 5},
            {**valid_score, "score": 100.0},
            {
                **valid_score,
                "knowledge_points": [
                    {
                        "label": "Python",
                        "correct": 5,
                        "total": 5,
                        "percentage": 100.0,
                    }
                ],
            },
        ):
            with self.subTest(forged_score=forged_score), self.assertRaises(
                ValidationError
            ):
                KnowledgeAnalysisInput.model_validate({**base, "score": forged_score})

    def test_submit_attempt_accepts_only_supported_complete_answer_counts(self):
        for count in (6, 7, 19):
            answers = [
                {"question_id": f"q{index}", "selected_option_id": "a"}
                for index in range(1, count + 1)
            ]
            with self.subTest(count=count), self.assertRaises(ValidationError):
                SubmitAttemptRequest(
                    user_id="user", request_id=uuid4(), answers=answers
                )

    def test_non_completed_attempt_states_validate_answer_snapshots(self):
        questionnaire = to_public_questionnaire(
            KnowledgeQuestionnaire.model_validate(self.knowledge_payload())
        )
        complete = [
            {"question_id": question.id, "selected_option_id": "a"}
            for question in questionnaire.questions
        ]
        DraftAttemptDetailResponse(
            id="draft", status="draft", questionnaire=questionnaire, answers=complete[:1]
        )
        AnalyzingAttemptDetailResponse(
            id="analyzing",
            status="analyzing",
            questionnaire=questionnaire,
            answers=complete,
        )
        FailedAttemptDetailResponse(
            id="failed",
            status="failed",
            questionnaire=questionnaire,
            answers=complete,
            error_message="safe failure",
        )

        duplicate = [complete[0], complete[0]]
        foreign = [{"question_id": "foreign", "selected_option_id": "a"}]
        invalid_option = [{"question_id": "q1", "selected_option_id": "missing"}]
        cases = (
            (DraftAttemptDetailResponse, "draft", duplicate, {}),
            (DraftAttemptDetailResponse, "draft", foreign, {}),
            (DraftAttemptDetailResponse, "draft", invalid_option, {}),
            (AnalyzingAttemptDetailResponse, "analyzing", duplicate, {}),
            (AnalyzingAttemptDetailResponse, "analyzing", foreign, {}),
            (AnalyzingAttemptDetailResponse, "analyzing", complete[:1], {}),
            (
                FailedAttemptDetailResponse,
                "failed",
                duplicate,
                {"error_message": "safe failure"},
            ),
            (
                FailedAttemptDetailResponse,
                "failed",
                foreign,
                {"error_message": "safe failure"},
            ),
            (
                FailedAttemptDetailResponse,
                "failed",
                complete[:1],
                {"error_message": "safe failure"},
            ),
        )
        for model, status, answers, extra in cases:
            with self.subTest(model=model.__name__, answers=answers), self.assertRaises(
                ValidationError
            ):
                model(
                    id="attempt",
                    status=status,
                    questionnaire=questionnaire,
                    answers=answers,
                    **extra,
                )

    def test_fun_analysis_and_completed_attempt_require_coherent_answers(self):
        questionnaire = FunQuestionnaire.model_validate(self.fun_payload())
        public = to_public_questionnaire(questionnaire)
        answers = [
            {"question_id": question.id, "selected_option_id": "a"}
            for question in questionnaire.questions
        ]
        analysis = {
            "title": "Result",
            "summary": "Summary",
            "sections": [{"heading": "Trait", "body": "Body"}],
            "charts": [],
        }
        FunAnalysisInput.model_validate(
            {"questionnaire": questionnaire, "answers": answers}
        )
        result = CompletedFunResult.model_validate(
            {"answers": answers, "analysis": analysis}
        )
        base = {
            "id": "attempt",
            "status": "completed",
            "mode": "fun",
            "questionnaire": public,
            "answers": answers,
            "result": result,
        }
        CompletedFunAttemptDetailResponse.model_validate(base)

        duplicate = [answers[0], answers[0], *answers[2:]]
        foreign = [dict(answer) for answer in answers]
        foreign[0]["question_id"] = "foreign"
        mismatched_result = {
            "answers": [{**answers[0], "selected_option_id": "b"}, *answers[1:]],
            "analysis": analysis,
        }
        knowledge_public = {**public.model_dump(mode="json"), "mode": "knowledge"}
        for mutation in (
            {**base, "questionnaire": knowledge_public},
            {**base, "answers": duplicate},
            {**base, "answers": foreign},
            {**base, "result": mismatched_result},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                CompletedFunAttemptDetailResponse.model_validate(mutation)

        with self.assertRaises(ValidationError):
            FunAnalysisInput.model_validate(
                {"questionnaire": questionnaire, "answers": duplicate}
            )
        with self.assertRaises(ValidationError):
            FunAnalysisInput.model_validate(
                {"questionnaire": questionnaire, "answers": foreign}
            )

    def test_answer_request_sizes_and_identifiers_are_strict(self):
        answers = [AnswerSelection(question_id="q1", selected_option_id="a")]
        SaveAnswersRequest(user_id=" user ", answers=answers)
        with self.assertRaises(ValidationError):
            SaveAnswersRequest(user_id="user", answers=[])
        with self.assertRaises(ValidationError):
            SubmitAttemptRequest(user_id="user", request_id=uuid4(), answers=answers)
        with self.assertRaises(ValidationError):
            AnswerSelection(question_id="bad id", selected_option_id="a")


if __name__ == "__main__":
    unittest.main()
