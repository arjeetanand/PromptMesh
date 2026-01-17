# optimization/testcase_generator.py

from models.registry import get_model
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


__all__ = [
    "generate_test_cases",
    "detect_task_type"
]


# -------------------------------
# TASK NORMALIZATION
# -------------------------------

TASK_NORMALIZATION_MAP = {
    "reasoning": "classification",
    "entity_extraction": "structured_output",
    "json_extraction": "structured_output",
    "extraction": "structured_output",
    "qa": "verification",
    "question_answering": "verification",
}


# -------------------------------
# GENERATOR TEMPLATES
# -------------------------------

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


# -------------------------------
# JSON ARRAY EXTRACTOR
# -------------------------------

def extract_json_list(text: str) -> list:

    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()

    match = re.search(r"\[.*\]", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


# -------------------------------
# TASK TYPE DETECTOR (CACHED)
# -------------------------------

TASK_CACHE = {}

def detect_task_type(prompt_text: str, model_name="qwen2.5:latest") -> str:

    if prompt_text in TASK_CACHE:
        return TASK_CACHE[prompt_text]

    detector_prompt = f"""
You are a classifier.

Classify the PROMPT TEMPLATE below into ONE category:

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
        params={"temperature": 0.0, "max_tokens": 40}
    )

    detected = response["output"].strip().lower()

    allowed = set(GENERATOR_TEMPLATES.keys())

    if detected not in allowed:
        print(f"[WARN] Unknown detected task type: {detected} → defaulting to classification")
        detected = "classification"

    TASK_CACHE[prompt_text] = detected

    print(f"[INFO] Auto-detected task type: {detected}")

    return detected


# -------------------------------
# PARALLEL GENERATOR
# -------------------------------

def parallel_generate(
    model,
    prompt: str,
    workers: int = 3,
    max_results: int = 12
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

    return results[:max_results]


# -------------------------------
# MAIN TESTCASE GENERATOR
# -------------------------------

def generate_test_cases(
    task_type: str,
    input_variables: list[str],
    base_inputs: list[str],
    schema_fields: list[str] | None = None,
    n: int = 6,
    model_name: str = "qwen2.5:latest"
):

    # Normalize task types
    task_type = TASK_NORMALIZATION_MAP.get(task_type, task_type)

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

    primary_var = input_variables[0] if input_variables else "text"

    prompt = template.format(
        n=n,
        fields=field_block
    )

    prompt += f"\n\nInput variable name: {primary_var}"

    prompt += "\n\nBase examples:\n"
    prompt += "\n".join(f"- {t}" for t in base_inputs)

    prompt += f"\n\nGenerate {n} NEW diverse examples as JSON array:"

    generated = parallel_generate(
        model=model,
        prompt=prompt,
        workers=3,
        max_results=n * 2
    )

    # Clean + dedupe
    generated = list(set([
        x.strip() for x in generated
        if isinstance(x, str) and len(x.strip()) > 10
    ]))

    print(f"[INFO] Base inputs: {len(base_inputs)}")
    print(f"[INFO] Generated inputs: {len(generated)}")

    if not generated:
        print("[WARN] Generator returned no new samples — using base inputs only")
        return base_inputs

    return base_inputs + generated[:n]
