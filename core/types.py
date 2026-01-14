from jinja2 import Template

def render_prompt(prompt_template: str, variables: dict) -> str:
    template = Template(prompt_template)
    return template.render(**variables)
