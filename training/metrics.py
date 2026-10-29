import json
import re


FIELDS = ("organization", "year", "claim")


def _normalize_text(value):
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip().casefold().rstrip(".,;:")


def _parse_output_with_status(output):
    try:
        parsed = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return None, "invalid_json"
    if not isinstance(parsed, dict) or set(parsed) != set(FIELDS):
        return None, "invalid_schema"
    if any(value is not None and not isinstance(value, str) for key, value in parsed.items() if key != "year"):
        return None, "invalid_schema"
    year = parsed["year"]
    if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1000 <= year <= 9999):
        return None, "invalid_schema"
    return parsed, None


def _parse_output(output):
    parsed, _status = _parse_output_with_status(output)
    return parsed


def _is_exact_record(row, parsed):
    if parsed is None:
        return False
    for field in FIELDS:
        actual = parsed[field]
        expected = row["output"][field]
        matches = actual == expected if field == "year" else _normalize_text(actual) == _normalize_text(expected)
        if not matches:
            return False
    return True


def score_predictions(rows, predictions):
    if len(rows) != len(predictions) or not rows:
        raise ValueError("Predictions must match a non-empty held-out split")

    field_correct = {field: 0 for field in FIELDS}
    valid_json = 0
    exact_records = 0
    for row, output in zip(rows, predictions):
        parsed = _parse_output(output)
        if parsed is None:
            continue
        valid_json += 1
        for field in FIELDS:
            actual = parsed[field]
            expected = row["output"][field]
            if field == "year":
                match = actual == expected
            else:
                match = _normalize_text(actual) == _normalize_text(expected)
            field_correct[field] += int(match)
        exact_records += int(_is_exact_record(row, parsed))

    count = len(rows)
    field_accuracy = round(sum(field_correct.values()) / (count * len(FIELDS)), 4)
    return {
        "examples": count,
        "json_valid_rate": round(valid_json / count, 4),
        "record_exact_match": round(exact_records / count, 4),
        "field_accuracy": field_accuracy,
        "field_exact_match": {field: round(field_correct[field] / count, 4) for field in FIELDS},
    }


def failure_analysis(rows, predictions):
    """Return aggregate output failures without retaining example text or generations."""
    if len(rows) != len(predictions) or not rows:
        raise ValueError("Predictions must match a non-empty held-out split")

    def new_bucket():
        return {
            "examples": 0,
            "failed_examples": 0,
            "invalid_json_examples": 0,
            "invalid_schema_examples": 0,
            "field_mismatch_examples": {field: 0 for field in FIELDS},
            "source_groups": set(),
            "failed_source_groups": set(),
        }

    buckets = {"all": new_bucket()}
    for row, output in zip(rows, predictions):
        year = row["output"]["year"]
        year_key = str(year) if year is not None else "undated"
        if year_key not in buckets:
            buckets[year_key] = new_bucket()

        parsed, status = _parse_output_with_status(output)
        if parsed is None:
            mismatches = {field: 1 for field in FIELDS}
        else:
            mismatches = {
                field: int(
                    parsed[field] != row["output"][field]
                    if field == "year"
                    else _normalize_text(parsed[field]) != _normalize_text(row["output"][field])
                )
                for field in FIELDS
            }

        failed = status is not None or any(mismatches.values())
        for bucket in (buckets["all"], buckets[year_key]):
            bucket["examples"] += 1
            bucket["source_groups"].add(row["group_id"])
            bucket["failed_examples"] += int(failed)
            bucket["invalid_json_examples"] += int(status == "invalid_json")
            bucket["invalid_schema_examples"] += int(status == "invalid_schema")
            for field, mismatch in mismatches.items():
                bucket["field_mismatch_examples"][field] += mismatch
            if failed:
                bucket["failed_source_groups"].add(row["group_id"])

    def serialize(bucket):
        return {
            "examples": bucket["examples"],
            "source_groups": len(bucket["source_groups"]),
            "failed_examples": bucket["failed_examples"],
            "failed_source_groups": len(bucket["failed_source_groups"]),
            "invalid_json_examples": bucket["invalid_json_examples"],
            "invalid_schema_examples": bucket["invalid_schema_examples"],
            "field_mismatch_examples": bucket["field_mismatch_examples"],
        }

    years = sorted(
        (key for key in buckets if key != "all"),
        key=lambda value: (value == "undated", int(value) if value != "undated" else 0),
    )
    return {
        "method": "json-schema-and-field-mismatch-counts-v1",
        "raw_examples_saved": False,
        "field_mismatch_note": "Invalid JSON or schema outputs count as a mismatch for every field; counts can overlap.",
        **serialize(buckets["all"]),
        "by_gold_year": {year: serialize(buckets[year]) for year in years},
    }
