from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestMode(str, Enum):
    KNOWLEDGE = "knowledge"
    FUN = "fun"


class TestDifficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TestAttemptStatus(str, Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=40,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]
UserId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=320)
]
ProviderValue = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=0, max_length=500)
]
Prompt = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
OptionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
]
KnowledgePoint = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]


class QuestionOption(StrictModel):
    id: Identifier
    text: OptionText


class PublicQuestion(StrictModel):
    id: Identifier
    prompt: Prompt
    options: list[QuestionOption] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def validate_unique_option_ids(self) -> PublicQuestion:
        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option ids must be unique within a question")
        return self


class KnowledgeQuestion(PublicQuestion):
    correct_option_id: Identifier
    explanation: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    knowledge_points: list[KnowledgePoint] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_answer_and_knowledge_points(self) -> KnowledgeQuestion:
        if self.correct_option_id not in {option.id for option in self.options}:
            raise ValueError("correct_option_id must identify an option in this question")
        return self


class FunQuestion(PublicQuestion):
    pass


def _validate_question_ids(questions: list[PublicQuestion]) -> None:
    question_ids = [question.id for question in questions]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("question ids must be unique")


def _validate_supported_question_count(questions: list[PublicQuestion]) -> None:
    if len(questions) not in {5, 10, 15, 20}:
        raise ValueError("question count must be exactly 5, 10, 15, or 20")


class KnowledgeQuestionnaire(StrictModel):
    mode: Literal[TestMode.KNOWLEDGE]
    title: Title
    description: Description
    questions: list[KnowledgeQuestion] = Field(min_length=5, max_length=20)

    @model_validator(mode="after")
    def validate_questions(self) -> KnowledgeQuestionnaire:
        _validate_supported_question_count(self.questions)
        _validate_question_ids(self.questions)
        return self


class FunQuestionnaire(StrictModel):
    mode: Literal[TestMode.FUN]
    title: Title
    description: Description
    questions: list[FunQuestion] = Field(min_length=5, max_length=20)

    @model_validator(mode="after")
    def validate_questions(self) -> FunQuestionnaire:
        _validate_supported_question_count(self.questions)
        _validate_question_ids(self.questions)
        return self


Questionnaire: TypeAlias = Annotated[
    KnowledgeQuestionnaire | FunQuestionnaire, Field(discriminator="mode")
]


class PublicQuestionnaire(StrictModel):
    mode: TestMode
    title: Title
    description: Description
    question_count: Literal[5, 10, 15, 20]
    questions: list[PublicQuestion] = Field(min_length=5, max_length=20)

    @model_validator(mode="after")
    def validate_questions(self) -> PublicQuestionnaire:
        _validate_supported_question_count(self.questions)
        if self.question_count != len(self.questions):
            raise ValueError("question_count must match questions")
        _validate_question_ids(self.questions)
        return self


def to_public_questionnaire(
    questionnaire: KnowledgeQuestionnaire | FunQuestionnaire,
) -> PublicQuestionnaire:
    return PublicQuestionnaire(
        mode=questionnaire.mode,
        title=questionnaire.title,
        description=questionnaire.description,
        question_count=len(questionnaire.questions),
        questions=[
            PublicQuestion(
                id=question.id,
                prompt=question.prompt,
                options=[QuestionOption(id=option.id, text=option.text) for option in question.options],
            )
            for question in questionnaire.questions
        ],
    )


