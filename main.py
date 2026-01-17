# ===============================
# MAIN ENTRY — PROMPT PIPELINE
# ===============================

from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.executor import PromptExecutor
from evaluation.scorer import evaluate

from comparison.runner import run_prompt_comparison

from optimization.failure_analysis import analyze_failure
from optimization.evolver import evolve_prompt
from optimization.testcase_generator import generate_test_cases

from models.registry import get_model


# -------------------------------
# CONFIG
# -------------------------------

COMPARE_PROMPTS = False

TASK = "summarization"
PRIMARY_PROMPT_VERSION = "v6"
PROMPT_VERSIONS = ["v1", "v2"]

BASE_INPUTS = [
    "The study found a 23% reduction in symptoms after 6 weeks. "
    "Researchers noted this was preliminary data from a small sample of 50 participants. "
    "Further trials with 500 participants are planned for next year."
]

FAST_MODELS = [
    "llama3.2:latest",
]

MID_MODELS = [
    "qwen2.5:latest",
]

HEAVY_MODELS = [
    "gemma2:9b",
]

EVAL_MODELS = FAST_MODELS + MID_MODELS + HEAVY_MODELS

OPTIMIZER_MODEL_NAME = "command-a-03-2025"

MAX_EVOLUTION_ITERS = 3
VARIANTS_PER_ITER = 3
MIN_DELTA = 0.25


# -------------------------------
# INIT
# -------------------------------

registry = PromptRegistry()
executor = PromptExecutor()


# ============================================================
# MODE 1: PROMPT COMPARISON (OPTIONAL)
# ============================================================

