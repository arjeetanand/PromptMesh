import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from core.types import render_prompt


DATASET_DIR = Path(__file__).parent / "datasets"
MAX_DATASET_BYTES = 5 * 1024 * 1024
MAX_BENCHMARK_CARD_BYTES = 64 * 1024
MAX_DATASET_ROWS = 1000
MAX_INPUT_CHARS = 4000
MIN_FINAL_TEST_EXAMPLES = 30
MIN_FINAL_TEST_GROUPS = 10
DATASET_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
OUTPUT_FIELDS = {"organization", "year", "claim"}


def dataset_path(dataset_id):
    if not isinstance(dataset_id, str) or not DATASET_ID_RE.fullmatch(dataset_id):
        raise ValueError("Dataset id is invalid")
    path = (DATASET_DIR / f"{dataset_id}.jsonl").resolve()
    if path.parent != DATASET_DIR.resolve():
        raise ValueError("Dataset path is invalid")
    return path


def _parse_dataset(dataset_id, content):
    path = dataset_path(dataset_id)
    size = len(content)
    if size > MAX_DATASET_BYTES:
        raise ValueError(f"Dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MB limit")

    rows = []
    seen_ids = set()
    seen_inputs = set()
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
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


def load_dataset_snapshot(dataset_id):
    path = dataset_path(dataset_id)
    if path.stat().st_size > MAX_DATASET_BYTES:
        raise ValueError(f"Dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MB limit")
    content = path.read_bytes()
    return _parse_dataset(dataset_id, content), hashlib.sha256(content).hexdigest()


def load_dataset(dataset_id):
    return load_dataset_snapshot(dataset_id)[0]


def dataset_sha256(dataset_id):
    return load_dataset_snapshot(dataset_id)[1]


def _benchmark_card_path(dataset_id):
    dataset_path(dataset_id)
    path = (DATASET_DIR / f"{dataset_id}.card.json").resolve()
    if path.parent != DATASET_DIR.resolve():
        raise ValueError("Benchmark card path is invalid")
    return path


