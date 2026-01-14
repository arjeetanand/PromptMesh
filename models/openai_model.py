import time
from openai import OpenAI
from models.base import BaseLLM

client = OpenAI()

class OpenAIModel(BaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def run(self, prompt: str, params: dict):
        start = time.time()

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=params.get("temperature", 0.0),
            max_tokens=params.get("max_tokens", 256)
        )

        latency = int((time.time() - start) * 1000)

        return {
            "output": response.choices[0].message.content,
            "tokens": response.usage.total_tokens,
            "latency_ms": latency,
            "model": self.model_name
        }
