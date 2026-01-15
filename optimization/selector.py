# optimization/selector.py

from core.types import render_prompt
from evaluation.scorer import evaluate

def select_best_prompt(candidate_prompts, model, task_inputs, constraints):
    scored = []

    for prompt in candidate_prompts:
        scores = []

        for _, text in task_inputs.items():
            rendered = render_prompt(prompt, {"text": text})
            result = model.run(rendered, constraints)
            evaluation = evaluate(result["output"], constraints)
            scores.append(evaluation.score)

        avg_score = sum(scores) / len(scores)

        scored.append({
            "prompt": prompt,
            "score": avg_score
        })

    best = max(scored, key=lambda x: x["score"])
    return best, scored
