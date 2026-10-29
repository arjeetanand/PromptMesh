"""Private, local-only review workflow for the public-source candidate packet."""

import csv
import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path


REVIEW_PACKET_DIR = Path(__file__).parent / "datasets" / "review_packets"
REVIEW_PACKET_PATH = REVIEW_PACKET_DIR / "public_candidate_review_20261028.csv"
MAX_PACKET_BYTES = 1_000_000
REQUIRED_COLUMNS = (
    "group_id", "input", "proposed_organization", "proposed_year", "proposed_claim",
    "review_status", "reviewed_organization", "reviewed_year", "reviewed_claim",
    "review_notes", "source_title", "source_url", "source_date", "reuse_status", "review_focus",
)
_WRITE_LOCK = threading.Lock()


def _validate_reuse_terms_url(value):
    if not value:
        return
    from training.datasets import source_host_from_url

    try:
        source_host_from_url(value)
    except ValueError as exc:
        raise ValueError("A source reuse terms link must be a valid HTTPS URL") from exc


def _read_rows():
    if REVIEW_PACKET_DIR.is_symlink() or REVIEW_PACKET_PATH.is_symlink():
        raise ValueError("The local review packet cannot be a symlink")
    if REVIEW_PACKET_PATH.stat().st_size > MAX_PACKET_BYTES:
        raise ValueError("The local review packet exceeds the 1 MB limit")

    try:
        with REVIEW_PACKET_PATH.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or any(
                column not in reader.fieldnames for column in REQUIRED_COLUMNS
            ):
                raise ValueError("The local review packet has an unsupported CSV header")
            fieldnames = list(reader.fieldnames)
            for optional_column in ("reuse_terms_url", "reuse_evidence"):
                if optional_column not in fieldnames:
                    fieldnames.append(optional_column)
            rows = []
            for index, row in enumerate(reader):
                if None in row or not row.get("group_id"):
                    raise ValueError("The local review packet contains a malformed row")
                normalized = {column: row.get(column, "") or "" for column in fieldnames}
                _validate_reuse_terms_url(normalized["reuse_terms_url"])
                normalized["row_index"] = index
                rows.append(normalized)
    except csv.Error as exc:
        raise ValueError("The local review packet is malformed CSV") from exc
    return fieldnames, rows


def _packet(rows):
    groups = {}
    for row in rows:
        group = groups.setdefault(row["group_id"], {
            "group_id": row["group_id"],
            "source_title": row["source_title"],
            "source_url": row["source_url"],
            "source_date": row["source_date"],
            "reuse_terms_url": row["reuse_terms_url"],
            "review_focus": row["review_focus"],
            "reuse_status": row["reuse_status"],
            "reuse_evidence": row["reuse_evidence"],
            "rows": [],
        })
        if group["reuse_status"] != row["reuse_status"] or group["reuse_evidence"] != row["reuse_evidence"]:
            raise ValueError("Source reuse decisions differ within a source group")
        group["rows"].append({
            key: row[key] for key in (
                "row_index", "input", "proposed_organization", "proposed_year", "proposed_claim",
                "review_status", "reviewed_organization", "reviewed_year", "reviewed_claim", "review_notes",
            )
        })

    group_rows = list(groups.values())
    for row in rows:
        group = groups[row["group_id"]]
        if any(
            group[key] != row[key]
            for key in ("source_title", "source_url", "source_date", "reuse_terms_url")
        ):
            raise ValueError("Source metadata differs within a source group")
    for group in group_rows:
        group["reviewed_rows"] = sum(row["review_status"] == "REVIEWED" for row in group["rows"])
        group["excluded_rows"] = sum(row["review_status"] == "EXCLUDED" for row in group["rows"])
        group["resolved_rows"] = group["reviewed_rows"] + group["excluded_rows"]
        group["eligible"] = (
            group["resolved_rows"] == len(group["rows"])
            and group["reviewed_rows"] > 0
            and group["reuse_status"] == "permission_confirmed"
            and bool(group["reuse_evidence"].strip())
        )

    total_rows = sum(len(group["rows"]) for group in group_rows)
    reviewed_rows = sum(group["reviewed_rows"] for group in group_rows)
    eligible_groups = sum(group["eligible"] for group in group_rows)
    eligible_group_ids = {group["group_id"] for group in group_rows if group["eligible"]}
    try:
        eligible_rows = _reviewed_dataset_rows(rows, eligible_group_ids)
        export_preview = _export_preview(eligible_rows)
    except (TypeError, ValueError) as exc:
        export_preview = {
            "ready": False,
            "examples": sum(row["group_id"] in eligible_group_ids and row["review_status"] == "REVIEWED" for row in rows),
            "source_groups": eligible_groups,
            "validation_examples": 0,
            "validation_source_groups": 0,
            "final_test_examples": 0,
            "final_test_source_groups": 0,
            "reason": f"Reviewed labels cannot be exported safely: {exc}",
        }
    balanced_export_preview = _balanced_export_preview(
        rows, [group for group in group_rows if group["eligible"]]
    )
    return {
        "total_rows": total_rows,
        "reviewed_rows": reviewed_rows,
        "excluded_rows": sum(group["excluded_rows"] for group in group_rows),
        "total_groups": len(group_rows),
        "reviewed_groups": sum(group["reviewed_rows"] == len(group["rows"]) for group in group_rows),
        "resolved_groups": sum(group["resolved_rows"] == len(group["rows"]) for group in group_rows),
        "eligible_groups": eligible_groups,
        "export_preview": export_preview,
        "balanced_export_preview": balanced_export_preview,
        "groups": group_rows,
    }


