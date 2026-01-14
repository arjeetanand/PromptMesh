import time
import cohere
from models.base import BaseLLM

co = cohere.Client()  # Uses COHERE_API_KEY env var


class CohereModel(BaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, prompt: str, params: dict):
        start = time.time()

        response = co.chat(
            model=self.model_name,
            message=prompt,
            temperature=params.get("temperature", 0.0),
            max_tokens=params.get("max_tokens", 256)
        )

        latency = int((time.time() - start) * 1000)

        return {
            "output": response.text,
            "tokens": response.meta.tokens.input_tokens
                     + response.meta.tokens.output_tokens,
            "latency_ms": latency,
            "model": self.model_name
        }
