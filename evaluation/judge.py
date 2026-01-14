from models.registry import get_model
import json
from models.constants import DEFAULT_JUDGE_MODEL
judge = get_model(DEFAULT_JUDGE_MODEL)

JUDGE_PROMPT = """
You are a strict evaluator.

Score the assistant output from 0 to 10 on:
1. Accuracy
2. Completeness
3. Instruction adherence
4. Hallucination risk (higher is worse)

Return ONLY valid JSON:
{
  "accuracy": number,
  "completeness": number,
  "adherence": number,
  "hallucination": number
}
"""

def judge_output(output: str) -> dict:
    response = judge.run(
        prompt=f"{JUDGE_PROMPT}\n\nOUTPUT:\n{output}",
        params={"temperature": 0.0, "max_tokens": 300}
    )

    try:
        return json.loads(response["output"])
    except Exception:
        return {
            "accuracy": 0,
            "completeness": 0,
            "adherence": 0,
            "hallucination": 10
        }