def _reviewed_dataset_rows(rows, eligible_group_ids):
    dataset_rows = []
    for row in rows:
        if row["group_id"] not in eligible_group_ids or row["review_status"] != "REVIEWED":
            continue
        raw_year = row["reviewed_year"].strip()
        try:
            year = int(raw_year) if raw_year else None
        except ValueError as exc:
            raise ValueError("A reviewed event year is not a four-digit integer") from exc
        dataset_rows.append({
            "group_id": row["group_id"],
            "input": row["input"],
            "output": {
                "organization": row["reviewed_organization"].strip() or None,
                "year": year,
                "claim": row["reviewed_claim"].strip() or None,
            },
        })
    return dataset_rows


def _export_preview(dataset_rows):
    from training import datasets

    groups = len({row["group_id"] for row in dataset_rows})
    preview = {
        "ready": False,
        "examples": len(dataset_rows),
        "source_groups": groups,
        "validation_examples": 0,
        "validation_source_groups": 0,
        "final_test_examples": 0,
        "final_test_source_groups": 0,
    }
    if groups < 12:
        preview["reason"] = f"Only {groups} export-eligible groups; at least 12 are needed before checking held-out split floors."
        return preview
    try:
        content = "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in dataset_rows
        ).encode("utf-8")
        validated_rows = datasets._parse_dataset("review_export_preview", content)
        splits = datasets.split_dataset(validated_rows)
    except (TypeError, ValueError) as exc:
        preview["reason"] = f"Reviewed rows cannot be exported safely: {exc}"
        return preview

    for name, target in (("validation", "validation"), ("test", "final_test")):
        split_rows = splits[name]
        preview[f"{target}_examples"] = len(split_rows)
        preview[f"{target}_source_groups"] = len({row["group_id"] for row in split_rows})
    preview["ready"] = all(
        preview[f"{split}_examples"] >= datasets.MIN_FINAL_TEST_EXAMPLES
        and preview[f"{split}_source_groups"] >= datasets.MIN_FINAL_TEST_GROUPS
        for split in ("validation", "final_test")
    )
    if not preview["ready"]:
        preview["reason"] = (
            "The reviewed split must contain at least "
            f"{datasets.MIN_FINAL_TEST_EXAMPLES} examples across {datasets.MIN_FINAL_TEST_GROUPS} source groups "
            "in both validation and final test."
        )
    return preview


def _reviewed_group_year(group):
    years = set()
    for row in group["rows"]:
        if row["review_status"] != "REVIEWED":
            continue
        raw_year = row["reviewed_year"].strip()
        if not raw_year:
            return None
        try:
            year = int(raw_year)
        except ValueError:
            return None
        years.add(year)
    if len(years) != 1:
        return None
    return next(iter(years))


