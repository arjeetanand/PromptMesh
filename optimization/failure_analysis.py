from typing import Dict


# def analyze_failure(evaluation_breakdown: dict) -> str:
#     hallucination = evaluation_breakdown.get("hallucination", 10)
#     accuracy = evaluation_breakdown.get("accuracy", 0)
#     completeness = evaluation_breakdown.get("completeness", 0)
#     adherence = evaluation_breakdown.get("adherence", 0)

#     if hallucination > 3:
#         return "hallucination"
#     if accuracy < 7:
#         return "accuracy_loss"
#     if completeness < 7:
#         return "missing_information"
#     if adherence < 7:
#         return "instruction_violation"
#     return "none"


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
