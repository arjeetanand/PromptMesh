# optimization/selector.py

from core.types import render_prompt
from evaluation.scorer import evaluate


def select_best_prompt(candidate_prompts, model, task_inputs, constraints, input_var):
    scored = []

    for prompt in candidate_prompts:
        scores = []

        for text in task_inputs:
            rendered = render_prompt(
                prompt,
                {input_var: text}
            )

            result = model.run(rendered, constraints)

            evaluation = evaluate(
                result["output"],
                constraints,
                text
            )

            scores.append(evaluation.score)

        avg_score = sum(scores) / len(scores)
        worst_score = min(scores)

        scored.append({
            "prompt": prompt,
            "score": avg_score,
            "worst_score": worst_score
        })

    # Prefer higher worst-case, then higher average
    best = max(scored, key=lambda x: (x["worst_score"], x["score"]))
    return best, scored