class AnalysisSection(StrictModel):
    heading: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ]
    body: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)
    ]

    @model_validator(mode="before")
    @classmethod
    def normalize_text_section(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        text = value.strip()
        heading = "分析要点"
        body = text
        if text.startswith("**"):
            closing = text.find("**", 2)
            if closing > 2:
                candidate = text[2:closing].rstrip("：:").strip()
                remainder = text[closing + 2 :].strip()
                if candidate and len(candidate) <= 80:
                    heading = candidate
                    body = remainder or candidate
        elif "：" in text:
            candidate, remainder = text.split("：", 1)
            if candidate.strip() and remainder.strip() and len(candidate.strip()) <= 80:
                heading, body = candidate.strip(), remainder.strip()
        elif ":" in text:
            candidate, remainder = text.split(":", 1)
            if candidate.strip() and remainder.strip() and len(candidate.strip()) <= 80:
                heading, body = candidate.strip(), remainder.strip()
        return {"heading": heading, "body": body}


class ChartItem(StrictModel):
    label: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
    ]
    value: float = Field(ge=0, le=100, allow_inf_nan=False)
    max_value: float = Field(ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        normalized = dict(value)
        if "label" not in normalized:
            for alias in ("item", "name", "dimension"):
                if alias in normalized:
                    normalized["label"] = normalized[alias]
                    break
        if "value" not in normalized and "score" in normalized:
            normalized["value"] = normalized["score"]
        if "max_value" not in normalized:
            normalized["max_value"] = normalized.get("max", 100)
        for alias in ("item", "name", "dimension", "score", "max"):
            normalized.pop(alias, None)
        return normalized

    @model_validator(mode="after")
    def validate_value(self) -> ChartItem:
        if self.value > self.max_value:
            raise ValueError("value must not exceed max_value")
        return self


class ChartData(StrictModel):
    kind: Literal["radar", "bar", "donut"]
    title: Title
    items: list[ChartItem] = Field(min_length=2, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        normalized = dict(value)
        if "kind" not in normalized and "type" in normalized:
            normalized["kind"] = normalized["type"]
        if "items" not in normalized and "data" in normalized:
            normalized["items"] = normalized["data"]
        normalized.pop("type", None)
        normalized.pop("data", None)
        return normalized


class KnowledgeAnalysis(StrictModel):
    title: Title
    summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)
    ]
    mastered: list[AnalysisSection] = Field(default_factory=list, max_length=6)
    weaknesses: list[AnalysisSection] = Field(default_factory=list, max_length=6)
    recommendations: list[AnalysisSection] = Field(default_factory=list, max_length=6)
    charts: list[ChartData] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def require_at_least_one_section(self) -> KnowledgeAnalysis:
        if not (self.mastered or self.weaknesses or self.recommendations):
            raise ValueError("at least one analysis section is required")
        return self


class FunAnalysis(StrictModel):
    title: Title
    summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)
    ]
    sections: list[AnalysisSection] = Field(min_length=1, max_length=6)
    charts: list[ChartData] = Field(default_factory=list, max_length=2)


class AnswerSelection(StrictModel):
    question_id: Identifier
    selected_option_id: Identifier


def _validate_unique_answer_ids(answers: list[AnswerSelection]) -> None:
    question_ids = [answer.question_id for answer in answers]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("answers must contain each question at most once")


class TestPreferencesUpdateRequest(StrictModel):
    user_id: UserId
    generation_provider_id: ProviderValue | None = None
    generation_model: ProviderValue | None = None
    analysis_provider_id: ProviderValue | None = None
    analysis_model: ProviderValue | None = None


class CreateTestRequest(StrictModel):
    user_id: UserId
    request_id: UUID
    mode: TestMode
    topic: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    requirements: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=0, max_length=4000)
    ] = ""
    question_count: Literal[5, 10, 15, 20] = 10
    difficulty: TestDifficulty | None = None
    retry_failed: bool = False

    @model_validator(mode="after")
    def normalize_difficulty(self) -> CreateTestRequest:
        if self.mode is TestMode.FUN:
            if self.difficulty is not None:
                raise ValueError("fun tests do not accept difficulty")
        elif self.difficulty is None:
            self.difficulty = TestDifficulty.INTERMEDIATE
        return self


class CreateAttemptRequest(StrictModel):
    user_id: UserId
    request_id: UUID


class SaveAnswersRequest(StrictModel):
    user_id: UserId
    answers: list[AnswerSelection] = Field(min_length=1, max_length=20)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: list[AnswerSelection]) -> list[AnswerSelection]:
        _validate_unique_answer_ids(answers)
        return answers


