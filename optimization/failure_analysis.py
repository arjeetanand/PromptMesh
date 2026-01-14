from typing import Dict

def analyze_failure(evaluation_breakdown: dict) -> str:
    if evaluation_breakdown["hallucination"] > 3:
        return "hallucination"
    if evaluation_breakdown["accuracy"] < 7:
        return "accuracy_loss"
    if evaluation_breakdown["completeness"] < 7:
        return "missing_information"
    if evaluation_breakdown["adherence"] < 7:
        return "instruction_violation"
    return "none"
