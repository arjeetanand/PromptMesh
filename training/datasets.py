import hashlib
import json
import re
from pathlib import Path

from core.types import render_prompt


DATASET_DIR = Path(__file__).parent / "datasets"
MAX_DATASET_BYTES = 5 * 1024 * 1024
MAX_DATASET_ROWS = 1000
MAX_INPUT_CHARS = 4000
DATASET_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
OUTPUT_FIELDS = {"organization", "year", "claim"}


def dataset_path(dataset_id):
    if not isinstance(dataset_id, str) or not DATASET_ID_RE.fullmatch(dataset_id):
        raise ValueError("Dataset id is invalid")
    path = (DATASET_DIR / f"{dataset_id}.jsonl").resolve()
    if path.parent != DATASET_DIR.resolve():
        raise ValueError("Dataset path is invalid")
    return path


def load_dataset(dataset_id):
    path = dataset_path(dataset_id)
    size = path.stat().st_size
    if size > MAX_DATASET_BYTES:
        raise ValueError(f"Dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MB limit")

    rows = []
    seen_ids = set()
    seen_inputs = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if len(rows) >= MAX_DATASET_ROWS:
            raise ValueError(f"Dataset may contain at most {MAX_DATASET_ROWS} examples")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Line {line_number} is not valid JSON") from exc
        if not isinstance(row, dict) or set(row) != {"group_id", "input", "output"}:
            raise ValueError(f"Line {line_number} must contain only group_id, input, and output")

        group_id = row["group_id"]
        text = row["input"]
        output = row["output"]
        if not isinstance(group_id, str) or not group_id.strip() or len(group_id) > 128:
            raise ValueError(f"Line {line_number} has an invalid group_id")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_INPUT_CHARS:
            raise ValueError(f"Line {line_number} input must contain 1–{MAX_INPUT_CHARS} characters")
        if not isinstance(output, dict) or set(output) != OUTPUT_FIELDS:
            raise ValueError(f"Line {line_number} output must have organization, year, and claim fields")
        if any(value is not None and not isinstance(value, str) for key, value in output.items() if key != "year"):
            raise ValueError(f"Line {line_number} organization and claim values must be text or null")
        year = output["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1000 <= year <= 9999):
            raise ValueError(f"Line {line_number} year must be a four-digit integer or null")

        normalized = " ".join(text.split()).casefold()
        if normalized in seen_inputs:
            raise ValueError(f"Line {line_number} duplicates another input")
        seen_inputs.add(normalized)
        seen_ids.add(group_id)
        rows.append({"group_id": group_id.strip(), "input": text.strip(), "output": output})

    if len(rows) < 12:
        raise ValueError("Dataset needs at least 12 labeled examples")
    if len(seen_ids) < 12:
        raise ValueError("Dataset needs at least 12 distinct group_id values for a held-out split")
    return rows


def dataset_sha256(dataset_id):
    return hashlib.sha256(dataset_path(dataset_id).read_bytes()).hexdigest()


def split_dataset(rows, seed=42):
    groups = sorted({row["group_id"] for row in rows})
    if len(groups) < 12:
        raise ValueError("Dataset needs at least 12 distinct group_id values for a held-out split")

    groups.sort(key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
    validation_count = max(2, round(len(groups) * 0.15))
    test_count = max(2, round(len(groups) * 0.15))
    train_count = len(groups) - validation_count - test_count
    if train_count < 8:
        raise ValueError("Dataset needs at least 8 training groups and 2 groups per held-out split")

    train_groups = set(groups[:train_count])
    validation_groups = set(groups[train_count:train_count + validation_count])
    test_groups = set(groups[train_count + validation_count:])
    splits = {"train": [], "validation": [], "test": []}
    for row in rows:
        if row["group_id"] in train_groups:
            splits["train"].append(row)
        elif row["group_id"] in validation_groups:
            splits["validation"].append(row)
        else:
            splits["test"].append(row)
    return splits


def format_sft_rows(rows, prompt_template):
    formatted = []
    for row in rows:
        prompt = render_prompt(prompt_template, {"text": row["input"]})
        prompt += "\nReturn only a JSON object with exactly these keys: organization, year, claim. Use null for missing fields."
        completion = json.dumps(row["output"], ensure_ascii=False, sort_keys=True)
        formatted.append({
            "prompt": [{"role": "user", "content": prompt}],
            "completion": [{"role": "assistant", "content": completion}],
        })
    return formatted


def split_counts(splits):
    return {name: len(rows) for name, rows in splits.items()}


def list_datasets():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for path in sorted(DATASET_DIR.glob("*.jsonl")):
        dataset_id = path.stem
        try:
            rows = load_dataset(dataset_id)
            counts = split_counts(split_dataset(rows))
            result.append({
                "id": dataset_id,
                "examples": len(rows),
                "groups": len({row["group_id"] for row in rows}),
                "splits": counts,
                "sha256": dataset_sha256(dataset_id),
                "synthetic": dataset_id == "entity_extraction_demo",
            })
        except (OSError, ValueError) as exc:
            result.append({"id": dataset_id, "error": str(exc)})
    return result