if COMPARE_PROMPTS:

    print("\n==== PROMPT COMPARISON MODE ====")

    results = run_prompt_comparison(
        task=TASK,
        prompt_versions=PROMPT_VERSIONS,
        input_vars={"text": BASE_INPUTS[0]},
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
# MODE 2: SINGLE PROMPT → MULTI-MODEL → EVOLVE
# ============================================================

print("\n==== SINGLE PROMPT • MULTI-MODEL MODE ====")

# ---- Load YAML prompt ----
try:
    base_prompt_def = registry.load(TASK, PRIMARY_PROMPT_VERSION)
    print(f"✓ Loaded prompt: {TASK}/{PRIMARY_PROMPT_VERSION}")
except FileNotFoundError as e:
    print(f"\n❌ ERROR: {e}")
    print(f"\nCreate this file: prompts/versions/{TASK}/{PRIMARY_PROMPT_VERSION}.yaml")
    exit(1)

task_name = base_prompt_def["task"]
input_var_name = base_prompt_def["input_variables"][0]
base_prompt = base_prompt_def["template"]

# ---- Generate test cases (distribution) ----
print("\n" + "="*60)
print("GENERATING TEST CASES")
print("="*60)

test_inputs = generate_test_cases(
    task=task_name,
    input_variables=base_prompt_def["input_variables"],
    base_inputs=BASE_INPUTS,
    n=3
)

print(f"\n✓ Total test cases: {len(test_inputs)}")
for i, t in enumerate(test_inputs[:3], 1):
    print(f"  {i}. {t[:80]}...")

REPRESENTATIVE_INPUT = test_inputs[0]

# ---- Evaluate across all models ----
print("\n" + "="*60)
print("EVALUATING MODELS")
print("="*60)

results = []

for model_name in EVAL_MODELS:
    print(f"\n[{model_name}]")
    model = get_model(model_name)
    scores = []
    breakdowns = []

    for i, text in enumerate(test_inputs, 1):
        rendered = render_prompt(base_prompt, {input_var_name: text})
        
        print(f"  Test {i}/{len(test_inputs)}...", end=" ")
        
        try:
            raw = model.run(rendered, base_prompt_def["constraints"])
            
            print(f"Output: {raw['output'][:60]}...")
            
            eval_result = evaluate(
                raw["output"],
                base_prompt_def["constraints"],
                text
            )
            
            scores.append(eval_result.score)
            breakdowns.append(eval_result.breakdown)
            
            print(f"    Score: {eval_result.score}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            scores.append(0.0)
            breakdowns.append({"error": str(e)})

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    
    results.append({
        "model": model_name,
        "score": avg_score,
        "breakdowns": breakdowns
    })
    
    print(f"  Average score: {avg_score}")


# ---- Filter invalid / empty-output models ----
def is_valid_result(r):
    return all("reason" not in b and "error" not in b for b in r["breakdowns"])

valid_results = [r for r in results if is_valid_result(r)]

if not valid_results:
    print("\n❌ No valid models produced usable output.")
    print("\nAll results:")
    for r in results:
        print(f"  {r['model']}: {r['breakdowns'][:2]}")
    exit(1)

results = valid_results

# ---- Rank models ----
results = sorted(results, key=lambda x: x["score"], reverse=True)

print("\n" + "="*60)
print("MODEL LEADERBOARD")
print("="*60)

for i, r in enumerate(results, start=1):
    avg_halluc = round(
        sum(b.get("hallucination", 0) for b in r["breakdowns"]) / len(r["breakdowns"]),
        2
    )

    print(
        f"{i}. {r['model']:<18} "
        f"score={r['score']:<5} "
        f"avg_halluc={avg_halluc}"
    )


# ---- Select top model ----
top_model = results[0]
best_model_name = top_model["model"]

print("\n🏆 TOP MODEL SELECTED 🏆")
print("Model     :", best_model_name)
print("Score     :", top_model["score"])
print("Breakdowns:", top_model["breakdowns"][:2])


# ============================================================
# PROMPT EVOLUTION (DISTRIBUTION-AWARE)
# ============================================================

failure_type = analyze_failure(top_model["breakdowns"])
print(f"\nDetected failure type: {failure_type}")

# Only evolve if there's a real problem AND score is below threshold
if failure_type != "none" and top_model["score"] < 7.0:

    print("\n" + "="*60)
    print("STARTING PROMPT EVOLUTION")
    print("="*60)

    optimizer_model = get_model(OPTIMIZER_MODEL_NAME)
    execution_model = get_model(best_model_name)

    evolution_history = evolve_prompt(
        initial_prompt=base_prompt,
        task_inputs=test_inputs,
        constraints=base_prompt_def["constraints"],
        optimizer_model=optimizer_model,
        execution_model=execution_model,
        input_var=base_prompt_def["input_variables"][0],
        max_iters=MAX_EVOLUTION_ITERS,
        variants_per_iter=VARIANTS_PER_ITER,
        min_delta=MIN_DELTA
    )

    final_prompt = evolution_history[-1]["prompt"]
    
    print("\n" + "="*60)
    print("EVOLUTION COMPLETE")
    print("="*60)
    print(f"Initial score: {evolution_history[0]['score']}")
    print(f"Final score:   {evolution_history[-1]['score']}")
    print(f"Improvement:   +{evolution_history[-1]['score'] - evolution_history[0]['score']:.2f}")

else:
    if failure_type == "none":
        print("✓ No failures detected - prompt is working well.")
    else:
        print(f"✓ Score {top_model['score']} is acceptable despite {failure_type}.")
    final_prompt = base_prompt


# ============================================================
# FINAL RUN (TOP MODEL ONLY)
# ============================================================

print("\n" + "="*60)
print("FINAL MODEL RUN")
print("="*60)

final_prompt_text = render_prompt(
    final_prompt,
    {input_var_name: REPRESENTATIVE_INPUT}
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
    REPRESENTATIVE_INPUT
)

print("\nMODEL:", r.model)
print("FINAL SCORE:", final_eval.score)
print("BREAKDOWN:", final_eval.breakdown)
print("LATENCY (ms):", r.latency_ms)
print("OUTPUT:\n", r.output)

print("\n==== DONE ====")