from abc import ABC, abstractmethod
from typing import Dict

class BaseLLM(ABC):

    @abstractmethod
    def run(self, prompt: str, params: Dict) -> Dict:
        """
        Returns:
        {
            "output": str,
            "tokens": int,
            "latency_ms": int,
            "model": str
        }
        """
        pass
