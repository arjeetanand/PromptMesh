# optimization/evolver.py

from core.types import render_prompt
from evaluation.scorer import evaluate
from optimization.mutator import generate_prompt_variants
from optimization.selector import select_best_prompt
from optimization.failure_analysis import analyze_failure
from optimization.validator import validate_prompt_structure
import difflib


def evaluate_prompt(prompt_template, task_inputs, model, constraints, input_var):
    scores = []
    breakdowns = []

    for text in task_inputs:
        rendered = render_prompt(
            prompt_template,
            {input_var: text}
        )

        result = model.run(rendered, constraints)

        evaluation = evaluate(
            result["output"],
            constraints,
            text
        )

        scores.append(evaluation.score)
        breakdowns.append(evaluation.breakdown)

    avg_score = sum(scores) / len(scores)
    return avg_score, breakdowns


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
    if hasattr(model, "model_name"):
        return model.model_name
    if hasattr(model, "model_id"):
        return model.model_id
    return model.__class__.__name__


def evolve_prompt(
    initial_prompt: str,
    task_inputs: list[str],
    constraints: dict,
    optimizer_model,
    execution_model,
    input_var: str,
    max_iters: int = 5,
    min_delta: float = 0.3,
    variants_per_iter: int = 5
):
    print(f"\n🔧 Prompt evolution using:")
    print(f"   Optimizer model : {get_model_label(optimizer_model)}")
    print(f"   Execution model : {get_model_label(execution_model)}")

    history = []

    # ---- ITERATION 0 ----
    current_prompt = initial_prompt
    current_score, current_breakdowns = evaluate_prompt(
        current_prompt,
        task_inputs,
        execution_model,
        constraints,
        input_var
    )

    print(f"\n--- Iteration 0 (baseline) ---")
    print(f"Score     : {current_score}")
    print(f"Breakdowns: {current_breakdowns[:2]}")

    history.append({
        "iteration": 0,
        "prompt": current_prompt,
        "score": current_score,
        "breakdowns": current_breakdowns
    })

    # ---- EVOLUTION LOOP ----
    for iteration in range(1, max_iters + 1):

        failure_type = analyze_failure(current_breakdowns)

        print(f"\n--- Iteration {iteration} ---")
        print(f"Failure driving evolution : {failure_type}")

        candidates = generate_prompt_variants(
            original_prompt=current_prompt,
            failure_type=failure_type,
            bad_output="",
            n=variants_per_iter
        )

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
            constraints=constraints,
            input_var=input_var
        )

    

        delta = best["score"] - current_score
        print(f"Best candidate score : {best['score']} (Δ {delta:+.2f})")

        if delta < min_delta:
            print("⛔ Convergence reached (delta below threshold).")
            break

        print("\nPrompt diff:")
        print_prompt_diff(current_prompt, best["prompt"])

        # Accept only meaningful improvement
        current_prompt = best["prompt"]
        current_score = best["score"]

        _, current_breakdowns = evaluate_prompt(
            current_prompt,
            task_inputs,
            execution_model,
            constraints,
            input_var
        )




        print(f"New breakdowns (sample): {current_breakdowns[:2]}")

        history.append({
            "iteration": iteration,
            "prompt": current_prompt,
            "score": current_score,
            "breakdowns": current_breakdowns
        })

    return history
