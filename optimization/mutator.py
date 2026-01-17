# optimization/mutator.py

from optimization.meta_prompt import META_PROMPT
from models.registry import get_model
from models.constants import DEFAULT_OPTIMIZER_MODEL
import re

optimizer = get_model(DEFAULT_OPTIMIZER_MODEL)


def clean_generated_prompt(text: str) -> str:
    """
    Extract the actual prompt from optimizer output.
    Remove meta-commentary, explanations, and formatting.
    """
    
    # Remove common prefixes
    text = re.sub(r'^(Here is|Here\'s|The revised prompt is:|Revised prompt:)\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove markdown code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'```', '', text)
    
    # Remove explanatory sections (common patterns)
    text = re.sub(r'\n\s*\*\*.*?\*\*.*$', '', text, flags=re.DOTALL)  # Remove **sections**
    text = re.sub(r'\n\s*##.*$', '', text, flags=re.DOTALL)  # Remove ## headers
    text = re.sub(r'\n\s*Changes made:.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\n\s*Key improvements:.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\n\s*This.*prompt.*$', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove meta-commentary at the end
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        # Stop if we hit meta-commentary
        if any(phrase in line.lower() for phrase in [
            'this version',
            'key change',
            'improvement',
            'note:',
            'explanation:',
            'the above',
            'this prompt'
        ]):
            break
        clean_lines.append(line)
    
    result = '\n'.join(clean_lines).strip()
    
    return result


def generate_prompt_variants(
    original_prompt: str,
    failure_type: str,
    bad_output: str,
    n: int = 5
) -> list[str]:
    """
    Generates N alternative prompt rewrites targeting the same failure.
    """

    variants = []

    for i in range(n):
        meta_instruction = META_PROMPT.format(
            original_prompt=original_prompt,
            failure_type=failure_type,
            bad_output=bad_output
        )
        
        full_prompt = (
            meta_instruction + 
            f"\n\nGenerate variant #{i+1}. "
            "Output ONLY the revised prompt text with no explanation, no preamble, no meta-commentary."
        )
        
        response = optimizer.run(
            prompt=full_prompt,
            params={
                "temperature": 0.4 + (i * 0.1),  # Increase diversity per variant
                "max_tokens": 600
            }
        )
        
        raw_output = response["output"].strip()
        cleaned = clean_generated_prompt(raw_output)
        
        print(f"\n[MUTATOR] Variant {i+1}:")
        print(f"  Raw length: {len(raw_output)}")
        print(f"  Clean length: {len(cleaned)}")
        print("\n----- MUTATED PROMPT START -----")
        print(cleaned)
        print("----- MUTATED PROMPT END -----\n")
        
        if len(cleaned) < 50:
            print(f"  ⚠️ Warning: Suspiciously short prompt, using raw")
            cleaned = raw_output
        
        variants.append(cleaned)

    return variants