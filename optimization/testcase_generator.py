# optimization/testcase_generator.py

from models.registry import get_model
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


__all__ = [
    "generate_test_cases",
    "detect_task_type"
]


GENERATOR_TEMPLATES = {

"structured_output": """
You are generating INPUT TEXTS for structured information extraction.

Target fields:
{fields}

Generate {n} diverse inputs.

Include:
- missing fields
- ambiguous references
- multiple entities
- numeric values
- incomplete information
- hallucination traps (no explicit facts)
- unstructured sentences

Rules:
- Do NOT include outputs
- Do NOT explain
- Generate realistic text

Return ONLY JSON array of strings.
""",

"summarization": """
Generate {n} diverse summarization input texts.

Include:
- dense paragraphs
- contradictory information
- short minimal content
- multi-topic text
- ambiguous statements
- hallucination risk content

Return ONLY JSON array.
""",

"classification": """
Generate {n} classification inputs.

Include:
- clear category examples
- borderline ambiguous cases
- noisy informal language
- mixed sentiment or topics

Return ONLY JSON array.
""",

"verification": """
Generate {n} verification inputs.

Include:
- clearly supported claims
- clearly false claims
- partially supported
- underspecified claims

Do NOT include answers.

Return ONLY JSON array.
""",

"generation": """
Generate {n} content generation prompts.

Include:
- creative tasks
- technical writing tasks
- constrained instructions
- ambiguous requirements
- long-form and short-form prompts

Return ONLY JSON array.
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
    task_type: str,
    input_variables: list[str],
    base_inputs: list[str],
    schema_fields: list[str] | None = None,
    n: int = 6,
    model_name: str = "qwen2.5:latest"
):

    if task_type not in GENERATOR_TEMPLATES:
        raise ValueError(
            f"No generator registered for task_type={task_type}. "
            f"Available: {list(GENERATOR_TEMPLATES.keys())}"
        )

    model = get_model(model_name)

    template = GENERATOR_TEMPLATES[task_type]

    field_block = ""
    if schema_fields:
        field_block = "\n".join(f"- {f}" for f in schema_fields)

    prompt = template.format(
        n=n,
        fields=field_block
    )

    prompt += "\n\nBase examples:\n"
    prompt += "\n".join(f"- {t}" for t in base_inputs)

    prompt += f"\n\nGenerate {n} NEW diverse examples as JSON array:"

    # response = model.run(
    #     prompt=prompt,
    #     params={
    #         "temperature": 0.7,
    #         "max_tokens": 1200
    #     }
    # )

    # generated = extract_json_list(response["output"])

    generated = parallel_generate(
        model=model,
        prompt=prompt,
        workers=3
    )


    # generated = [
    #     x for x in generated
    #     if isinstance(x, str) and len(x) > 10
    # ]

    generated = list(set([
    x for x in generated
    if isinstance(x, str) and len(x) > 10
]))


    return base_inputs + generated


def detect_task_type(prompt_text: str, model_name="qwen2.5:latest") -> str:

    detector_prompt = f"""
You are a classifier.

Given the PROMPT TEMPLATE below, classify its task type into ONE of:

structured_output
summarization
classification
verification
generation

PROMPT TEMPLATE:
{prompt_text}

Return ONLY the task_type string.
"""

    model = get_model(model_name)

    response = model.run(
        prompt=detector_prompt,
        params={"temperature": 0.0, "max_tokens": 50}
    )

    detected = response["output"].strip().lower()

    allowed = {
        "structured_output",
        "summarization",
        "classification",
        "verification",
        "generation"
    }

    if detected not in allowed:
        print(f"[WARN] Unknown detected task type: {detected}")
        return "generation"

    print(f"[INFO] Auto-detected task type: {detected}")
    return detected


def parallel_generate(
    model,
    prompt: str,
    workers: int = 3
) -> list[str]:

    results = []

    def run_one():
        response = model.run(
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 1200
            }
        )
        return extract_json_list(response["output"])

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one) for _ in range(workers)]

        for f in as_completed(futures):
            try:
                batch = f.result()
                if isinstance(batch, list):
                    results.extend(batch)
            except Exception as e:
                print(f"[WARN] Parallel generator error: {e}")

    return results
