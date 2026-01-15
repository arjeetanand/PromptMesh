# ===============================
# MAIN ENTRY – PROMPT PIPELINE
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


# -------------------------------
# CONFIG
# -------------------------------

# ---- MODE SWITCH ----
COMPARE_PROMPTS = False   # True = old prompt-vs-prompt mode

TASK = "summarization"

PRIMARY_PROMPT_VERSION = "v2"      # used when COMPARE_PROMPTS = False
PROMPT_VERSIONS = ["v1", "v2"]     # used only when COMPARE_PROMPTS = True

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
}

TEST_NAME = "hallucination_trap"
INPUT_TEXT = TEST_CASES[TEST_NAME]

EVAL_TASK_INPUTS = {
    "baseline": TEST_CASES["baseline"],
    "hallucination_trap": TEST_CASES["hallucination_trap"],
}


FAST_MODELS = [
    "gemma3:1b",
    "llama3.2:latest",
]

MID_MODELS = [
    # "llama3:latest",
    "llama3:8b",
    # "qwen2.5:latest",
    # "mistral:latest",
]

HEAVY_MODELS = [
    "gemma2:9b",
    # "deepseek-r1:8b",
    # "llava:latest",
]

EVAL_MODELS = FAST_MODELS + MID_MODELS + HEAVY_MODELS



# OPTIMIZER_MODEL_NAME = "command-a-03-2025"
OPTIMIZER_MODEL_NAME = "deepseek-r1:8b"

MAX_EVOLUTION_ITERS = 3
VARIANTS_PER_ITER = 3
MIN_DELTA = 0.25


# -------------------------------
# INIT
# -------------------------------

registry = PromptRegistry()
executor = PromptExecutor()


# ============================================================
# MODE 1: PROMPT COMPARISON (OPTIONAL / RESEARCH MODE)
# ============================================================

if COMPARE_PROMPTS:

    print("\n==== PROMPT COMPARISON MODE ====")

    results = run_prompt_comparison(
        task=TASK,
        prompt_versions=PROMPT_VERSIONS,
        input_vars={"text": INPUT_TEXT},
        models=EVAL_MODELS
    )

    print("\n==== PROMPT COMPARISON RESULTS ====")

    best_overall = None

    for r in results:
        print("-" * 60)
        print(f"Prompt Version : {r.prompt_version}")
        print(f"Model          : {r.model}")
        print(f"Score          : {r.evaluation.score}")
        print(f"Breakdown      : {r.evaluation.breakdown}")
        print(f"Output:\n{r.output}")

        if best_overall is None or r.evaluation.score > best_overall.evaluation.score:
            best_overall = r

    print("\n🏆 BEST RESULT 🏆")
    print("Prompt :", best_overall.prompt_version)
    print("Model  :", best_overall.model)
    print("Score  :", best_overall.evaluation.score)

    print("\n==== DONE ====")
    exit(0)


# ============================================================
# MODE 2: SINGLE PROMPT → MULTI-MODEL → EVOLVE → FINAL RUN
# ============================================================

print("\n==== SINGLE PROMPT • MULTI-MODEL MODE ====")

# ---- Load base prompt ----
base_prompt_def = registry.load(TASK, PRIMARY_PROMPT_VERSION)
base_prompt = base_prompt_def["template"]

prompt_text = render_prompt(base_prompt, {"text": INPUT_TEXT})

# ---- Run prompt across all models ----
raw_results = executor.run(
    prompt=prompt_text,
    params=base_prompt_def["constraints"],
    models=EVAL_MODELS
)

results = []

for r in raw_results:
    eval_result = evaluate(
        r.output,
        base_prompt_def["constraints"],
        INPUT_TEXT
    )

    results.append({
        "model": r.model,
        "score": eval_result.score,
        "breakdown": eval_result.breakdown,
        "output": r.output,
        "latency": r.latency_ms
    })


results = [
    r for r in results
    if r["breakdown"].get("reason") != "empty_output"
]


# ---- Rank models ----
results = sorted(results, key=lambda x: x["score"], reverse=True)

print("\n==== MODEL LEADERBOARD ====")

for i, r in enumerate(results, start=1):
    print(
        f"{i}. {r['model']:<18} "
        f"score={r['score']:<4} "
        f"halluc={r['breakdown'].get('hallucination')}"
    )

# ---- Select top model ----
top_model = results[0]
best_model_name = top_model["model"]

print("\n🏆 TOP MODEL SELECTED 🏆")
print("Model     :", best_model_name)
print("Score     :", top_model["score"])
print("Breakdown :", top_model["breakdown"])


# ============================================================
# PROMPT EVOLUTION (ONLY FOR TOP MODEL)
# ============================================================

failure_type = analyze_failure(top_model["breakdown"])
print("\nDetected failure type:", failure_type)

if failure_type != "none":

    print("\n==== STARTING PROMPT EVOLUTION ====")

    optimizer_model = get_model(OPTIMIZER_MODEL_NAME)
    execution_model = get_model(best_model_name)

    evolution_history = evolve_prompt(
        initial_prompt=base_prompt,
        task_inputs=EVAL_TASK_INPUTS,
        constraints=base_prompt_def["constraints"],
        optimizer_model=optimizer_model,
        execution_model=execution_model,
        max_iters=MAX_EVOLUTION_ITERS,
        variants_per_iter=VARIANTS_PER_ITER,
        min_delta=MIN_DELTA
    )

    final_prompt = evolution_history[-1]["prompt"]

else:
    print("Prompt already optimal for top model.")
    final_prompt = base_prompt


# ============================================================
# FINAL RUN (TOP MODEL ONLY)
# ============================================================

print("\n==== FINAL MODEL RUN ====")

final_prompt_text = render_prompt(
    final_prompt,
    {"text": INPUT_TEXT}
)

final_results = executor.run(
    prompt=final_prompt_text,
    params=base_prompt_def["constraints"],
    models=[best_model_name]
)

r = final_results[0]

final_eval = evaluate(
    r.output,
    base_prompt_def["constraints"],
    INPUT_TEXT
)

print("\nMODEL:", r.model)
print("FINAL SCORE:", final_eval.score)
print("BREAKDOWN:", final_eval.breakdown)
print("LATENCY (ms):", r.latency_ms)
print("OUTPUT:\n", r.output)

print("\n==== DONE ====")
