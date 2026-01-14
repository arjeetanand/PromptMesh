from dataclasses import dataclass

@dataclass
class ExecutionResult:
    model: str
    output: str
    tokens: int
    latency_ms: int
