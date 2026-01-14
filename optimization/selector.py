from evaluation.scorer import evaluate


def select_best_prompt(
    candidate_prompts: list[str],
    model,
    constraints: dict
):
    scored = []

    for prompt in candidate_prompts:
        result = model.run(prompt, constraints)
        evaluation = evaluate(result["output"], constraints)

        scored.append({
            "prompt": prompt,
            "output": result["output"],
            "score": evaluation.score,
            "breakdown": evaluation.breakdown
        })

    best = max(scored, key=lambda x: x["score"])
    return best, scored
