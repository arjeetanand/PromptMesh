import unittest
from unittest.mock import patch

from evaluation.judge import judge_output
from evaluation.scorer import evaluate
from evaluation.types import JudgeUnavailableError


class EvaluationScoringTests(unittest.TestCase):
    judge_scores = {
        "accuracy": 2,
        "completeness": 10,
        "adherence": 2,
        "hallucination": 0,
    }

    def score(self, task_type):
        evaluator_globals = {
            "rule_checks": lambda output, constraints: {"non_empty": True},
            "judge_output": lambda output, source: self.judge_scores,
        }
        with patch.dict(evaluate.__globals__, evaluator_globals):
            return evaluate("output", {}, "source", task_type)

    def test_classification_uses_classification_weights(self):
        self.assertEqual(self.score("classification").score, 1.6)

    def test_generation_uses_completeness_weight(self):
        self.assertEqual(self.score("generation").score, 4.2)

    def test_missing_judge_result_fails_instead_of_scoring_zero(self):
        evaluator_globals = {
            "rule_checks": lambda output, constraints: {"non_empty": True},
            "judge_output": lambda output, source: None,
        }
        with patch.dict(evaluate.__globals__, evaluator_globals):
            with self.assertRaisesRegex(JudgeUnavailableError, "not scored"):
                evaluate("output", {}, "source", "classification")

    def test_three_judge_failures_produce_no_default_score(self):
        with (
            patch("evaluation.judge.get_judge_model", side_effect=RuntimeError("offline")) as get_judge,
            patch("builtins.print"),
        ):
            self.assertIsNone(judge_output("output", "source"))
        self.assertEqual(get_judge.call_count, 3)


if __name__ == "__main__":
    unittest.main()
