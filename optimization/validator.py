from evaluation.scorer import evaluate

META_LEAK_PATTERNS = [
    "Observed failure type",
    "Problematic model output",
    "failure type:",
    "Rewrite variant",
]

LOCKED_LINES = [
    "Do not add new facts.",
    "Preserve key numbers and names.",
]


def validate_prompt_structure(original: str, mutated: str) -> bool:
    original_lines = [l.strip() for l in original.splitlines() if l.strip()]
    mutated_lines = [l.strip() for l in mutated.splitlines() if l.strip()]

    # ❌ Reject meta-prompt leakage
    for bad in META_LEAK_PATTERNS:
        if bad.lower() in mutated.lower():
            return False

    # ❌ Locked safety constraints must not be removed
    for line in LOCKED_LINES:
        if line in original and line not in mutated:
            return False

    # ❌ Must not grow more than 20%
    if len(mutated_lines) > len(original_lines) * 1.2:
        return False

    # ❌ Must preserve opening role
    if not mutated_lines[0].startswith(original_lines[0]):
        return False

    return True
