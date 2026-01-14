# ===============================
# MAIN ENTRY – PROMPT EVOLUTION
# ===============================

from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.executor import PromptExecutor
from evaluation.scorer import evaluate

from comparison.runner import run_prompt_comparison
from comparison.ranker import rank_prompts

from optimization.failure_analysis import analyze_failure
from optimization.evolver import evolve_prompt

from models.registry import get_model
from storage.repository import (
    save_prompt,
    save_run,
    save_evaluation
)

# -------------------------------
# CONFIG
# -------------------------------
TASK = "summarization"
PROMPT_VERSIONS = ["v1", "v2"]



TEST_CASES = {
    "baseline": (
        "OpenAI released a new language model in 2025. "
        "The model improved reasoning performance and reduced hallucinations "
        "compared to earlier versions."
    ),

    "hallucination_trap": (
        "In 2025, OpenAI released a new model. "
        "The announcement mentioned improvements over previous systems "
        "but did not provide specific metrics or comparisons."
    ),

    "completeness_failure": (
        "OpenAI announced a new AI model in 2025."
    ),

    "instruction_conflict": (
        "OpenAI released a new model in 2025. "
        "The release emphasized that the model should not be described as more "
        "intelligent than previous systems, only more reliable."
    ),
}


TEST_NAME = "hallucination_trap"
INPUT_TEXT = TEST_CASES[TEST_NAME]

# TEST_NAME = "baseline"
# TEST_NAME = "hallucination_trap"
# TEST_NAME = "completeness_failure"
# TEST_NAME = "instruction_conflict"


EVAL_MODELS = [
    "llama3",
    "qwen2.5",
    "command-a-03-2025"
]

FINAL_RUN_MODELS = [
    "llama3-8b"
]

OPTIMIZER_MODEL_NAME = "command-a-03-2025"

MAX_EVOLUTION_ITERS = 3
VARIANTS_PER_ITER = 3
MIN_DELTA = 0.25


# -------------------------------
# STEP 1: INITIAL PROMPT COMPARISON
# -------------------------------
print("\n==== INITIAL PROMPT COMPARISON ====")

registry = PromptRegistry()
executor = PromptExecutor()

results = run_prompt_comparison(
    task=TASK,
    prompt_versions=PROMPT_VERSIONS,
    input_vars={"text": INPUT_TEXT},
    models=EVAL_MODELS
)

ranked = rank_prompts(results)
best_run = ranked[0]

base_prompt_def = registry.load(TASK, best_run.prompt_version)

print("\n==== BEST INITIAL PROMPT ====")
print("Prompt version:", best_run.prompt_version)
print("Model:", best_run.model)
print("Score:", best_run.evaluation.score)
print("Breakdown:", best_run.evaluation.breakdown)
print("Output:\n", best_run.output)


# -------------------------------
# STEP 2: SAVE BASE PROMPT
# -------------------------------
prompt_id = save_prompt(
    task=TASK,
    version=best_run.prompt_version,
    prompt_text=base_prompt_def["template"]
)


# -------------------------------
# STEP 3: FAILURE ANALYSIS
# -------------------------------
failure_type = analyze_failure(best_run.evaluation.breakdown)

print("\nDetected failure type:", failure_type)

if failure_type == "none":
    print("Prompt already optimal. Skipping evolution.")
    final_prompt = base_prompt_def["template"]
    evolution_history = []

else:
    # -------------------------------
    # STEP 4: PROMPT EVOLUTION
    # -------------------------------
    print("\n==== STARTING PROMPT EVOLUTION ====")

    optimizer_model = get_model(OPTIMIZER_MODEL_NAME)

    evolution_history = evolve_prompt(
        initial_prompt=base_prompt_def["template"],
        base_output=best_run.output,
        constraints=base_prompt_def["constraints"],
        optimizer_model=optimizer_model,
        eval_model=optimizer_model,
        max_iters=MAX_EVOLUTION_ITERS,
        variants_per_iter=VARIANTS_PER_ITER,
        min_delta=MIN_DELTA
    )

    print("\n==== PROMPT EVOLUTION TRACE ====")

    for step in evolution_history:
        print(f"\nIteration {step['iteration']}")
        print("Score:", step["score"])
        print("Breakdown:", step["breakdown"])
        print("Prompt:\n", step["prompt"])

    final_prompt = evolution_history[-1]["prompt"]


# -------------------------------
# STEP 5: FINAL MULTI-MODEL EVALUATION
# -------------------------------
print("\n==== FINAL PROMPT EVALUATION ====")

final_prompt_text = render_prompt(
    final_prompt,
    {"text": INPUT_TEXT}
)

final_results = executor.run(
    prompt=final_prompt_text,
    params=base_prompt_def["constraints"],
    models=FINAL_RUN_MODELS
)

for iteration, r in enumerate(final_results, start=1):
    eval_result = evaluate(r.output, base_prompt_def["constraints"])

    run_id = save_run(
        prompt_id=prompt_id,
        iteration=iteration,
        failure_type=failure_type
    )

    save_evaluation(
        run_id=run_id,
        model=r.model,
        eval_result=eval_result,
        latency_ms=r.latency_ms,
        output=r.output
    )

    print("\nMODEL:", r.model)
    print("SCORE:", eval_result.score)
    print("LATENCY (ms):", r.latency_ms)
    print("BREAKDOWN:", eval_result.breakdown)
    print("OUTPUT:\n", r.output)


print("\n==== DONE ====")
