import yaml
from pathlib import Path

PROMPT_BASE_PATH = Path("prompts/versions")

class PromptRegistry:
    def __init__(self):
        self._cache = {}

    def load(self, task: str, version: str):
        key = f"{task}:{version}"
        if key in self._cache:
            return self._cache[key]

        path = PROMPT_BASE_PATH / task / f"{version}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")

        with open(path, "r") as f:
            prompt = yaml.safe_load(f)

        self._cache[key] = prompt
        return prompt
    
    def load_with_metadata(self, task: str, version: str) -> dict:
        prompt_def = self.load(task, version)

        metadata = {
            "task": prompt_def.get("task"),
            "task_type": prompt_def.get("task_type"),
            "input_variables": prompt_def.get("input_variables", []),
            "schema_fields": (
                prompt_def.get("output_schema", {})
                .get("fields", [])
            ),
            "constraints": prompt_def.get("constraints", {}),
            "template": prompt_def.get("template")
        }

        return metadata