class SubmitAttemptRequest(StrictModel):
    user_id: UserId
    request_id: UUID
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: list[AnswerSelection]) -> list[AnswerSelection]:
        _validate_unique_answer_ids(answers)
        if len(answers) not in {5, 10, 15, 20}:
            raise ValueError("submitted answer count must be exactly 5, 10, 15, or 20")
        return answers


class RetryAnalysisRequest(StrictModel):
    user_id: UserId
    request_id: UUID


class ModelSnapshot(StrictModel):
    provider_id: ProviderValue
    provider_name: ProviderValue
    model: ProviderValue
    temperature: Literal[1.0] = 1.0
    captured_at: datetime


class KnowledgePointScore(StrictModel):
    label: KnowledgePoint
    correct: int = Field(ge=0)
    total: int = Field(ge=1)
    percentage: float = Field(ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_correct_count(self) -> KnowledgePointScore:
        if self.correct > self.total:
            raise ValueError("correct must not exceed total")
        return self


class KnowledgeScore(StrictModel):
    correct_count: int = Field(ge=0)
    question_count: int = Field(ge=1)
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    max_score: Literal[100.0] = 100.0
    knowledge_points: list[KnowledgePointScore]

    @model_validator(mode="after")
    def validate_correct_count(self) -> KnowledgeScore:
        if self.correct_count > self.question_count:
            raise ValueError("correct_count must not exceed question_count")
        return self


def _validate_complete_answers(
    questionnaire: KnowledgeQuestionnaire | FunQuestionnaire | PublicQuestionnaire,
    answers: list[AnswerSelection],
) -> None:
    _validate_answers_against_questionnaire(questionnaire, answers, require_complete=True)


def _validate_answers_against_questionnaire(
    questionnaire: KnowledgeQuestionnaire | FunQuestionnaire | PublicQuestionnaire,
    answers: list[AnswerSelection],
    *,
    require_complete: bool,
) -> None:
    _validate_unique_answer_ids(answers)
    expected = {question.id for question in questionnaire.questions}
    actual = {answer.question_id for answer in answers}
    if not actual.issubset(expected):
        raise ValueError("answers must only identify questionnaire questions")
    if require_complete and actual != expected:
        raise ValueError("answers must contain exactly one selection for every question")
    options_by_question = {
        question.id: {option.id for option in question.options}
        for question in questionnaire.questions
    }
    if any(
        answer.selected_option_id not in options_by_question[answer.question_id]
        for answer in answers
    ):
        raise ValueError("selected_option_id must identify an option in its question")


def _calculate_knowledge_score(
    questionnaire: KnowledgeQuestionnaire,
    answers: list[AnswerSelection],
) -> KnowledgeScore:
    answer_map = {
        answer.question_id: answer.selected_option_id for answer in answers
    }
    correct_count = 0
    totals: dict[str, list[int]] = {}
    for question in questionnaire.questions:
        is_correct = answer_map[question.id] == question.correct_option_id
        if is_correct:
            correct_count += 1
        for label in dict.fromkeys(question.knowledge_points):
            counts = totals.setdefault(label, [0, 0])
            counts[1] += 1
            if is_correct:
                counts[0] += 1
    points = [
        KnowledgePointScore(
            label=label,
            correct=counts[0],
            total=counts[1],
            percentage=round(counts[0] / counts[1] * 100, 2),
        )
        for label, counts in totals.items()
    ]
    return KnowledgeScore(
        correct_count=correct_count,
        question_count=len(questionnaire.questions),
        score=round(correct_count / len(questionnaire.questions) * 100, 2),
        max_score=100.0,
        knowledge_points=points,
    )


class KnowledgeAnalysisInput(StrictModel):
    questionnaire: KnowledgeQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)
    score: KnowledgeScore

    @model_validator(mode="after")
    def validate_input(self) -> KnowledgeAnalysisInput:
        _validate_complete_answers(self.questionnaire, self.answers)
        expected_score = _calculate_knowledge_score(self.questionnaire, self.answers)
        if self.score.model_dump() != expected_score.model_dump():
            raise ValueError("score must match questionnaire and answers")
        return self


