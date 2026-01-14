from dataclasses import dataclass
from evaluation.types import EvaluationResult

@dataclass
class PromptRunResult:
    prompt_version: str
    model: str
    output: str
    evaluation: EvaluationResult
