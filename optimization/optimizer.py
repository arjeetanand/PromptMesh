from optimization.meta_prompt import META_PROMPT
from models.registry import get_model
from models.constants import DEFAULT_OPTIMIZER_MODEL
optimizer_model = get_model(DEFAULT_OPTIMIZER_MODEL)


def generate_improved_prompt(
    original_prompt: str,
    failure_type: str,
    bad_output: str
) -> str:


    response = optimizer_model.run(
        prompt=META_PROMPT.format(
            original_prompt=original_prompt,
            failure_type=failure_type,
            bad_output=bad_output
        ),
        params={"temperature": 0.2, "max_tokens": 500}
    )

    return response["output"].strip()