def _balanced_export_preview(rows, eligible_groups):
    from training import datasets

    candidate_group_metadata = {}
    for group in eligible_groups:
        group_id = group["group_id"]
        try:
            source_host = datasets.source_host_from_url(group["source_url"])
        except ValueError as exc:
            return {
                "ready": False,
                "examples": 0,
                "source_groups": 0,
                "validation_examples": 0,
                "validation_source_groups": 0,
                "final_test_examples": 0,
                "final_test_source_groups": 0,
                "years": list(datasets.YEAR_BALANCED_COHORT_YEARS),
                "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR,
                "selected_group_ids": [],
                "reason": str(exc),
            }
        candidate_group_metadata[group_id] = {
            "year": _reviewed_group_year(group),
            "source_host": source_host,
            "source_url": group["source_url"],
        }
    candidate_group_years = {
        group_id: metadata["year"]
        for group_id, metadata in candidate_group_metadata.items()
    }
    selection_metadata = {
        group_id: {"year": metadata["year"], "source_host": metadata["source_host"]}
        for group_id, metadata in candidate_group_metadata.items()
    }
    candidate_counts = {
        str(year): sum(candidate_year == year for candidate_year in candidate_group_years.values())
        for year in datasets.YEAR_BALANCED_COHORT_YEARS
    }
    candidate_host_counts = {
        str(year): len({
            metadata["source_host"] for metadata in candidate_group_metadata.values()
            if metadata["year"] == year
        })
        for year in datasets.YEAR_BALANCED_COHORT_YEARS
    }
    preview = {
        "ready": False,
        "examples": 0,
        "source_groups": 0,
        "validation_examples": 0,
        "validation_source_groups": 0,
        "final_test_examples": 0,
        "final_test_source_groups": 0,
        "years": list(datasets.YEAR_BALANCED_COHORT_YEARS),
        "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR,
        "candidate_groups_by_year": candidate_counts,
        "candidate_source_hosts_by_year": candidate_host_counts,
        "selected_group_ids": [],
        "candidate_group_years": [
            {"group_id": group_id, "year": candidate_group_years[group_id]}
            for group_id in sorted(candidate_group_years)
        ],
        "candidate_group_metadata": [
            {"group_id": group_id, **candidate_group_metadata[group_id]}
            for group_id in sorted(candidate_group_metadata)
        ],
        "selected_source_hosts_by_year": {},
    }
    missing_years = [
        year for year in datasets.YEAR_BALANCED_COHORT_YEARS
        if candidate_counts[str(year)] < datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR
    ]
    if missing_years:
        required = datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR
        counts = ", ".join(
            f"{year}: {candidate_counts[str(year)]}/{required}"
            for year in datasets.YEAR_BALANCED_COHORT_YEARS
        )
        preview["reason"] = f"Balanced pilot needs {required} reviewed, rights-cleared groups per year (2020–2025). Current groups: {counts}."
        return preview
    try:
        selected_group_ids = datasets.select_year_host_diverse_groups(selection_metadata)
    except ValueError as exc:
        preview["reason"] = str(exc)
        return preview

    preview["selected_group_ids"] = selected_group_ids
    preview["selected_source_hosts_by_year"] = {
        str(year): len({
            candidate_group_metadata[group_id]["source_host"]
            for group_id in selected_group_ids
            if candidate_group_metadata[group_id]["year"] == year
        })
        for year in datasets.YEAR_BALANCED_COHORT_YEARS
    }
    selected_rows = _reviewed_dataset_rows(rows, set(selected_group_ids))
    split_preview = _export_preview(selected_rows)
    preview.update(split_preview)
    preview.update({
        "years": list(datasets.YEAR_BALANCED_COHORT_YEARS),
        "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR,
        "candidate_groups_by_year": candidate_counts,
        "candidate_source_hosts_by_year": candidate_host_counts,
        "selected_group_ids": selected_group_ids,
        "candidate_group_years": [
            {"group_id": group_id, "year": candidate_group_years[group_id]}
            for group_id in sorted(candidate_group_years)
        ],
        "candidate_group_metadata": [
            {"group_id": group_id, **candidate_group_metadata[group_id]}
            for group_id in sorted(candidate_group_metadata)
        ],
        "selected_source_hosts_by_year": preview["selected_source_hosts_by_year"],
    })
    return preview


def load_review_packet():
    with _WRITE_LOCK:
        _, rows = _read_rows()
    return _packet(rows)


