from dataclasses import dataclass
from typing import Dict

@dataclass
class EvaluationResult:
    score: float
    breakdown: Dict[str, float]
    passed: bool
