from typing import List
from core.result import ExecutionResult
from models.registry import get_model

class PromptExecutor:

    def run(
        self,
        prompt: str,
        params: dict,
        models: List[str]
    ) -> List[ExecutionResult]:

        results = []

        for model_name in models:
            model = get_model(model_name)
            raw = model.run(prompt, params)

            results.append(
                ExecutionResult(
                    model=raw["model"],
                    output=raw["output"],
                    tokens=raw["tokens"],
                    latency_ms=raw["latency_ms"]
                )
            )

        return results
