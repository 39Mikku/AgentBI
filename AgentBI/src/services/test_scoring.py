from __future__ import annotations

from collections.abc import Mapping

from AgentBI.src.schemas.test_schema import (
    KnowledgePointScore,
    KnowledgeQuestionnaire,
    KnowledgeScore,
)


class KnowledgeScoringError(ValueError):
    """The submitted answer map is incomplete or does not match the questionnaire."""


def score_knowledge_test(
    questionnaire: KnowledgeQuestionnaire,
    answers: Mapping[str, str],
) -> KnowledgeScore:
    if not isinstance(questionnaire, KnowledgeQuestionnaire):
        raise KnowledgeScoringError("a knowledge questionnaire is required")
    if not isinstance(answers, Mapping):
        raise KnowledgeScoringError("answers must be a question-to-option map")

    expected_question_ids = {question.id for question in questionnaire.questions}
    submitted_question_ids = set(answers)
    if submitted_question_ids != expected_question_ids:
        raise KnowledgeScoringError("answers must cover every question exactly once")

    correct_count = 0
    point_totals: dict[str, list[int]] = {}
    for question in questionnaire.questions:
        selected_option_id = answers[question.id]
        valid_option_ids = {option.id for option in question.options}
        if selected_option_id not in valid_option_ids:
            raise KnowledgeScoringError("an answer does not identify an available option")

        is_correct = selected_option_id == question.correct_option_id
        if is_correct:
            correct_count += 1
        for label in dict.fromkeys(question.knowledge_points):
            counts = point_totals.setdefault(label, [0, 0])
            counts[1] += 1
            if is_correct:
                counts[0] += 1

    question_count = len(questionnaire.questions)
    knowledge_points = [
        KnowledgePointScore(
            label=label,
            correct=counts[0],
            total=counts[1],
            percentage=round(counts[0] / counts[1] * 100, 2),
        )
        for label, counts in point_totals.items()
    ]
    return KnowledgeScore(
        correct_count=correct_count,
        question_count=question_count,
        score=round(correct_count / question_count * 100, 2),
        max_score=100.0,
        knowledge_points=knowledge_points,
    )
