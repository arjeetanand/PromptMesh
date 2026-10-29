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
SPLIT_SEED = 42
GROUP_HASH_SPLIT = "group-hash-v1"
GROUP_YEAR_SPLIT = "group-year-stratified-v1"
YEAR_BALANCED_COHORT = "year-balanced-v1"
YEAR_BALANCED_COHORT_SEED = 42
YEAR_BALANCED_COHORT_YEARS = tuple(range(2020, 2026))
YEAR_BALANCED_COHORT_GROUPS_PER_YEAR = 12
# shortcut: fewer than 30 groups use hash splits; lower the cutoff only when small benchmark strata are useful.
YEAR_STRATIFIED_MIN_GROUPS = 30
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


def select_year_balanced_groups(candidate_group_years):
    """Select the fixed 12-per-year pilot cohort from reviewed group years."""
    if not isinstance(candidate_group_years, dict):
        raise ValueError("Balanced cohort candidates must map source groups to reviewed years")
    for group_id, year in candidate_group_years.items():
        if not isinstance(group_id, str) or not group_id.strip() or len(group_id) > 128:
            raise ValueError("Balanced cohort candidates contain an invalid source group")
        if year is not None and (type(year) is not int or not 1000 <= year <= 9999):
            raise ValueError("Balanced cohort candidate years must be four-digit integers or null")

    selected = []
    for year in YEAR_BALANCED_COHORT_YEARS:
        candidates = [group_id for group_id, candidate_year in candidate_group_years.items() if candidate_year == year]
        if len(candidates) < YEAR_BALANCED_COHORT_GROUPS_PER_YEAR:
            raise ValueError(
                f"Year {year} has {len(candidates)} eligible groups; "
                f"the pilot needs {YEAR_BALANCED_COHORT_GROUPS_PER_YEAR}"
            )
        ranked = sorted(
            candidates,
            key=lambda group_id: (
                hashlib.sha256(
                    f"{YEAR_BALANCED_COHORT_SEED}:{YEAR_BALANCED_COHORT}:{year}:{group_id}".encode("utf-8")
                ).hexdigest(),
                group_id,
            ),
        )
        selected.extend(ranked[:YEAR_BALANCED_COHORT_GROUPS_PER_YEAR])
    return selected


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

    schema_one_fields = {
        "schema_version", "dataset_id", "dataset_sha256", "task", "source", "grouping", "annotation", "limitations"
    }
    if not isinstance(card, dict) or type(card.get("schema_version")) is not int:
        raise ValueError("Benchmark card must be an object with a supported schema version")
    schema_version = card["schema_version"]
    expected_fields = schema_one_fields | ({"cohort"} if schema_version == 2 else set())
    if schema_version not in {1, 2} or set(card) != expected_fields:
        raise ValueError("Benchmark card fields do not match its schema version")
    if card["dataset_id"] != dataset_id or card["task"] != "entity_extraction":
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

    if schema_version == 2:
        cohort = card["cohort"]
        cohort_fields = {
            "strategy", "seed", "groups_per_year", "years", "candidate_group_years", "selected_group_ids"
        }
        if not isinstance(cohort, dict) or set(cohort) != cohort_fields:
            raise ValueError("Balanced cohort metadata does not match schema version 2")
        if (
            cohort["strategy"] != YEAR_BALANCED_COHORT
            or type(cohort["seed"]) is not int
            or cohort["seed"] != YEAR_BALANCED_COHORT_SEED
            or type(cohort["groups_per_year"]) is not int
            or cohort["groups_per_year"] != YEAR_BALANCED_COHORT_GROUPS_PER_YEAR
            or cohort["years"] != list(YEAR_BALANCED_COHORT_YEARS)
        ):
            raise ValueError("Balanced cohort strategy, seed, years, or group target is unsupported")
        candidates = cohort["candidate_group_years"]
        if not isinstance(candidates, list):
            raise ValueError("Balanced cohort candidate group years must be a list")
        candidate_group_years = {}
        for item in candidates:
            if not isinstance(item, dict) or set(item) != {"group_id", "year"}:
                raise ValueError("Balanced cohort candidate group metadata is malformed")
            group_id = item["group_id"]
            if not isinstance(group_id, str) or group_id in candidate_group_years:
                raise ValueError("Balanced cohort candidate group IDs must be unique text")
            candidate_group_years[group_id] = item["year"]
        if list(candidate_group_years) != sorted(candidate_group_years):
            raise ValueError("Balanced cohort candidate group metadata must be sorted by group ID")
        selected_group_ids = cohort["selected_group_ids"]
        if (
            not isinstance(selected_group_ids, list)
            or any(not isinstance(group_id, str) for group_id in selected_group_ids)
            or len(selected_group_ids) != len(set(selected_group_ids))
        ):
            raise ValueError("Balanced cohort selected group IDs must be unique text values")
        expected_selected = select_year_balanced_groups(candidate_group_years)
        if selected_group_ids != expected_selected:
            raise ValueError("Balanced cohort selected groups do not match its candidate list and deterministic rule")
        if {row["group_id"] for row in rows} != set(selected_group_ids):
            raise ValueError("Balanced cohort selected groups do not match the dataset rows")
        for row in rows:
            if row["output"]["year"] != candidate_group_years[row["group_id"]]:
                raise ValueError("Balanced cohort reviewed years differ from the recorded cohort plan")
        references = source.get("references")
        if not isinstance(references, list):
            raise ValueError("Balanced cohort source references must list every selected group")
        reference_group_ids = [item.get("group_id") for item in references if isinstance(item, dict)]
        if (
            len(reference_group_ids) != len(references)
            or len(reference_group_ids) != len(set(reference_group_ids))
            or set(reference_group_ids) != set(selected_group_ids)
        ):
            raise ValueError("Balanced cohort source references do not match the selected groups")

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


