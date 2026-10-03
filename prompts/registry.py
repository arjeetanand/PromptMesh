import yaml
import re
from pathlib import Path

PROMPT_BASE_PATH = Path(__file__).resolve().parent / "versions"
_TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_VERSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _contained_path(path: Path, root: Path) -> Path:
    """Resolve a candidate and reject paths, including symlinks, outside root."""
    root = root.resolve()
    candidate = path.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise FileNotFoundError("Prompt not found") from exc
    return candidate

class PromptRegistry:
    def __init__(self):
        self._cache = {}

    def task_directory(self, task: str) -> Path:
        if not isinstance(task, str) or not _TASK_ID.fullmatch(task):
            raise FileNotFoundError("Prompt task not found")
        return _contained_path(PROMPT_BASE_PATH / task, PROMPT_BASE_PATH)

    def list_versions(self, task: str):
        task_dir = self.task_directory(task)
        if not task_dir.is_dir():
            return []
        versions = []
        for candidate in task_dir.glob("*.y*ml"):
            try:
                resolved = _contained_path(candidate, PROMPT_BASE_PATH)
            except FileNotFoundError:
                continue
            if resolved.is_file():
                versions.append(candidate.stem)
        return sorted(versions)

    def load(self, task: str, version: str):
        if not isinstance(version, str) or not _VERSION_ID.fullmatch(version):
            raise FileNotFoundError("Prompt version not found")

        task_dir = self.task_directory(task)
        path = _contained_path(task_dir / f"{version}.yaml", PROMPT_BASE_PATH)
        key = str(path)
        if key in self._cache:
            return self._cache[key]

        if not path.is_file():
            raise FileNotFoundError("Prompt not found")

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
