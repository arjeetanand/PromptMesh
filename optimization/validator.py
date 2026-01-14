from evaluation.scorer import evaluate

def validate_improvement(
    old_output: str,
    new_output: str,
    constraints: dict
) -> bool:

    old_eval = evaluate(old_output, constraints)
    new_eval = evaluate(new_output, constraints)

    return (
        new_eval.passed
        and new_eval.score >= old_eval.score
        and new_eval.breakdown["hallucination"]
            <= old_eval.breakdown["hallucination"]
    )
