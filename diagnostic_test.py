#!/usr/bin/env python3
"""
Diagnostic script to test judge evaluation independently
"""

import sys
from models.registry import get_model

# First, let's verify which judge.py is being loaded
import evaluation.judge
print(f"Loading judge from: {evaluation.judge.__file__}")
print("=" * 60)

from evaluation.judge import judge_output, extract_json

# Test the extract_json function directly first
print("\n" + "="*60)
print("TESTING extract_json FUNCTION")
print("="*60)

test_json_strings = [
    '{"accuracy": 8, "completeness": 7, "adherence": 9, "hallucination": 2}',
    '{\n  "accuracy": 8,\n  "completeness": 7,\n  "adherence": 9,\n  "hallucination": 2\n}',
]

for i, test_str in enumerate(test_json_strings, 1):
    print(f"\nTest {i}: {repr(test_str[:50])}")
    try:
        result = extract_json(test_str)
        print(f"✓ Parsed: {result}")
    except Exception as e:
        print(f"❌ Failed: {e}")

# Test the judge with a simple example
print("\n" + "="*60)
print("TESTING judge_output FUNCTION")
print("="*60)

source_text = "OpenAI released a new model in 2025. The announcement mentioned improvements over previous systems but did not provide specific metrics."

test_outputs = [
    # Good output
    "OpenAI released a new model in 2025 with improvements over previous systems, though specific metrics were not provided.",
    
    # Hallucinated output
    "OpenAI released GPT-5 in 2025, which is 10x faster and 95% more accurate than GPT-4.",
    
    # Empty output
    "",
    
    # Minimal output
    "New model released."
]

for i, output in enumerate(test_outputs, 1):
    print(f"\n--- Test Case {i} ---")
    print(f"Output: {output[:100]}")
    
    try:
        scores = judge_output(output, source_text)
        print(f"✓ Scores: {scores}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("Testing Model Execution")
print("="*60)

# Test basic model execution
model = get_model("llama3.2:latest")
print(f"\nModel: {model}")

test_prompt = "Say 'Hello World' and nothing else."
result = model.run(test_prompt, {"temperature": 0.0, "max_tokens": 50})

print(f"\nPrompt: {test_prompt}")
print(f"Output: {result['output']}")
print(f"Tokens: {result['tokens']}")
print(f"Latency: {result['latency_ms']}ms")

print("\n" + "="*60)
print("Testing Judge Model Directly")
print("="*60)

judge = get_model("command-a-03-2025")
print(f"Judge model: {judge}")

judge_prompt = """Return only this JSON:
{"accuracy": 8, "completeness": 7, "adherence": 9, "hallucination": 2}"""

result = judge.run(judge_prompt, {"temperature": 0.0, "max_tokens": 200})
print(f"\nJudge raw output:")
print(repr(result['output']))
print(f"\nJudge output (formatted):")
print(result['output'])

# Try to parse it
try:
    parsed = extract_json(result['output'])
    print(f"\n✓ Successfully parsed: {parsed}")
except Exception as e:
    print(f"\n❌ Failed to parse: {e}")

print("\n✓ Diagnostic complete")