import unittest

from AgentBI.src.schemas.test_schema import KnowledgeQuestionnaire
from AgentBI.src.services.test_scoring import (
    KnowledgeScoringError,
    score_knowledge_test,
)


class TestKnowledgeScoring(unittest.TestCase):
    @staticmethod
    def point(result, label: str):
        return next(point for point in result.knowledge_points if point.label == label)

    @staticmethod
    def questionnaire() -> KnowledgeQuestionnaire:
        answer_keys = ["a", "b", "a", "b", "a"]
        points = ["Python", "Python", "Typing", "Typing", "Python"]
        return KnowledgeQuestionnaire.model_validate(
            {
                "mode": "knowledge",
                "title": "Python",
                "description": "",
                "questions": [
                    {
                        "id": f"q{index}",
                        "prompt": f"Question {index}",
                        "options": [
                            {"id": "a", "text": "A"},
                            {"id": "b", "text": "B"},
                        ],
                        "correct_option_id": answer_keys[index - 1],
                        "explanation": "Explanation",
                        "knowledge_points": [points[index - 1]],
                    }
                    for index in range(1, 6)
                ],
            }
        )

    def test_score_is_deterministic_and_groups_knowledge_points(self):
        result = score_knowledge_test(
            self.questionnaire(),
            {"q1": "a", "q2": "a", "q3": "a", "q4": "a", "q5": "b"},
        )
        self.assertEqual(
            (result.correct_count, result.question_count, result.score, result.max_score),
            (2, 5, 40.0, 100.0),
        )
        self.assertEqual(self.point(result, "Python").correct, 1)
        self.assertEqual(self.point(result, "Python").total, 3)
        self.assertEqual(self.point(result, "Python").percentage, 33.33)
        self.assertEqual(self.point(result, "Typing").percentage, 50.0)

    def test_score_requires_exactly_one_valid_answer_per_question(self):
        questionnaire = self.questionnaire()
        for answers in (
            {"q1": "a"},
            {
                "q1": "a",
                "q2": "b",
                "q3": "a",
                "q4": "b",
                "q5": "a",
                "extra": "a",
            },
            {"q1": "missing", "q2": "b", "q3": "a", "q4": "b", "q5": "a"},
        ):
            with self.subTest(answers=answers), self.assertRaises(KnowledgeScoringError):
                score_knowledge_test(questionnaire, answers)

    def test_score_rounds_percentages_to_two_decimal_places(self):
        result = score_knowledge_test(
            self.questionnaire(),
            {"q1": "a", "q2": "b", "q3": "b", "q4": "a", "q5": "b"},
        )
        self.assertEqual(result.score, 40.0)
        self.assertEqual(self.point(result, "Python").percentage, 66.67)
        self.assertEqual(self.point(result, "Typing").percentage, 0.0)

    def test_duplicate_knowledge_point_on_one_question_is_counted_once(self):
        questionnaire = self.questionnaire()
        questionnaire.questions[0].knowledge_points = ["Python", "Python"]
        result = score_knowledge_test(
            questionnaire,
            {"q1": "a", "q2": "a", "q3": "a", "q4": "a", "q5": "a"},
        )
        self.assertEqual(self.point(result, "Python").total, 3)

    def test_score_does_not_mutate_questionnaire_or_answers(self):
        questionnaire = self.questionnaire()
        answers = {"q1": "a", "q2": "b", "q3": "a", "q4": "b", "q5": "a"}
        before_questionnaire = questionnaire.model_dump()
        before_answers = answers.copy()
        score_knowledge_test(questionnaire, answers)
        self.assertEqual(questionnaire.model_dump(), before_questionnaire)
        self.assertEqual(answers, before_answers)

    def test_knowledge_point_scores_remain_an_ordinary_list(self):
        result = score_knowledge_test(
            self.questionnaire(),
            {"q1": "a", "q2": "b", "q3": "a", "q4": "b", "q5": "a"},
        )
        self.assertIs(type(result.knowledge_points), list)


if __name__ == "__main__":
    unittest.main()
