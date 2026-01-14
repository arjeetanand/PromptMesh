from evaluation.rules import rule_checks
from evaluation.judge import judge_output
from evaluation.types import EvaluationResult

def evaluate(output: str, prompt_constraints: dict) -> EvaluationResult:
    rules = rule_checks(output, prompt_constraints)

    if not rules["non_empty"]:
        return EvaluationResult(
            score=0.0,
            breakdown={"reason": "empty_output"},
            passed=False
        )

    judge_scores = judge_output(output)

    final_score = (
        0.4 * judge_scores["accuracy"]
        + 0.3 * judge_scores["completeness"]
        + 0.2 * judge_scores["adherence"]
        - 0.1 * judge_scores["hallucination"]
    )

    return EvaluationResult(
        score=round(final_score, 2),
        breakdown=judge_scores,
        passed=True
    )
