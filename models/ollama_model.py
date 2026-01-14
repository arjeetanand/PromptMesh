import time
import ollama
from models.base import BaseLLM


class OllamaModel(BaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, prompt: str, params: dict):
        start = time.time()

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": params.get("temperature", 0.0),
                "num_predict": params.get("max_tokens", 256),
            }
        )

        latency = int((time.time() - start) * 1000)

        return {
            "output": response["message"]["content"],
            "tokens": response.get("eval_count", 0),
            "latency_ms": latency,
            "model": self.model_name
        }
