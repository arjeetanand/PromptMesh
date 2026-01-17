from typing import Dict

def analyze_failure(breakdowns: list[dict]) -> str:
    counts = {
        "hallucination": 0,
        "accuracy_loss": 0,
        "missing_information": 0,
        "instruction_violation": 0
    }

    for b in breakdowns:
        if b.get("hallucination", 0) > 3:
            counts["hallucination"] += 1
        if b.get("accuracy", 10) < 7:
            counts["accuracy_loss"] += 1
        if b.get("completeness", 10) < 7:
            counts["missing_information"] += 1
        if b.get("adherence", 10) < 7:
            counts["instruction_violation"] += 1

    dominant = max(counts, key=counts.get)
    return dominant if counts[dominant] > 0 else "none"
