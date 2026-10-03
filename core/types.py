import re

from core.security import MAX_PROMPT_CHARS, MAX_RENDERED_PROMPT_CHARS


_EXPRESSION = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
_VARIABLE = re.compile(r"\s*([A-Za-z][A-Za-z0-9_]*)\s*")
_UNSUPPORTED_JINJA = re.compile(r"\{%|\{#")

def render_prompt(prompt_template: str, variables: dict) -> str:
    """Render simple placeholders without interpreting template expressions."""
    if not isinstance(prompt_template, str) or len(prompt_template) > MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt templates must be at most {MAX_PROMPT_CHARS} characters")
    if _UNSUPPORTED_JINJA.search(prompt_template):
        raise ValueError("Only simple {{ variable }} prompt placeholders are supported")

    parts = []
    output_length = 0

    def append(value):
        nonlocal output_length
        output_length += len(value)
        if output_length > MAX_RENDERED_PROMPT_CHARS:
            raise ValueError(
                f"Rendered prompts must be at most {MAX_RENDERED_PROMPT_CHARS} characters"
            )
        parts.append(value)

    position = 0
    for match in _EXPRESSION.finditer(prompt_template):
        append(prompt_template[position:match.start()])
        variable = _VARIABLE.fullmatch(match.group(1))
        if variable is None:
            raise ValueError("Only simple {{ variable }} prompt placeholders are supported")
        name = variable.group(1)
        value = variables.get(name, "")
        if not isinstance(value, str):
            raise ValueError(f"Prompt variable '{name}' must be text")
        append(value)
        position = match.end()

    tail = prompt_template[position:]
    if "{{" in tail or "}}" in tail:
        raise ValueError("Only simple {{ variable }} prompt placeholders are supported")
    append(tail)
    return "".join(parts)
