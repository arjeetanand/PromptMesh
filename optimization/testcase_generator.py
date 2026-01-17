# optimization/testcase_generator.py

from models.registry import get_model
import json
import re

GENERATOR_PROMPTS = {
    "summarization": """
You are generating INPUT TEXTS to test a summarization prompt.

Generate {n} diverse input texts.
Each text should test a different failure mode:
- missing details
- ambiguity
- hallucination risk
- minimal content
- dense information
- conflicting statements

Return ONLY a JSON array of strings like this:
["text 1", "text 2", "text 3"]

Do NOT include summaries or explanations.
""",

    "verification": """
You are generating INPUT TEXTS to test a factual verification prompt.

Each input should contain:
- a factual claim
- a source text that may or may not support the claim

Some inputs MUST be:
- clearly supported
- clearly not supported
- ambiguous / underspecified

Generate {n} diverse input texts.
Do NOT include answers.
Return ONLY a JSON array of strings.
"""
}


def extract_json_list(text: str) -> list:
    """Extract JSON list from model output."""
    # Remove markdown code blocks
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    
    # Try to find JSON array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Try parsing entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    return []


def generate_test_cases(
    task: str,
    input_variables: list[str],
    base_inputs: list[str],
    n: int = 6,
    model_name: str = "qwen2.5:latest"
) -> list[str]:
    """
    Generates distribution-aware test cases for prompt evaluation.
    """
    
    if task not in GENERATOR_PROMPTS:
        print(f"[WARN] No test-case generator for task: {task}")
        print(f"[WARN] Returning base inputs only")
        return base_inputs

    model = get_model(model_name)

    prompt = (
        GENERATOR_PROMPTS[task].format(n=n)
        + "\n\nBase examples:\n"
        + "\n".join(f"- {t}" for t in base_inputs)
        + f"\n\nGenerate {n} NEW diverse examples as JSON array:"
    )

    print(f"\n[DEBUG] Generating {n} test cases using {model_name}...")
    
    try:
        response = model.run(
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 1000
            }
        )
        
        print(f"[DEBUG] Generator raw output:")
        print(response["output"][:500])
        print("-" * 40)
        
        generated = extract_json_list(response["output"])
        
        if not isinstance(generated, list):
            print(f"[WARN] Generated output is not a list: {type(generated)}")
            generated = []
        
        # Ensure all items are strings
        generated = [str(x) for x in generated if isinstance(x, str) and len(x) > 10]
        
        print(f"[DEBUG] ✓ Generated {len(generated)} valid test cases")
        
    except Exception as e:
        print(f"[ERROR] Test case generation failed: {e}")
        generated = []

    # Always include original inputs
    all_cases = base_inputs + generated
    print(f"[DEBUG] Total test cases: {len(all_cases)}")
    
    return all_cases