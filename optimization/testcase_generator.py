"""
Intelligent Test Case Generator - Context-Aware
Analyzes user input and generates relevant, diverse test cases
"""
from models.registry import get_model
from typing import List, Optional
import json
import re

__all__ = ["generate_test_cases", "detect_task_type"]


# ============================================================
# INTELLIGENT GENERATION PROMPTS
# ============================================================

ANALYSIS_PROMPT = """Analyze this test input and identify:
1. Domain/topic (e.g., business, technology, health, etc.)
2. Key entities mentioned (companies, people, numbers, dates)
3. Complexity level (simple, moderate, complex)
4. Tone (formal, casual, technical)

Input: "{input_text}"

Return ONLY a JSON object:
{{
  "domain": "...",
  "entities": ["...", "..."],
  "complexity": "...",
  "tone": "..."
}}
"""

GENERATION_PROMPT = """You are generating test cases for evaluating an AI prompt.

TASK TYPE: {task_type}

USER'S ORIGINAL INPUT:
{original_input}

ANALYSIS:
- Domain: {domain}
- Complexity: {complexity}
- Entities: {entities}

YOUR TASK:
Generate {n} diverse test inputs that are SIMILAR to the original but cover different scenarios:

1. **Variation in complexity**: Generate some simpler and some more complex than original
2. **Variation in length**: Mix of short, medium, and longer texts
3. **Different entities**: Use different names, numbers, dates but same domain
4. **Edge cases**: Include boundary cases (very short, very long, ambiguous)
5. **Domain consistency**: Stay within the same domain as original

EXAMPLES for this task type:
{examples}

CRITICAL RULES:
- Each test case should be TESTABLE with the same prompt
- Maintain the same general format as original
- Vary the difficulty and scenarios
- Keep the same domain/topic as original
- Return ONLY a valid JSON array of strings
- No markdown, no explanation, no commentary

Format: ["test case 1", "test case 2", ...]
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_json(text: str):
    """Extract JSON from model output"""
    # Remove markdown
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass

    # Find JSON with regex
    patterns = [
        r'\{[^{}]*\}',  # Simple object
        r'\[[^\[\]]*\]',  # Simple array
        r'\{.*?\}',  # Complex object
        r'\[.*?\]'   # Complex array
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                continue

    # Extract quoted strings as array
    strings = re.findall(r'"([^"]+)"', text)
    if strings and len(strings) > 0:
        return strings

    return None


def analyze_input_context(input_text: str, model) -> dict:
    """Analyze the user's input to understand context"""
    try:
        print(f"[INFO] Analyzing input context...")
        prompt = ANALYSIS_PROMPT.format(input_text=input_text[:500])

        response = model.run(prompt, {"temperature": 0.3, "max_tokens": 200})
        output = response["output"]

        print(f"[DEBUG] Analysis output: {output[:200]}")

        analysis = extract_json(output)
        if isinstance(analysis, dict):
            return {
                "domain": analysis.get("domain", "general"),
                "entities": analysis.get("entities", []),
                "complexity": analysis.get("complexity", "moderate"),
                "tone": analysis.get("tone", "formal")
            }
    except Exception as e:
        print(f"[WARN] Context analysis failed: {e}")

    # Fallback: simple heuristic analysis
    return {
        "domain": "general",
        "entities": [],
        "complexity": "moderate" if len(input_text) > 100 else "simple",
        "tone": "formal"
    }


def generate_with_retries(model, prompt: str, max_retries: int = 2) -> List[str]:
    """Generate with multiple retries and fallback strategies"""
    for attempt in range(max_retries):
        try:
            temp = 0.7 + (attempt * 0.15)  # Increase temperature on retry
            response = model.run(prompt, {"temperature": temp, "max_tokens": 600})
            output = response["output"]

            print(f"[DEBUG] Attempt {attempt + 1} output: {output[:200]}...")

            # Try to extract array
            result = extract_json(output)

            if isinstance(result, list) and len(result) > 0:
                # Clean and validate
                cleaned = [
                    str(x).strip() 
                    for x in result 
                    if isinstance(x, str) and len(str(x).strip()) > 15
                ]
                if cleaned:
                    print(f"[SUCCESS] Generated {len(cleaned)} test cases")
                    return cleaned

        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1} failed: {e}")
            continue

    return []


# ============================================================
# MAIN FUNCTION
# ============================================================

