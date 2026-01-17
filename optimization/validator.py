# optimization/validator.py

from evaluation.scorer import evaluate

META_LEAK_PATTERNS = [
    "Observed failure type",
    "Problematic model output",
    "failure type:",
    "Rewrite variant",
    "Here is the revised",
    "Here's the revised",
    "Key changes:",
    "This version",
    "Changes made:",
]

LOCKED_LINES = []


def validate_prompt_structure(original: str, mutated: str) -> bool:
    """
    Validate that the mutated prompt is well-formed and safe.
    Returns True if valid, False if rejected.
    """
    
    original_lines = [l.strip() for l in original.splitlines() if l.strip()]
    mutated_lines = [l.strip() for l in mutated.splitlines() if l.strip()]
    
    # Debug info
    print(f"\n[VALIDATOR] Checking prompt:")
    print(f"  Original lines: {len(original_lines)}")
    print(f"  Mutated lines: {len(mutated_lines)}")
    
    # ❌ Reject if too short (likely truncated)
    if len(mutated_lines) < 3:
        print(f"  ❌ REJECT: Too few lines ({len(mutated_lines)})")
        return False
    
    # ❌ Reject meta-prompt leakage
    for bad in META_LEAK_PATTERNS:
        if bad.lower() in mutated.lower():
            print(f"  ❌ REJECT: Meta-leak detected: '{bad}'")
            return False
    
    # ❌ Locked safety constraints must not be removed
    for line in LOCKED_LINES:
        if line in original and line not in mutated:
            print(f"  ❌ REJECT: Removed locked line: '{line[:50]}'")
            return False
    
    # ⚠️ Warn but allow if length changed significantly (up to 50%)
    if len(mutated_lines) > len(original_lines) * 1.5:
        print(f"  ⚠️ WARNING: Prompt grew by {len(mutated_lines) - len(original_lines)} lines")
        # Don't reject, just warn
    
    # ❌ Reject if completely different structure (first line should be similar intent)
    if len(original_lines) > 0 and len(mutated_lines) > 0:
        # Check if first lines share some common words
        orig_words = set(original_lines[0].lower().split())
        mut_words = set(mutated_lines[0].lower().split())
        overlap = len(orig_words & mut_words)
        
        if overlap < 2:  # At least 2 words in common
            print(f"  ⚠️ WARNING: First line completely different (overlap: {overlap})")
            # Don't reject, just warn - sometimes rewrites are radical
    
    # ✅ Check for template variables ({{ text }}) if original had them
    if '{{' in original and '}}' in original:
        if '{{' not in mutated or '}}' not in mutated:
            print(f"  ❌ REJECT: Missing template variables")
            return False
    
    print(f"  ✅ ACCEPT: Prompt passed validation")
    return True