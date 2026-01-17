#!/usr/bin/env python3
"""
Test the JSON extraction function with various formats
"""

import re
import json

def extract_json(text: str) -> dict:
    """Extract JSON from model output with multiple fallback strategies."""
    
    # Remove markdown code blocks
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()
    
    # Strategy 1: Try to find complete JSON object with better regex
    match = re.search(r'\{[^}]*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Clean up the JSON string
        json_str = re.sub(r'\s+', ' ', json_str)
        try:
            parsed = json.loads(json_str)
            if all(k in parsed for k in ["accuracy", "completeness", "adherence", "hallucination"]):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Try parsing the entire text after cleaning
    try:
        cleaned = re.sub(r'\s+', ' ', text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Extract numbers using regex patterns
    try:
        patterns = {
            "accuracy": r'"accuracy"\s*:\s*(\d+)',
            "completeness": r'"completeness"\s*:\s*(\d+)',
            "adherence": r'"adherence"\s*:\s*(\d+)',
            "hallucination": r'"hallucination"\s*:\s*(\d+)'
        }
        
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                result[key] = int(match.group(1))
        
        if len(result) == 4:
            return result
            
    except (AttributeError, ValueError):
        pass
    
    # Strategy 4: Most aggressive cleaning
    try:
        ultra_clean = text.replace('\n', ' ').replace('\r', ' ')
        ultra_clean = re.sub(r'\s+', ' ', ultra_clean)
        return json.loads(ultra_clean)
    except json.JSONDecodeError:
        pass
    
    raise ValueError(f"No valid JSON found in: {text[:200]}")


# Test cases
test_cases = [
    # From diagnostic test - what the judge actually returns
    '{"accuracy": 8, "completeness": 7, "adherence": 9, "hallucination": 2}',
    
    # With newlines (the problematic one)
    '''{\n  "accuracy": 8,\n  "completeness": 7,\n  "adherence": 9,\n  "hallucination": 2\n}''',
    
    # With extra text
    '''Here is the JSON:
    {
      "accuracy": 8,
      "completeness": 7,
      "adherence": 9,
      "hallucination": 2
    }''',
    
    # In code block
    '''```json
    {"accuracy": 8, "completeness": 7, "adherence": 9, "hallucination": 2}
    ```''',
    
    # Mixed spacing
    '''{  "accuracy"  :  8  ,  "completeness"  :  7  ,  "adherence"  :  9  ,  "hallucination"  :  2  }''',
]

print("Testing JSON extraction:")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Input: {repr(test[:80])}")
    try:
        result = extract_json(test)
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("All tests complete!")