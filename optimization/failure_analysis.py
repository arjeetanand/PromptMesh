from typing import Dict


def analyze_failure(evaluation_breakdown: dict) -> str:
    hallucination = evaluation_breakdown.get("hallucination", 10)
    accuracy = evaluation_breakdown.get("accuracy", 0)
    completeness = evaluation_breakdown.get("completeness", 0)
    adherence = evaluation_breakdown.get("adherence", 0)

    if hallucination > 3:
        return "hallucination"
    if accuracy < 7:
        return "accuracy_loss"
    if completeness < 7:
        return "missing_information"
    if adherence < 7:
        return "instruction_violation"
    return "none"

# def analyze_failure(evaluation_breakdown: dict) -> str:
#     if "reason" in evaluation_breakdown:
#         return "judge_failed"

#     if evaluation_breakdown.get("hallucination", 0) > 3:
#         return "hallucination"
#     if evaluation_breakdown.get("accuracy", 10) < 7:
#         return "accuracy_loss"
#     if evaluation_breakdown.get("completeness", 10) < 7:
#         return "missing_information"
#     if evaluation_breakdown.get("adherence", 10) < 7:
#         return "instruction_violation"

#     return "none"

