from typing import Dict


def rule_checks(output: str, prompt_constraints: dict) -> Dict[str, bool]:
    checks = {}

    # Non-empty output
    checks["non_empty"] = bool(output and output.strip())

    # Max length (soft guard)
    max_tokens = prompt_constraints.get("max_tokens", None)
    if max_tokens:
        checks["length_ok"] = len(output.split()) < max_tokens * 1.2
    else:
        checks["length_ok"] = True

    return checks
