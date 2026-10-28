import json
import re


FIELDS = ("organization", "year", "claim")


def _normalize_text(value):
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip().casefold().rstrip(".,;:")


def _parse_output(output):
    try:
        parsed = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != set(FIELDS):
        return None
    if any(value is not None and not isinstance(value, str) for key, value in parsed.items() if key != "year"):
        return None
    year = parsed["year"]
    if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1000 <= year <= 9999):
        return None
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
