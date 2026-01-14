from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.executor import PromptExecutor
from evaluation.scorer import evaluate

registry = PromptRegistry()
prompt_def = registry.load("summarization", "v1")

prompt_text = render_prompt(
    prompt_def["template"],
    {"text": "OpenAI released a new model in 2025 with improved reasoning."}
)

executor = PromptExecutor()


from comparison.runner import run_prompt_comparison
from comparison.ranker import rank_prompts

results = run_prompt_comparison(
    task="summarization",
    prompt_versions=["v1", "v2"],
    input_vars={
    "text": "OpenAI released a new model in 2025 that significantly improved reasoning and reduced hallucinations."
},
    # input_vars={"text": "..."},
    models=["command-a-03-2025"]
)


ranked = rank_prompts(results)

for r in ranked:
    print("\nPROMPT VERSION:", r.prompt_version)
    print("MODEL:", r.model)
    print("SCORE:", r.evaluation.score)
    print("BREAKDOWN:", r.evaluation.breakdown)
    print("OUTPUT:", r.output)


from optimization.failure_analysis import analyze_failure
from optimization.optimizer import generate_improved_prompt
from optimization.validator import validate_improvement

best = ranked[0]
failure_type = analyze_failure(best.evaluation.breakdown)

if failure_type != "none":
    best_prompt_def = registry.load("summarization", best.prompt_version)

    improved_prompt = generate_improved_prompt(
        original_prompt=best_prompt_def["template"],
        failure_type=failure_type,
        bad_output=best.output
    )

    print("\nSUGGESTED PROMPT IMPROVEMENT:\n")
    print(improved_prompt)




models = [
    # "llama3",
    # "mistral",
    # "qwen2.5",
    # "command-a-03-2025",
    "llama3",
    "qwen2.5",
    "llama3-8b"
    # "command-r-plus"
]


multi_results = executor.run(
    prompt=prompt_text,
    params=prompt_def["constraints"],
    models=models
)

print("\n==== MULTI-MODEL COMPARISON ====")

for r in multi_results:
    eval_result = evaluate(r.output, prompt_def["constraints"])

    print("\nMODEL:", r.model)
    print("SCORE:", eval_result.score)
    print("LATENCY:", r.latency_ms)
    print("BREAKDOWN:", eval_result.breakdown)
    print("OUTPUT:\n", r.output)
