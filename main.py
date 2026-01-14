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
from optimization.mutator import generate_prompt_variants
from optimization.selector import select_best_prompt
from optimization.evolver import evolve_prompt

from models.registry import get_model


# -------------------------------
# CONFIG
# -------------------------------
TASK = "summarization"
PROMPT_VERSIONS = ["v1", "v2"]
INPUT_TEXT = (
    "OpenAI released a new model in 2025 that significantly improved reasoning "
    "and reduced hallucinations."
)

EVAL_MODELS = [
    "llama3",
    # "mistral",
    "qwen2.5",
    "command-a-03-2025"
]

FINAL_RUN_MODELS = [
    "llama3-8b"
]

OPTIMIZER_MODEL_NAME = "command-a-03-2025"


# -------------------------------
# STEP 1: LOAD PROMPTS
# -------------------------------
registry = PromptRegistry()

print("\n==== LOADING PROMPTS ====")

executor = PromptExecutor()

results = run_prompt_comparison(
    task=TASK,
    prompt_versions=PROMPT_VERSIONS,
    input_vars={"text": INPUT_TEXT},
    models=EVAL_MODELS
)

ranked = rank_prompts(results)

best_run = ranked[0]

print("\n==== BEST INITIAL PROMPT ====")
print("Prompt version:", best_run.prompt_version)
print("Model:", best_run.model)
print("Score:", best_run.evaluation.score)
print("Breakdown:", best_run.evaluation.breakdown)
print("Output:\n", best_run.output)


# -------------------------------
# STEP 2: FAILURE ANALYSIS
# -------------------------------
failure_type = analyze_failure(best_run.evaluation.breakdown)

print("\nDetected failure type:", failure_type)

if failure_type == "none":
    print("Prompt is already optimal. Skipping evolution.")
    final_prompt = registry.load(TASK, best_run.prompt_version)["template"]

else:
    # -------------------------------
    # STEP 3: PROMPT EVOLUTION
    # -------------------------------
    print("\n==== STARTING PROMPT EVOLUTION ====")

    base_prompt_def = registry.load(TASK, best_run.prompt_version)
    optimizer_model = get_model(OPTIMIZER_MODEL_NAME)

    evolution_history = evolve_prompt(
        initial_prompt=base_prompt_def["template"],
        base_output=best_run.output,
        constraints=base_prompt_def["constraints"],
        optimizer_model=optimizer_model,
        max_iters=3,
        min_delta=0.25,
        variants_per_iter=3
    )

    print("\n==== PROMPT EVOLUTION TRACE ====")

    for step in evolution_history:
        print(f"\nIteration {step['iteration']}")
        print("Score:", step["score"])
        print("Breakdown:", step["breakdown"])
        print("Prompt:\n", step["prompt"])

    final_prompt = evolution_history[-1]["prompt"]


# -------------------------------
# STEP 4: FINAL MULTI-MODEL RUN
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

for r in final_results:
    eval_result = evaluate(r.output, base_prompt_def["constraints"])

    print("\nMODEL:", r.model)
    print("SCORE:", eval_result.score)
    print("LATENCY (ms):", r.latency_ms)
    print("BREAKDOWN:", eval_result.breakdown)
    print("OUTPUT:\n", r.output)


print("\n==== DONE ====")
