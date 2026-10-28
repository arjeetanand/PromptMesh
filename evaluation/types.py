from dataclasses import dataclass
from typing import Dict


class JudgeUnavailableError(RuntimeError):
    """Raised when an evaluation cannot get a valid response from its judge."""


@dataclass
class EvaluationResult:
    score: float
    breakdown: Dict[str, float | str]
    passed: bool