def save_group_review(group_id, updates, reuse_status, reuse_evidence):
    if reuse_status not in {"permission_unconfirmed", "permission_confirmed", "excluded"}:
        raise ValueError("Choose a valid source reuse status")
    evidence = reuse_evidence.strip()
    if reuse_status == "permission_confirmed" and not evidence:
        raise ValueError("Add the source reuse permission or license evidence")
    if reuse_status == "excluded" and not evidence:
        raise ValueError("Add a reason for excluding this source")

    with _WRITE_LOCK:
        fieldnames, rows = _read_rows()
        matching = [row for row in rows if row["group_id"] == group_id]
        expected_indexes = {row["row_index"] for row in matching}
        submitted_indexes = [item["row_index"] for item in updates]
        if not matching or len(updates) != len(matching) or set(submitted_indexes) != expected_indexes:
            raise ValueError("The review rows do not match this source group")
        if len(set(submitted_indexes)) != len(submitted_indexes):
            raise ValueError("A review row was submitted more than once")

        update_by_index = {item["row_index"]: item for item in updates}
        for row in matching:
            update = update_by_index[row["row_index"]]
            status = update["review_status"]
            notes = update["review_notes"].strip()
            if status == "EXCLUDED" and not notes:
                raise ValueError("Add a reason before excluding a candidate row")
            row["review_status"] = status
            row["reviewed_organization"] = (update["reviewed_organization"] or "").strip()
            row["reviewed_year"] = "" if update["reviewed_year"] is None else str(update["reviewed_year"])
            row["reviewed_claim"] = (update["reviewed_claim"] or "").strip()
            row["review_notes"] = notes
            row["reuse_status"] = reuse_status
            row["reuse_evidence"] = evidence

        descriptor, temp_name = tempfile.mkstemp(prefix=".review-packet-", suffix=".tmp", dir=REVIEW_PACKET_DIR)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as destination:
                writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)
                destination.flush()
                os.fsync(destination.fileno())
            os.chmod(temp_name, REVIEW_PACKET_PATH.stat().st_mode & 0o777)
            os.replace(temp_name, REVIEW_PACKET_PATH)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

        return _packet(rows)


