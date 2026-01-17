# optimization/testcase_generator.py

from models.registry import get_model
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional


__all__ = [
    "generate_test_cases",
    "detect_task_type"
]


# ============================================================
# TASK NORMALIZATION LAYER
# ============================================================

TASK_NORMALIZATION_MAP = {
    "reasoning": "classification",
    "entity_extraction": "structured_output",
    "json_extraction": "structured_output",
    "extraction": "structured_output",
    "qa": "verification",
    "question_answering": "verification",
    "reasoning" : "reasoning",

    
}


# ============================================================
# GENERATOR PROMPT TEMPLATES
# ============================================================

GENERATOR_TEMPLATES = {

    "summarization": """
        Generate {n} diverse summarization input texts.

        Include:
        - dense paragraphs
        - contradictory information
        - short minimal content
        - multi-topic text
        - ambiguous statements
        - hallucination risk content

        Return ONLY a valid JSON array of strings.
        """,

    "structured_output": """
            You are generating INPUT TEXTS for structured information extraction.

            Target output fields:
            {fields}

            Generate {n} diverse input texts.

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

            Return ONLY a valid JSON array of strings.
            """,

    "reasoning": """
            Generate {n} ambiguous or underspecified input texts that require reasoning.

            Include:
            - vague statements
            - unclear references
            - missing actors
            - ambiguous pronouns
            - partial facts

            Rules:
            - Each item must be a standalone sentence
            - No explanations
            - No answers

            Return ONLY valid JSON array of strings.
            """,

    "classification": """
        Generate {n} classification input texts.

        Include:
        - clear category examples
        - borderline ambiguous cases
        - noisy informal language
        - mixed sentiment or intent

        Return ONLY a valid JSON array of strings.
        """,

    "verification": """
        You are generating INPUT TEXTS for fact verification.

        Each input MUST follow this EXACT format:

        Claim: <single factual claim>
        Source: <text that may or may not support the claim>

        Generate {n} diverse inputs.

        Distribution:
        - 40% clearly supported (exact wording or numeric match)
        - 30% clearly false
        - 20% underspecified
        - 10% partially overlapping facts

        Rules:
        - For supported cases, the claim MUST appear explicitly in the source
        - Match numbers exactly when used
        - Do NOT include answers
        - Do NOT explain
        - Each item must be a single string

        Return ONLY a valid JSON array of strings.

        """,

    "generation": """
        You are generating INPUT PROMPTS to test a content generation system.

        Your job is to produce realistic user prompts that someone would type into an AI assistant.

        Generate {n} diverse prompt strings.

        Include variety:
        - creative writing tasks
        - technical documentation requests
        - short-form content requests
        - long-form writing tasks
        - constrained instruction prompts
        - ambiguous or underspecified requests

        Rules:
        - Each item MUST be a single natural language prompt
        - Do NOT include answers
        - Do NOT number items
        - Do NOT use bullet points
        - Do NOT add explanations
        - Do NOT add markdown

        Output format rules:
        - Return ONLY a valid JSON array
        - Each array element MUST be a string

        Example output format:
        [
        "Write a short inspirational quote about teamwork.",
        "Generate a two-paragraph introduction for a cybersecurity blog.",
        "Create a product description for a wireless keyboard."
        ]

        If you cannot produce valid JSON, return [] only.
        """,

    # Universal fallback for unknown future tasks
    "universal": """
            You are generating INPUT TEXTS to test an AI prompt.

            Generate {n} realistic and diverse inputs that users would naturally provide.

            Rules:
            - Each item must be a single string
            - No numbering
            - No markdown
            - No explanations

            Return ONLY a valid JSON array of strings.

            Example:
            [
            "Explain the benefits of remote work.",
            "Summarize this article about renewable energy.",
            "Classify the sentiment of this sentence."
            ]

            If formatting fails return [].
            """,
}


# ============================================================
# JSON ARRAY EXTRACTION
# ============================================================

def extract_json_list(text: str) -> List[str]:
    """
    Safely extract JSON list from LLM output.
    """

    # Strip markdown blocks
    text = re.sub(r"```json\s*|\s*```", "", text, flags=re.IGNORECASE).strip()

    # Try to find array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # Fallback: try full parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return []


# ============================================================
# TASK TYPE AUTO-DETECTION (CACHED)
# ============================================================

TASK_CACHE = {}

