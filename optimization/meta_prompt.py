META_PROMPT = """
You are an expert prompt engineer.

Original prompt:
{original_prompt}

Observed failure type:
{failure_type}

Problematic model output:
{bad_output}

Rewrite the prompt to fix ONLY the failure.

Rules:
- Preserve structure
- Do NOT add new instructions
- Do NOT repeat constraints
- Modify the minimum necessary text

Do NOT:
- Add verbosity
- Change task scope
- Introduce new instructions unrelated to the failure

Return ONLY the revised prompt text.
"""