def generate_test_cases(
    task_type: str,
    input_variables: List[str],
    base_inputs: List[str],
    schema_fields: Optional[List[str]] = None,
    n: int = 5
) -> List[str]:
    """
    Generate intelligent, context-aware test cases

    Strategy:
    1. Analyze the first base input to understand context
    2. Generate n-1 similar but varied test cases
    3. Return original + generated cases
    """
    print(f"\n{'='*80}")
    print(f"INTELLIGENT TEST CASE GENERATION")
    print(f"{'='*80}")
    print(f"Task type: {task_type}")
    print(f"Requested: {n} test cases")
    print(f"Base inputs provided: {len(base_inputs)}")

    # If we already have enough, return them
    if len(base_inputs) >= n:
        print(f"[INFO] Using provided base inputs (sufficient)")
        return base_inputs[:n]

    # Need to generate more
    needed = n - len(base_inputs)
    print(f"[INFO] Need to generate {needed} additional test cases")

    try:
        # Use a good model for generation
        model = get_model("command-a-03-2025")

        # Analyze the first input to understand context
        original_input = base_inputs[0]
        print(f"\n[INFO] Analyzing original input:\n{original_input[:200]}...\n")

        context = analyze_input_context(original_input, model)
        print(f"[INFO] Detected context: {context}")

        # Build examples from base inputs
        examples_text = "\n".join(f"{i+1}. {inp}" for i, inp in enumerate(base_inputs[:3]))

        # Create intelligent generation prompt
        prompt = GENERATION_PROMPT.format(
            task_type=task_type,
            original_input=original_input,
            domain=context["domain"],
            complexity=context["complexity"],
            entities=", ".join(context["entities"][:5]) if context["entities"] else "none",
            examples=examples_text,
            n=needed
        )

        print(f"\n[DEBUG] Generation prompt (first 400 chars):\n{prompt[:400]}...\n")

        # Generate with retries
        generated = generate_with_retries(model, prompt, max_retries=2)

        if not generated:
            print("[WARN] Generation failed completely, using smart fallback...")
            # Smart fallback: create variations of base inputs
            generated = create_smart_variations(base_inputs, needed, task_type)

        # Combine base + generated
        all_cases = base_inputs + generated[:needed]

        print(f"\n{'='*80}")
        print(f"FINAL RESULT: {len(all_cases)} test cases")
        print(f"{'='*80}")
        for i, case in enumerate(all_cases, 1):
            print(f"{i}. {case[:100]}{'...' if len(case) > 100 else ''}")
        print(f"{'='*80}\n")

        return all_cases

    except Exception as e:
        print(f"[ERROR] Test case generation failed: {e}")
        import traceback
        traceback.print_exc()

        # Final fallback
        print("[FALLBACK] Using base inputs with simple variations")
        return create_smart_variations(base_inputs, n, task_type)


def create_smart_variations(base_inputs: List[str], n: int, task_type: str) -> List[str]:
    """Create intelligent variations when LLM generation fails"""
    variations = list(base_inputs)

    # Simple transformation strategies based on task type
    transforms = {
        "summarization": [
            lambda x: x.replace(".", ". Additionally, recent developments suggest further changes."),
            lambda x: x.split(".")[0] + ".",  # Shorter version
            lambda x: x.replace("10%", "25%").replace("2023", "2024")  # Change numbers
        ],
        "extraction": [
            lambda x: x.replace("Google", "Amazon").replace("30%", "15%"),
            lambda x: x.replace("2022", "2023").replace("increased", "decreased"),
        ],
        "classification": [
            lambda x: x.replace("exceeded", "failed to meet").replace("outstanding", "poor"),
            lambda x: x + " However, improvements are expected.",
        ],
        "default": [
            lambda x: x.replace(".", ". Furthermore, analysis shows interesting patterns."),
            lambda x: x.split(".")[0] + ".",
        ]
    }

    transform_list = transforms.get(task_type, transforms["default"])

    # Apply transformations
    for base in base_inputs:
        if len(variations) >= n:
            break
        for transform in transform_list:
            if len(variations) >= n:
                break
            try:
                variation = transform(base)
                if variation != base and variation not in variations:
                    variations.append(variation)
            except:
                continue

    # If still not enough, duplicate with markers
    while len(variations) < n:
        for i, base in enumerate(base_inputs):
            if len(variations) >= n:
                break
            variations.append(f"{base} (Test scenario {len(variations) + 1})")

    return variations[:n]


def detect_task_type(prompt_template: str) -> str:
    """Auto-detect task type from prompt template"""
    prompt_lower = prompt_template.lower()

    keywords = {
        "summarization": ["summarize", "summary", "brief", "concise"],
        "extraction": ["extract", "find", "identify", "list"],
        "classification": ["classify", "categorize", "label", "category"],
        "verification": ["verify", "check", "fact", "claim", "true", "false"],
        "reasoning": ["reason", "infer", "conclude", "deduce", "analyze"],
        "generation": ["generate", "write", "create", "compose", "draft"]
    }

    scores = {}
    for task, words in keywords.items():
        scores[task] = sum(1 for word in words if word in prompt_lower)

    best_match = max(scores, key=scores.get)

    if scores[best_match] > 0:
        return best_match
    else:
        return "generation"  # Default