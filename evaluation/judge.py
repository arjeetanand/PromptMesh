# evaluation/judge.py

from models.registry import get_model
from models.constants import DEFAULT_JUDGE_MODEL
import json
import re

judge = get_model(DEFAULT_JUDGE_MODEL)

JUDGE_PROMPT = """
You are a strict evaluator.

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

Return ONLY valid JSON:
{
  "accuracy": number,
  "completeness": number,
  "adherence": number,
  "hallucination": number
}
"""


def extract_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found")
    return json.loads(match.group(0))


def judge_output(output: str, source_text: str) -> dict | None:
    for attempt in range(3):
        response = judge.run(
                prompt=f"{JUDGE_PROMPT}\n\nSOURCE TEXT:\n{source_text}\n\nMODEL OUTPUT:\n{output}",
                params={"temperature": 0.0, "max_tokens": 300}
            )

        try:
            return extract_json(response["output"])
        except Exception:
            if attempt == 2:
                return None