def split_dataset(rows, seed=SPLIT_SEED):
    groups = sorted({row["group_id"] for row in rows})
    if len(groups) < 12:
        raise ValueError("Dataset needs at least 12 distinct group_id values for a held-out split")

    if split_strategy(rows) == GROUP_YEAR_SPLIT:
        strata = _group_year_strata(rows)
        ordered = {
            signature: sorted(group_ids, key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
            for signature, group_ids in strata.items()
            if len(group_ids) >= 3
        }
        validation_groups = {group_ids[0] for group_ids in ordered.values()}
        test_groups = {group_ids[1] for group_ids in ordered.values()}
        assigned = {
            "validation": {signature: 1 for signature in ordered},
            "test": {signature: 1 for signature in ordered},
        }
        remaining = {signature: group_ids[2:] for signature, group_ids in ordered.items()}
        target = max(2, len(ordered), round(len(groups) * 0.15))
        for name, split_groups in (("validation", validation_groups), ("test", test_groups)):
            while len(split_groups) < target:
                available = [signature for signature, group_ids in remaining.items() if group_ids]
                if not available:
                    break
                signature = max(
                    available,
                    key=lambda item: (
                        len(ordered[item]) * 0.15 - assigned[name][item],
                        hashlib.sha256(f"{seed}:{name}:{item}".encode()).hexdigest(),
                    ),
                )
                split_groups.add(remaining[signature].pop(0))
                assigned[name][signature] += 1
        train_groups = set(groups) - validation_groups - test_groups
    else:
        groups.sort(key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
        validation_count = max(2, round(len(groups) * 0.15))
        test_count = max(2, round(len(groups) * 0.15))
        train_count = len(groups) - validation_count - test_count
        if train_count < 8:
            raise ValueError("Dataset needs at least 8 training groups and 2 groups per held-out split")
        train_groups = set(groups[:train_count])
        validation_groups = set(groups[train_count:train_count + validation_count])
        test_groups = set(groups[train_count + validation_count:])

    if len(train_groups) < 8:
        raise ValueError("Dataset needs at least 8 training groups and 2 groups per held-out split")
    splits = {"train": [], "validation": [], "test": []}
    for row in rows:
        if row["group_id"] in train_groups:
            splits["train"].append(row)
        elif row["group_id"] in validation_groups:
            splits["validation"].append(row)
        else:
            splits["test"].append(row)
    return splits


def _group_year_strata(rows):
    years_by_group = {}
    for row in rows:
        years_by_group.setdefault(row["group_id"], set()).add(row["output"]["year"])
    strata = {}
    for group_id, years in years_by_group.items():
        signature = tuple(sorted(years, key=lambda year: -1 if year is None else year))
        strata.setdefault(signature, []).append(group_id)
    return strata


def split_strategy(rows):
    strata = _group_year_strata(rows)
    if len({row["group_id"] for row in rows}) >= YEAR_STRATIFIED_MIN_GROUPS and any(len(groups) >= 3 for groups in strata.values()):
        return GROUP_YEAR_SPLIT
    return GROUP_HASH_SPLIT


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
                "split_seed": SPLIT_SEED,
                "split_strategy": split_strategy(rows),
                "sha256": digest,
                "synthetic": dataset_id == "entity_extraction_demo",
                "benchmark": benchmark_card_status(dataset_id, rows, digest),
            })
        except (OSError, ValueError) as exc:
            result.append({"id": dataset_id, "error": str(exc)})
    return result
