from prompts.registry import PromptRegistry
from core.executor import PromptExecutor
from evaluation.scorer import evaluate
from comparison.types import PromptRunResult


def run_prompt_comparison(
    task: str,
    prompt_versions: list,
    input_vars: dict,
    models: list
):
    registry = PromptRegistry()
    executor = PromptExecutor()

    results = []

    for version in prompt_versions:
        prompt_def = registry.load(task, version)

        prompt_text = prompt_def["template"]
        from core.types import render_prompt
        prompt_text = render_prompt(prompt_text, input_vars)

        exec_results = executor.run(
            prompt=prompt_text,
            params=prompt_def["constraints"],
            models=models
        )

        for r in exec_results:
            evaluation = evaluate(r.output, prompt_def["constraints"])

            results.append(
                PromptRunResult(
                    prompt_version=version,
                    model=r.model,
                    output=r.output,
                    evaluation=evaluation
                )
            )

    return results
