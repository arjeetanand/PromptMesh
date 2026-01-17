META_PROMPT = """You are an expert prompt engineer tasked with fixing a problematic prompt.

ORIGINAL PROMPT:
{original_prompt}

DETECTED PROBLEM:
{failure_type}

YOUR TASK:
Rewrite the prompt to fix the {failure_type} issue while preserving the original task.

CRITICAL RULES:
1. Output ONLY the revised prompt - no explanations, no preamble
2. Do NOT add phrases like "Here is the revised prompt" or "Changes made:"
3. Do NOT include any meta-commentary about what you changed
4. Preserve the template variables (like {{{{ text }}}})
5. Keep the same overall structure and task intent
6. Only modify the parts that contribute to {failure_type}

SPECIFIC FIX FOR {failure_type}:
- hallucination: Add explicit instructions to ONLY use information from source, forbid adding external knowledge
- accuracy_loss: Strengthen requirements for factual precision and source fidelity
- missing_information: Emphasize completeness and coverage of key details
- instruction_violation: Make instructions clearer, more explicit, and unambiguous

Output the revised prompt now:"""