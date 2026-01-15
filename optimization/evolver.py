from core.types import render_prompt
from evaluation.scorer import evaluate
from optimization.mutator import generate_prompt_variants
from optimization.selector import select_best_prompt
from optimization.failure_analysis import analyze_failure
from optimization.validator import validate_prompt_structure
import difflib


def evaluate_prompt(prompt_template, task_inputs, model, constraints):
    scores = []
    last_breakdown = None

    for _, text in task_inputs.items():
        rendered = render_prompt(prompt_template, {"text": text})
        result = model.run(rendered, constraints)

        evaluation = evaluate(
            result["output"],
            constraints,
            text
        )

        scores.append(evaluation.score)
        last_breakdown = evaluation.breakdown

    return sum(scores) / len(scores), last_breakdown



def print_prompt_diff(old, new):
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile="before",
        tofile="after",
        lineterm=""
    )
    for line in diff:
        print(line)


def get_model_label(model) -> str:
    """
    Returns a readable identifier for any model adapter.
    """
    if hasattr(model, "model_name"):
        return model.model_name
    if hasattr(model, "model_id"):
        return model.model_id
    return model.__class__.__name__


def evolve_prompt(
    initial_prompt: str,
    task_inputs: dict,
    constraints: dict,
    optimizer_model,
    execution_model,
    max_iters: int = 5,
    min_delta: float = 0.3,
    variants_per_iter: int = 5
):
    print(f"\n🔧 Prompt evolution using:")
    # print(f"   Optimizer model : {optimizer_model.model_name}")
    # print(f"   Execution model : {execution_model.model_name}")
    print(f"   Optimizer model : {get_model_label(optimizer_model)}")
    print(f"   Execution model : {get_model_label(execution_model)}")


    history = []

    # ---- ITERATION 0 ----
    current_prompt = initial_prompt
    current_score, current_breakdown = evaluate_prompt(
        current_prompt,
        task_inputs,
        execution_model,
        constraints
    )

    print(f"\n--- Iteration 0 (baseline) ---")
    print(f"Score     : {current_score}")
    print(f"Breakdown : {current_breakdown}")

    history.append({
        "iteration": 0,
        "prompt": current_prompt,
        "score": current_score,
        "breakdown": current_breakdown
    })

    # ---- EVOLUTION LOOP ----
    for iteration in range(1, max_iters + 1):

        failure_type = analyze_failure(current_breakdown)

        print(f"\n--- Iteration {iteration} ---")
        print(f"Failure driving evolution : {failure_type}")

        # Generate candidates
        candidates = generate_prompt_variants(
            original_prompt=current_prompt,
            failure_type=failure_type,
            bad_output="",
            n=variants_per_iter
        )

        # Guardrails
        candidates = [
            p for p in candidates
            if validate_prompt_structure(current_prompt, p)
        ]

        if not candidates:
            print("❌ No valid prompt variants survived validation.")
            break

        best, scored = select_best_prompt(
            candidate_prompts=candidates,
            model=execution_model,
            task_inputs=task_inputs,
            constraints=constraints
        )

        delta = best["score"] - current_score

        print(f"Best candidate score : {best['score']} (Δ {delta:+.2f})")

        if delta < min_delta:
            print("⛔ Convergence reached (delta below threshold).")
            break

        print("\nPrompt diff:")
        print_prompt_diff(current_prompt, best["prompt"])

        # Accept
        current_prompt = best["prompt"]
        current_score = best["score"]

        _, current_breakdown = evaluate_prompt(
            current_prompt,
            task_inputs,
            execution_model,
            constraints
        )

        print(f"New breakdown : {current_breakdown}")

        history.append({
            "iteration": iteration,
            "prompt": current_prompt,
            "score": current_score,
            "breakdown": current_breakdown
        })

    return history
