import time
import cohere
from functools import lru_cache
from models.base import BaseLLM
from core.security import MODEL_REQUEST_TIMEOUT_SECONDS


@lru_cache(maxsize=1)
def _get_client():
    return cohere.Client(timeout=MODEL_REQUEST_TIMEOUT_SECONDS)


class CohereModel(BaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, prompt: str, params: dict):
        start = time.time()

        response = _get_client().chat(
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