def _load_benchmark_card_snapshot(dataset_id, rows, dataset_digest):
    if dataset_id == "entity_extraction_demo":
        raise ValueError("The synthetic demo cannot be used as a final benchmark")
    path = _benchmark_card_path(dataset_id)
    if path.stat().st_size > MAX_BENCHMARK_CARD_BYTES:
        raise ValueError("Benchmark card exceeds the 64 KB limit")
    content = path.read_bytes()
    if len(content) > MAX_BENCHMARK_CARD_BYTES:
        raise ValueError("Benchmark card exceeds the 64 KB limit")
    try:
        card = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Benchmark card must be valid UTF-8 JSON") from exc

    expected_fields = {
        "schema_version", "dataset_id", "dataset_sha256", "task", "source", "grouping", "annotation", "limitations"
    }
    if not isinstance(card, dict) or set(card) != expected_fields:
        raise ValueError("Benchmark card fields do not match schema version 1")
    if type(card["schema_version"]) is not int or card["schema_version"] != 1 or card["dataset_id"] != dataset_id or card["task"] != "entity_extraction":
        raise ValueError("Benchmark card identity or schema version does not match the dataset")
    if not isinstance(card["dataset_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", card["dataset_sha256"]):
        raise ValueError("Benchmark card dataset_sha256 must be a 64-character SHA-256")
    if card["dataset_sha256"] != dataset_digest:
        raise ValueError("Benchmark card dataset_sha256 does not match the current dataset")

    def require_text(value, label):
        if not isinstance(value, str) or not value.strip() or "REPLACE_WITH" in value.upper():
            raise ValueError(f"Benchmark card {label} is required")

    source = card["source"]
    grouping = card["grouping"]
    annotation = card["annotation"]
    if not isinstance(source, dict) or not isinstance(grouping, dict) or not isinstance(annotation, dict):
        raise ValueError("Benchmark card source, grouping, and annotation must be objects")
    for key in ("description", "authorization_or_license"):
        require_text(source.get(key), f"source.{key}")
    for key in ("unit", "policy"):
        require_text(grouping.get(key), f"grouping.{key}")
    require_text(annotation.get("guidelines_version"), "annotation.guidelines_version")
    require_text(annotation.get("reviewer_role"), "annotation.reviewer_role")
    if annotation.get("review_status") != "human_reviewed" or annotation.get("all_labels_human_reviewed") is not True:
        raise ValueError("Benchmark card labels must be marked human-reviewed")

    groups = {row["group_id"] for row in rows}
    expected_counts = {
        "total_examples": len(rows),
        "reviewed_examples": len(rows),
        "total_source_groups": len(groups),
        "reviewed_source_groups": len(groups),
    }
    for key, expected in expected_counts.items():
        value = annotation.get(key)
        if type(value) is not int or value != expected:
            raise ValueError(f"Benchmark card {key} must equal {expected}")

    reviewed_at = annotation.get("reviewed_at_utc")
    if not isinstance(reviewed_at, str):
        raise ValueError("Benchmark card annotation.reviewed_at_utc is required")
    try:
        timestamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Benchmark card annotation.reviewed_at_utc must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Benchmark card annotation.reviewed_at_utc must include a timezone")

    limitations = card["limitations"]
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("Benchmark card must list known limitations")
    for limitation in limitations:
        require_text(limitation, "limitations")
    return card, hashlib.sha256(content).hexdigest()


def load_benchmark_card(dataset_id, rows=None, dataset_digest=None):
    if rows is None or dataset_digest is None:
        snapshot_rows, digest = load_dataset_snapshot(dataset_id)
        if rows is not None and rows != snapshot_rows:
            raise ValueError("Dataset changed while validating its benchmark card")
        rows, dataset_digest = snapshot_rows, digest
    return _load_benchmark_card_snapshot(dataset_id, rows, dataset_digest)[0]


def benchmark_card_status(dataset_id, rows=None, dataset_digest=None):
    if dataset_id == "entity_extraction_demo":
        return {
            "card_ready": False,
            "validation_ready": False,
            "final_test_ready": False,
            "status": "synthetic_only",
            "reason": "Synthetic demo data is not a final benchmark.",
        }
    if rows is None or dataset_digest is None:
        try:
            snapshot_rows, digest = load_dataset_snapshot(dataset_id)
        except FileNotFoundError:
            return {
                "card_ready": False,
                "validation_ready": False,
                "final_test_ready": False,
                "status": "missing_dataset",
                "reason": "The dataset file is missing.",
            }
        except (OSError, ValueError) as exc:
            return {
                "card_ready": False,
                "validation_ready": False,
                "final_test_ready": False,
                "status": "invalid_dataset",
                "reason": str(exc),
            }
        if rows is not None and rows != snapshot_rows:
            return {
                "card_ready": False,
                "validation_ready": False,
                "final_test_ready": False,
                "status": "invalid_dataset",
                "reason": "Dataset changed while validating its benchmark card",
            }
        rows, dataset_digest = snapshot_rows, digest
    try:
        card, card_hash = _load_benchmark_card_snapshot(dataset_id, rows, dataset_digest)
    except FileNotFoundError:
        return {
            "card_ready": False,
            "validation_ready": False,
            "final_test_ready": False,
            "status": "missing_card",
            "reason": "A human-review benchmark card is required.",
        }
    except (OSError, ValueError) as exc:
        return {
            "card_ready": False,
            "validation_ready": False,
            "final_test_ready": False,
            "status": "invalid_card",
            "reason": str(exc),
        }
    annotation = card["annotation"]
    splits = split_dataset(rows)
    validation = splits["validation"]
    final_test = splits["test"]
    validation_groups = len({row["group_id"] for row in validation})
    final_test_groups = len({row["group_id"] for row in final_test})
    validation_ready = (
        len(validation) >= MIN_FINAL_TEST_EXAMPLES
        and validation_groups >= MIN_FINAL_TEST_GROUPS
    )
    final_test_ready = (
        len(final_test) >= MIN_FINAL_TEST_EXAMPLES
        and final_test_groups >= MIN_FINAL_TEST_GROUPS
    )
    return {
        "card_ready": True,
        "validation_ready": validation_ready,
        "final_test_ready": final_test_ready,
        "status": "review_attested",
        "card_sha256": card_hash,
        "reviewed_examples": annotation["reviewed_examples"],
        "reviewed_source_groups": annotation["reviewed_source_groups"],
        "reviewed_at_utc": annotation["reviewed_at_utc"],
        "validation_examples": len(validation),
        "validation_source_groups": validation_groups,
        "final_test_examples": len(final_test),
        "final_test_source_groups": final_test_groups,
        "minimum_final_test_examples": MIN_FINAL_TEST_EXAMPLES,
        "minimum_final_test_groups": MIN_FINAL_TEST_GROUPS,
    }


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
            rows, digest = load_dataset_snapshot(dataset_id)
            counts = split_counts(split_dataset(rows))
            result.append({
                "id": dataset_id,
                "examples": len(rows),
                "groups": len({row["group_id"] for row in rows}),
                "splits": counts,
                "sha256": digest,
                "synthetic": dataset_id == "entity_extraction_demo",
                "benchmark": benchmark_card_status(dataset_id, rows, digest),
            })
        except (OSError, ValueError) as exc:
            result.append({"id": dataset_id, "error": str(exc)})
    return result
