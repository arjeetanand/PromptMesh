from typing import List, Dict


FAILURE_TYPES = [
    "hallucination",
    "accuracy_loss",
    "missing_information",
    "instruction_violation"
]


def analyze_failure(breakdowns: list[dict]) -> str:
    if not breakdowns:
        return "none"

    weights = {
        "hallucination": 0,
        "accuracy_loss": 0,
        "missing_information": 0,
        "instruction_violation": 0
    }

    for b in breakdowns:
        halluc = b.get("hallucination", 0)
        acc = b.get("accuracy", 10)
        comp = b.get("completeness", 10)
        adher = b.get("adherence", 10)

        if halluc >= 5:
            weights["hallucination"] += 2
        elif halluc >= 3:
            weights["hallucination"] += 1

        if acc < 6:
            weights["accuracy_loss"] += 1

        if comp < 6:
            weights["missing_information"] += 1

        # Only count instruction violation if VERY low
        if adher <= 4:
            weights["instruction_violation"] += 1

    dominant = max(weights, key=weights.get)

    return dominant if weights[dominant] > 0 else "none"