class FunAnalysisInput(StrictModel):
    questionnaire: FunQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)

    @model_validator(mode="after")
    def validate_input(self) -> FunAnalysisInput:
        _validate_complete_answers(self.questionnaire, self.answers)
        return self


class CompletedKnowledgeQuestion(KnowledgeQuestion):
    selected_option_id: Identifier
    is_correct: bool

    @model_validator(mode="after")
    def validate_selection_truth(self) -> CompletedKnowledgeQuestion:
        if self.selected_option_id not in {option.id for option in self.options}:
            raise ValueError("selected_option_id must identify an option in this question")
        if self.is_correct != (self.selected_option_id == self.correct_option_id):
            raise ValueError("is_correct must match selected and correct option ids")
        return self


def _aggregate_completed_knowledge_points(
    questions: list[CompletedKnowledgeQuestion],
) -> list[KnowledgePointScore]:
    totals: dict[str, list[int]] = {}
    for question in questions:
        for label in dict.fromkeys(question.knowledge_points):
            counts = totals.setdefault(label, [0, 0])
            counts[1] += 1
            if question.is_correct:
                counts[0] += 1
    return [
        KnowledgePointScore(
            label=label,
            correct=counts[0],
            total=counts[1],
            percentage=round(counts[0] / counts[1] * 100, 2),
        )
        for label, counts in totals.items()
    ]


def _knowledge_point_scores_match(
    actual: list[KnowledgePointScore], expected: list[KnowledgePointScore]
) -> bool:
    if len({item.label for item in actual}) != len(actual):
        return False
    actual_by_label = {item.label: item.model_dump() for item in actual}
    expected_by_label = {item.label: item.model_dump() for item in expected}
    return actual_by_label == expected_by_label


class CompletedKnowledgeResult(StrictModel):
    questions: list[CompletedKnowledgeQuestion] = Field(min_length=5, max_length=20)
    correct_count: int = Field(ge=0)
    question_count: Literal[5, 10, 15, 20]
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    max_score: Literal[100.0] = 100.0
    knowledge_points: list[KnowledgePointScore]
    analysis: KnowledgeAnalysis

    @model_validator(mode="after")
    def validate_trusted_result(self) -> CompletedKnowledgeResult:
        _validate_supported_question_count(self.questions)
        _validate_question_ids(self.questions)
        if self.question_count != len(self.questions):
            raise ValueError("question_count must match questions")
        expected_correct = sum(question.is_correct for question in self.questions)
        if self.correct_count != expected_correct:
            raise ValueError("correct_count must match question results")
        expected_score = round(expected_correct / len(self.questions) * 100, 2)
        if self.score != expected_score:
            raise ValueError("score must match question results")
        expected_points = _aggregate_completed_knowledge_points(self.questions)
        if not _knowledge_point_scores_match(self.knowledge_points, expected_points):
            raise ValueError("knowledge_points must match question results")
        return self


class CompletedFunResult(StrictModel):
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)
    analysis: FunAnalysis

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: list[AnswerSelection]) -> list[AnswerSelection]:
        _validate_unique_answer_ids(answers)
        if len(answers) not in {5, 10, 15, 20}:
            raise ValueError("completed answer count must be exactly 5, 10, 15, or 20")
        return answers


class TestPreferencesResponse(TestPreferencesUpdateRequest):
    pass


class TestAttemptSummaryResponse(StrictModel):
    id: str
    status: TestAttemptStatus
    created_at: datetime
    updated_at: datetime
    score: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


class TestSessionSummaryResponse(StrictModel):
    id: str
    title: Title
    description: Description
    mode: TestMode
    question_count: Literal[5, 10, 15, 20]
    updated_at: datetime


class TestSessionDetailResponse(TestSessionSummaryResponse):
    questionnaire: PublicQuestionnaire
    attempts: list[TestAttemptSummaryResponse] = Field(default_factory=list)


