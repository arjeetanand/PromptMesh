from optimization.meta_prompt import META_PROMPT
from models.registry import get_model
from models.constants import DEFAULT_OPTIMIZER_MODEL

optimizer = get_model(DEFAULT_OPTIMIZER_MODEL)


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
        response = optimizer.run(
            prompt=META_PROMPT.format(
                original_prompt=original_prompt,
                failure_type=failure_type,
                bad_output=bad_output
            )
            + f"\n\nRewrite variant #{i+1}.",
            params={
                "temperature": 0.4,   # allow diversity
                "max_tokens": 500
            }
        )

        variants.append(response["output"].strip())

    return variants
