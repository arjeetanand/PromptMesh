"""Private, local-only review workflow for the public-source candidate packet."""

import csv
import os
import tempfile
import threading
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
            if "reuse_evidence" not in fieldnames:
                fieldnames.append("reuse_evidence")
            rows = []
            for index, row in enumerate(reader):
                if None in row or not row.get("group_id"):
                    raise ValueError("The local review packet contains a malformed row")
                normalized = {column: row.get(column, "") or "" for column in fieldnames}
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
    for group in group_rows:
        group["reviewed_rows"] = sum(row["review_status"] == "REVIEWED" for row in group["rows"])
        group["eligible"] = (
            group["reviewed_rows"] == len(group["rows"])
            and group["reuse_status"] == "permission_confirmed"
            and bool(group["reuse_evidence"].strip())
        )

    total_rows = sum(len(group["rows"]) for group in group_rows)
    reviewed_rows = sum(group["reviewed_rows"] for group in group_rows)
    eligible_groups = sum(group["eligible"] for group in group_rows)
    return {
        "total_rows": total_rows,
        "reviewed_rows": reviewed_rows,
        "total_groups": len(group_rows),
        "reviewed_groups": sum(group["reviewed_rows"] == len(group["rows"]) for group in group_rows),
        "eligible_groups": eligible_groups,
        "groups": group_rows,
    }


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
