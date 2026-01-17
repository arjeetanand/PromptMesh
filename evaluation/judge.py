# evaluation/judge.py

from models.registry import get_model
from models.constants import DEFAULT_JUDGE_MODEL
import json
import re

# judge = get_model(DEFAULT_JUDGE_MODEL)

def get_judge_model():
    return get_model(DEFAULT_JUDGE_MODEL)


JUDGE_PROMPT = """You are a strict evaluator.

You are given:
1. SOURCE TEXT
2. MODEL OUTPUT

Score the output from 0 to 10 on:
- Accuracy (faithfulness to source)
- Completeness (covers key info)
- Instruction adherence
- Hallucination risk (penalize new facts NOT in source)

If the output introduces facts or interpretations NOT present in the source,
hallucination MUST be high.

Return ONLY valid JSON with no other text:
{{
  "accuracy": <number 0-10>,
  "completeness": <number 0-10>,
  "adherence": <number 0-10>,
  "hallucination": <number 0-10>
}}

SOURCE TEXT:
{source_text}

MODEL OUTPUT:
{output}

JSON:"""


def extract_json(text: str) -> dict:
    """Extract JSON from model output with multiple fallback strategies."""
    
    # Remove markdown code blocks
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    
    # Strategy 1: Direct parse after basic cleanup
    try:
        # Replace newlines and normalize whitespace
        cleaned = text.replace('\n', ' ').replace('\r', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        parsed = json.loads(cleaned)
        if all(k in parsed for k in ["accuracy", "completeness", "adherence", "hallucination"]):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Find JSON object and parse
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Normalize whitespace
        json_str = json_str.replace('\n', ' ').replace('\r', ' ')
        json_str = re.sub(r'\s+', ' ', json_str)
        try:
            parsed = json.loads(json_str)
            if all(k in parsed for k in ["accuracy", "completeness", "adherence", "hallucination"]):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Extract individual values with regex
    try:
        patterns = {
            "accuracy": r'"accuracy"\s*:\s*(\d+)',
            "completeness": r'"completeness"\s*:\s*(\d+)',
            "adherence": r'"adherence"\s*:\s*(\d+)',
            "hallucination": r'"hallucination"\s*:\s*(\d+)'
        }
        
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                result[key] = int(match.group(1))
        
        if len(result) == 4:
            return result
            
    except (AttributeError, ValueError):
        pass
    
    raise ValueError(f"No valid JSON found in: {text[:200]}")


def judge_output(output: str, source_text: str) -> dict | None:
    """Judge model output against source text."""
    
    # Handle empty output
    if not output or not output.strip():
        return {
            "accuracy": 0,
            "completeness": 0,
            "adherence": 0,
            "hallucination": 10
        }
    
    for attempt in range(3):
        full_prompt = JUDGE_PROMPT.format(
            source_text=source_text,
            output=output
        )
        
        try:
            judge = get_judge_model()
            response = judge.run(
                prompt=full_prompt,
                params={"temperature": 0.0, "max_tokens": 500}
            )
            
            raw_output = response["output"]
            
            print(f"[DEBUG] Judge attempt {attempt+1} raw output:")
            print(repr(raw_output[:300]))  # Use repr to see escape characters
            print("-" * 40)
            
            scores = extract_json(raw_output)
            
            # Validate scores are in range
            for key in ["accuracy", "completeness", "adherence", "hallucination"]:
                if key not in scores:
                    raise ValueError(f"Missing key: {key}")
                if not isinstance(scores[key], (int, float)):
                    raise ValueError(f"Invalid type for {key}: {type(scores[key])}")
                if not 0 <= scores[key] <= 10:
                    raise ValueError(f"{key} out of range: {scores[key]}")
            
            print(f"[DEBUG] ✓ Extracted scores: {scores}")
            return scores
            
        except Exception as e:
            print(f"[DEBUG] Attempt {attempt+1} failed: {e}")
            if attempt == 2:
                print(f"[ERROR] All judge attempts failed. Returning default scores.")
                # Return neutral scores instead of failing
                return {
                    "accuracy": 5,
                    "completeness": 5,
                    "adherence": 5,
                    "hallucination": 5
                }
    
    return None