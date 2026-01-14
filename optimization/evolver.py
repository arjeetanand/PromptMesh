from evaluation.scorer import evaluate
from optimization.mutator import generate_prompt_variants
from optimization.selector import select_best_prompt


def evolve_prompt(
    initial_prompt: str,
    base_output: str,
    constraints: dict,
    optimizer_model,
    eval_model,   # NEW
    max_iters: int = 5,
    min_delta: float = 0.3,
    variants_per_iter: int = 5
):
    """
    Iteratively evolves a prompt until convergence.
    """

    history = []

    current_prompt = initial_prompt
    # current_eval = evaluate(base_output, constraints)
    initial_result = eval_model.run(initial_prompt, constraints)
    current_eval = evaluate(initial_result["output"], constraints)


    history.append({
        "iteration": 0,
        "prompt": current_prompt,
        "score": current_eval.score,
        "breakdown": current_eval.breakdown
    })

    for iteration in range(1, max_iters + 1):
        failure_type = (
            "hallucination"
            if current_eval.breakdown["hallucination"] > 3
            else "accuracy_loss"
        )

        candidates = generate_prompt_variants(
            original_prompt=current_prompt,
            failure_type=failure_type,
            bad_output=base_output,
            n=variants_per_iter
        )

        best_candidate, all_candidates = select_best_prompt(
            candidate_prompts=candidates,
            model=optimizer_model,
            constraints=constraints
        )

        delta = best_candidate["score"] - current_eval.score

        history.append({
            "iteration": iteration,
            "prompt": best_candidate["prompt"],
            "score": best_candidate["score"],
            "breakdown": best_candidate["breakdown"]
        })

        # ---- CONVERGENCE CHECK ----
        if delta < min_delta:
            break

        if (
            best_candidate["breakdown"]["hallucination"]
            >= current_eval.breakdown["hallucination"]
        ):
            break

        # Accept new prompt
        current_prompt = best_candidate["prompt"]
        # current_eval = evaluate(best_candidate["output"], constraints)
        current_eval = evaluate(best_candidate["output"], constraints)


    return history