class DraftAttemptDetailResponse(StrictModel):
    id: str
    status: Literal[TestAttemptStatus.DRAFT]
    questionnaire: PublicQuestionnaire
    answers: list[AnswerSelection] = Field(max_length=20)

    @model_validator(mode="after")
    def validate_answers(self) -> DraftAttemptDetailResponse:
        _validate_answers_against_questionnaire(
            self.questionnaire, self.answers, require_complete=False
        )
        return self


class AnalyzingAttemptDetailResponse(StrictModel):
    id: str
    status: Literal[TestAttemptStatus.ANALYZING]
    questionnaire: PublicQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)

    @model_validator(mode="after")
    def validate_answers(self) -> AnalyzingAttemptDetailResponse:
        _validate_complete_answers(self.questionnaire, self.answers)
        return self


class FailedAttemptDetailResponse(StrictModel):
    id: str
    status: Literal[TestAttemptStatus.FAILED]
    questionnaire: PublicQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)
    error_message: Annotated[str, StringConstraints(max_length=500)]

    @model_validator(mode="after")
    def validate_answers(self) -> FailedAttemptDetailResponse:
        _validate_complete_answers(self.questionnaire, self.answers)
        return self


class CompletedKnowledgeAttemptDetailResponse(StrictModel):
    id: str
    status: Literal[TestAttemptStatus.COMPLETED]
    mode: Literal[TestMode.KNOWLEDGE]
    questionnaire: PublicQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)
    result: CompletedKnowledgeResult

    @model_validator(mode="after")
    def validate_snapshot(self) -> CompletedKnowledgeAttemptDetailResponse:
        if self.questionnaire.mode is not TestMode.KNOWLEDGE:
            raise ValueError("knowledge attempt requires a knowledge questionnaire")
        _validate_complete_answers(self.questionnaire, self.answers)
        public_result_questions = [
            PublicQuestion(
                id=question.id,
                prompt=question.prompt,
                options=question.options,
            )
            for question in self.result.questions
        ]
        if self.questionnaire.questions != public_result_questions:
            raise ValueError("result questions must match public questionnaire")
        if self.questionnaire.question_count != self.result.question_count:
            raise ValueError("result question_count must match questionnaire")
        answer_map = {
            answer.question_id: answer.selected_option_id for answer in self.answers
        }
        result_answer_map = {
            question.id: question.selected_option_id for question in self.result.questions
        }
        if answer_map != result_answer_map:
            raise ValueError("result selections must match saved answers")
        return self


class CompletedFunAttemptDetailResponse(StrictModel):
    id: str
    status: Literal[TestAttemptStatus.COMPLETED]
    mode: Literal[TestMode.FUN]
    questionnaire: PublicQuestionnaire
    answers: list[AnswerSelection] = Field(min_length=5, max_length=20)
    result: CompletedFunResult

    @model_validator(mode="after")
    def validate_snapshot(self) -> CompletedFunAttemptDetailResponse:
        if self.questionnaire.mode is not TestMode.FUN:
            raise ValueError("fun attempt requires a fun questionnaire")
        _validate_complete_answers(self.questionnaire, self.answers)
        answer_map = {
            answer.question_id: answer.selected_option_id for answer in self.answers
        }
        result_answer_map = {
            answer.question_id: answer.selected_option_id
            for answer in self.result.answers
        }
        if answer_map != result_answer_map:
            raise ValueError("result answers must match saved answers")
        return self


TestAttemptDetailResponse: TypeAlias = (
    DraftAttemptDetailResponse
    | AnalyzingAttemptDetailResponse
    | FailedAttemptDetailResponse
    | CompletedKnowledgeAttemptDetailResponse
    | CompletedFunAttemptDetailResponse
)


class TestListResponse(StrictModel):
    items: list[TestSessionSummaryResponse]
    next_cursor: str | None = None


class GenerationStatusResponse(StrictModel):
    state: Literal["generating", "completed", "failed"]
    request_id: UUID
    test_id: str | None = None
    error_message: Annotated[str, StringConstraints(max_length=500)] | None = None
    retry_after_ms: int = Field(default=1000, ge=0)