def detect_task_type(prompt_text: str, model_name: str = "qwen2.5:latest") -> str:

    if prompt_text in TASK_CACHE:
        return TASK_CACHE[prompt_text]

    detector_prompt = f"""
You are a task classifier.

Classify the PROMPT TEMPLATE below into ONE category:

structured_output
summarization
classification
verification
generation

PROMPT TEMPLATE:
{prompt_text}

Return ONLY the task type string.
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


# ============================================================
# ADAPTIVE PROMPT BUILDER
# ============================================================

def build_adaptive_prompt(
    task_type: str,
    base_prompt_hint: str,
    input_vars: List[str],
    schema_fields: Optional[List[str]],
    n: int
) -> str:

    template = GENERATOR_TEMPLATES.get(task_type, GENERATOR_TEMPLATES["universal"])

    field_block = ""
    if schema_fields:
        field_block = "\n".join(f"- {f}" for f in schema_fields)

    input_var_block = "\n".join(f"- {v}" for v in input_vars)

    return template.format(
        n=n,
        fields=field_block,
        input_vars=input_var_block,
        task_hint=base_prompt_hint[:600]
    )


# ============================================================
# PARALLEL GENERATION ENGINE
# ============================================================

def parallel_generate(
    model,
    prompt: str,
    workers: int = 3,
    max_results: int = 12
) -> List[str]:

    results: List[str] = []

    def run_one():
        response = model.run(
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 1400
            }
        )

        raw = response["output"]

        if "[" not in raw:
            print("[WARN] Generator returned non-JSON output:")
            print(raw[:300])

        return extract_json_list(raw)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one) for _ in range(workers)]

        for future in as_completed(futures):
            try:
                batch = future.result(timeout=120)
                if isinstance(batch, list):
                    results.extend(batch)
            except Exception as e:
                print(f"[WARN] Generator worker failed: {e}")

            except TimeoutError:
                print("[WARN] Parallel generation timeout")


    return results[:max_results]


# ============================================================
# MAIN TESTCASE GENERATOR API
# ============================================================

def generate_test_cases(
        task_type: str,
        input_variables: List[str],
        base_inputs: List[str],
        schema_fields: Optional[List[str]] = None,
        n: int = 6,
        model_name: str = "qwen2.5:latest"
    ) -> List[str]:


    generated = [] 
    # Normalize task label
    task_type = TASK_NORMALIZATION_MAP.get(task_type, task_type)

    if task_type not in GENERATOR_TEMPLATES:
        print(f"[WARN] No generator template for {task_type} → using universal fallback")
        task_type = "universal"

    model = get_model(model_name)

    # Build adaptive generation prompt
    adaptive_prompt = build_adaptive_prompt(
        task_type=task_type,
        base_prompt_hint=" ".join(base_inputs[:2]),
        input_vars=input_variables,
        schema_fields=schema_fields,
        n=n
    )

    adaptive_prompt += "\n\nBase examples:\n"
    adaptive_prompt += "\n".join(f"- {x}" for x in base_inputs)

    adaptive_prompt += "\n\nIMPORTANT: Return ONLY a JSON array of strings."

    # First generation attempt
    raw = parallel_generate(
        model=model,
        prompt=adaptive_prompt,
        workers=3,
        max_results=n * 2
    )

    # Cleanup + dedupe
    cleaned = list(set([
        x.strip() for x in generated
        if isinstance(x, str) and len(x.strip()) > 10
    ]))

    generated = cleaned[:n]

    print(f"[INFO] Base inputs: {len(base_inputs)}")
    print(f"[INFO] Generated inputs: {len(generated)}")

    # Retry once if empty
    if not generated:
        print("[WARN] Empty generation result — retrying with stricter JSON enforcement")

        retry_prompt = adaptive_prompt + """

                STRICT MODE:
                - Output ONLY valid JSON
                - No markdown
                - No explanation
                - No commentary
                """

        generated = parallel_generate(
            model=model,
            prompt=retry_prompt,
            workers=2,
            max_results=n * 2
        )

        generated = list(set([
            x.strip() for x in generated
            if isinstance(x, str) and len(x.strip()) > 10
        ]))

    if not generated:
        print("[WARN] Generator failed — returning base inputs only")
        return base_inputs
    
    remaining = max(0, n - len(base_inputs))
    return base_inputs + generated[:remaining]