def export_reviewed_dataset(dataset_id, reviewer_role, cohort_mode="all_eligible"):
    from training import datasets

    if not isinstance(dataset_id, str) or not datasets.DATASET_ID_RE.fullmatch(dataset_id):
        raise ValueError("Dataset id is invalid")
    reviewer_role = reviewer_role.strip() if isinstance(reviewer_role, str) else ""
    if not reviewer_role or len(reviewer_role) > 128:
        raise ValueError("Add the reviewer role (not a personal name; maximum 128 characters)")
    if cohort_mode not in {"all_eligible", "balanced_year_12"}:
        raise ValueError("Choose a supported reviewed-dataset cohort")

    with _WRITE_LOCK:
        _, packet_rows = _read_rows()
        packet = _packet(packet_rows)
        preview_key = "balanced_export_preview" if cohort_mode == "balanced_year_12" else "export_preview"
        preview = packet[preview_key]
        if not preview["ready"]:
            raise ValueError(preview.get("reason") or "The reviewed packet is not ready for benchmark export")

        if cohort_mode == "balanced_year_12":
            selected_group_ids = list(preview["selected_group_ids"])
        else:
            selected_group_ids = [group["group_id"] for group in packet["groups"] if group["eligible"]]
        selected_group_id_set = set(selected_group_ids)
        rows = _reviewed_dataset_rows(packet_rows, selected_group_id_set)
        content = "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ).encode("utf-8")
        validated_rows = datasets._parse_dataset(dataset_id, content)
        digest = hashlib.sha256(content).hexdigest()
        splits = datasets.split_dataset(validated_rows)
        split_counts = {
            name: {
                "examples": len(split_rows),
                "source_groups": len({row["group_id"] for row in split_rows}),
            }
            for name, split_rows in splits.items()
        }

        data_dir = Path(datasets.DATASET_DIR)
        data_path = data_dir / f"{dataset_id}.jsonl"
        card_path = data_dir / f"{dataset_id}.card.json"
        if data_dir.is_symlink() or data_path.is_symlink() or card_path.is_symlink():
            raise ValueError("The reviewed dataset output path cannot be a symlink")
        if data_path.exists() or card_path.exists():
            raise FileExistsError("A dataset or benchmark card with this id already exists")

        included_groups = [group for group in packet["groups"] if group["group_id"] in selected_group_id_set]
        references = []
        for group in included_groups:
            references.append({
                "group_id": group["group_id"],
                "title": group["source_title"],
                "url": group["source_url"],
                "reuse_evidence": group["reuse_evidence"].strip(),
            })
        card = {
            "schema_version": 3 if cohort_mode == "balanced_year_12" else 1,
            "dataset_id": dataset_id,
            "dataset_sha256": digest,
            "task": "entity_extraction",
            "source": {
                "description": "Human-reviewed public-source entity-extraction examples.",
                "authorization_or_license": "Each included source group has a local human-confirmed reuse decision; source-level evidence is listed in references.",
                "references": references,
            },
            "grouping": {
                "unit": "one public source document or source fact per group_id",
                "policy": (
                    "Select 12 source groups per reviewed year (2020–2025), maximizing distinct normalized source hosts "
                    "with the deterministic SHA-256 year-host-diverse-v1 rule; choose one eligible group per host before "
                    "repeating hosts when possible, keep each group intact, and omit eligible groups outside the cohort."
                    if cohort_mode == "balanced_year_12"
                    else "Keep all included variants from one source fact in the same group; excluded variants are omitted."
                ),
            },
            "annotation": {
                "guidelines_version": "entity-extraction-v1",
                "review_status": "human_reviewed",
                "all_labels_human_reviewed": True,
                "total_examples": len(validated_rows),
                "reviewed_examples": len(validated_rows),
                "total_source_groups": len({row["group_id"] for row in validated_rows}),
                "reviewed_source_groups": len({row["group_id"] for row in validated_rows}),
                "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
                "reviewer_role": reviewer_role,
            },
            "limitations": [
                "Review and reuse decisions are local self-attestations, not independently audited.",
                "Paraphrases from a source are grouped and do not count as independent facts.",
                "Inspect source, topic, year, and writing-style coverage before generalizing results.",
            ],
        }
        if cohort_mode == "balanced_year_12":
            card["cohort"] = {
                "strategy": datasets.YEAR_HOST_DIVERSE_COHORT,
                "seed": datasets.YEAR_BALANCED_COHORT_SEED,
                "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR,
                "years": list(datasets.YEAR_BALANCED_COHORT_YEARS),
                "candidate_group_metadata": preview["candidate_group_metadata"],
                "selected_group_ids": selected_group_ids,
            }
        card_content = (json.dumps(card, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        if len(card_content) > datasets.MAX_BENCHMARK_CARD_BYTES:
            raise ValueError("The reviewed source references exceed the 64 KB benchmark-card limit")

        created_paths = []
        try:
            with tempfile.TemporaryDirectory(prefix=".reviewed-export-", dir=data_dir) as temporary_dir:
                temporary_dir = Path(temporary_dir)
                staged_data = temporary_dir / data_path.name
                staged_card = temporary_dir / card_path.name
                staged_data.write_bytes(content)
                staged_card.write_bytes(card_content)
                os.chmod(staged_data, 0o600)
                os.chmod(staged_card, 0o600)
                os.link(staged_data, data_path)
                created_paths.append(data_path)
                os.link(staged_card, card_path)
                created_paths.append(card_path)
        except Exception:
            for path in reversed(created_paths):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            raise

        try:
            status = datasets.benchmark_card_status(dataset_id, validated_rows, digest)
            if not status["card_ready"] or not status["validation_ready"] or not status["final_test_ready"]:
                raise ValueError(status.get("reason") or "The generated dataset did not pass benchmark readiness checks")
        except Exception:
            for path in reversed(created_paths):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            raise

        selected_groups_by_year = {}
        selected_source_hosts_by_year = {}
        if cohort_mode == "balanced_year_12":
            year_by_group = {
                item["group_id"]: item
                for item in preview["candidate_group_metadata"]
            }
            selected_groups_by_year = {
                str(year): sum(year_by_group[group_id]["year"] == year for group_id in selected_group_ids)
                for year in datasets.YEAR_BALANCED_COHORT_YEARS
            }
            selected_source_hosts_by_year = {
                str(year): len({
                    year_by_group[group_id]["source_host"]
                    for group_id in selected_group_ids
                    if year_by_group[group_id]["year"] == year
                })
                for year in datasets.YEAR_BALANCED_COHORT_YEARS
            }
        return {
            "dataset_id": dataset_id,
            "dataset_sha256": digest,
            "benchmark_card_sha256": status["card_sha256"],
            "examples": len(validated_rows),
            "source_groups": len({row["group_id"] for row in validated_rows}),
            "cohort": {
                "mode": cohort_mode,
                "groups_per_year": datasets.YEAR_BALANCED_COHORT_GROUPS_PER_YEAR if cohort_mode == "balanced_year_12" else None,
                "selected_groups_by_year": selected_groups_by_year,
                "selected_source_hosts_by_year": selected_source_hosts_by_year,
                "selection_seed": datasets.YEAR_BALANCED_COHORT_SEED if cohort_mode == "balanced_year_12" else None,
            },
            "splits": split_counts,
            "benchmark": status,
        }
