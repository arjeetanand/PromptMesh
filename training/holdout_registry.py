"""Private local registry for final-test source groups and input fingerprints."""

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from training.datasets import load_dataset_snapshot, split_dataset


DEFAULT_BENCHMARKS_DIR = Path(__file__).parent / "benchmarks"


def _json_digest(value):
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_holdout_identity(rows):
    if not rows:
        raise ValueError("The frozen test split is empty")
    groups = set()
    inputs = set()
    for row in rows:
        group_id = row.get("group_id")
        text = row.get("input")
        if not isinstance(group_id, str) or not group_id.strip() or not isinstance(text, str) or not text.strip():
            raise ValueError("Frozen test rows need source-group IDs and input text")
        groups.add(hashlib.sha256(f"group-v1\0{group_id.strip().casefold()}".encode("utf-8")).hexdigest())
        normalized_input = " ".join(text.split()).casefold()
        inputs.add(hashlib.sha256(f"input-v1\0{normalized_input}".encode("utf-8")).hexdigest())
    fingerprints = sorted(
        [{"kind": "source_group", "sha256": value} for value in groups]
        + [{"kind": "input", "sha256": value} for value in inputs],
        key=lambda item: (item["kind"], item["sha256"]),
    )
    return {
        "version": 1,
        "sha256": _json_digest(fingerprints),
        "source_groups": len(groups),
        "examples": len(rows),
        "unique_inputs": len(inputs),
        "fingerprints": fingerprints,
    }


def validate_holdout_identity(identity):
    if (
        not isinstance(identity, dict)
        or identity.get("version") != 1
        or not isinstance(identity.get("fingerprints"), list)
        or not identity["fingerprints"]
        or identity.get("sha256") != _json_digest(identity["fingerprints"])
    ):
        raise ValueError("Frozen test identity is invalid")


def _registry_path(benchmarks_dir, create=False):
    if benchmarks_dir.is_symlink():
        raise ValueError("Benchmark report directory is invalid")
    if create:
        benchmarks_dir.mkdir(parents=True, exist_ok=True)
    root = benchmarks_dir.resolve()
    path = benchmarks_dir / ".holdout-registry.sqlite3"
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Frozen test registry path is invalid")
    if create and not path.exists():
        try:
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
    if path.exists():
        if not path.is_file():
            raise ValueError("Frozen test registry is invalid")
        os.chmod(path, 0o600)
    return path


def _open_registry(benchmarks_dir, create=False):
    path = _registry_path(benchmarks_dir, create=create)
    if not path.exists():
        return None
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS holdout_versions ("
            "dataset_id TEXT NOT NULL, dataset_sha256 TEXT NOT NULL, holdout_sha256 TEXT NOT NULL, "
            "PRIMARY KEY(dataset_id, dataset_sha256))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS holdout_identities ("
            "identity_sha256 TEXT PRIMARY KEY, identity_kind TEXT NOT NULL, dataset_id TEXT NOT NULL, "
            "dataset_sha256 TEXT NOT NULL, holdout_sha256 TEXT NOT NULL, reserved_at TEXT NOT NULL)"
        )
        return connection
    except Exception:
        connection.close()
        raise


def _existing_benchmark_versions(benchmarks_dir):
    if benchmarks_dir.is_symlink():
        raise ValueError("Benchmark report directory is invalid")
    if not benchmarks_dir.exists():
        return []
    versions = set()
    for dataset_dir in benchmarks_dir.iterdir():
        if dataset_dir.name.startswith("."):
            continue
        if dataset_dir.is_symlink():
            raise ValueError("A previous benchmark directory is invalid")
        if not dataset_dir.is_dir() or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", dataset_dir.name):
            continue
        for version_dir in dataset_dir.iterdir():
            if version_dir.is_symlink():
                raise ValueError("A previous benchmark version directory is invalid")
            if not version_dir.is_dir() or not re.fullmatch(r"[a-f0-9]{64}", version_dir.name):
                continue
            for name in ("reservation.json", "final.json"):
                artifact = version_dir / name
                if artifact.is_symlink():
                    raise ValueError("A previous frozen test artifact is invalid")
                if artifact.is_file():
                    versions.add((dataset_dir.name, version_dir.name))
    return sorted(versions)


def _index_previous_holdouts(benchmarks_dir):
    versions = _existing_benchmark_versions(benchmarks_dir)
    if not versions:
        return
    connection = _open_registry(benchmarks_dir, create=True)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for dataset_id, dataset_digest in versions:
            if connection.execute(
                "SELECT 1 FROM holdout_versions WHERE dataset_id = ? AND dataset_sha256 = ?",
                (dataset_id, dataset_digest),
            ).fetchone():
                continue
            try:
                rows, current_digest = load_dataset_snapshot(dataset_id)
            except (OSError, ValueError, UnicodeError) as exc:
                raise ValueError(
                    "A prior frozen-test reservation cannot be indexed; restore its original dataset snapshot before another benchmark"
                ) from exc
            if current_digest != dataset_digest:
                raise ValueError(
                    "A prior frozen-test reservation references a changed dataset; restore its original snapshot before another benchmark"
                )
            identity = create_holdout_identity(split_dataset(rows)["test"])
            reserved_at = datetime.now(timezone.utc).isoformat()
            for fingerprint in identity["fingerprints"]:
                connection.execute(
                    "INSERT OR IGNORE INTO holdout_identities "
                    "(identity_sha256, identity_kind, dataset_id, dataset_sha256, holdout_sha256, reserved_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        fingerprint["sha256"], fingerprint["kind"], dataset_id, dataset_digest,
                        identity["sha256"], reserved_at,
                    ),
                )
            connection.execute(
                "INSERT INTO holdout_versions (dataset_id, dataset_sha256, holdout_sha256) VALUES (?, ?, ?)",
                (dataset_id, dataset_digest, identity["sha256"]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _overlap_exists(connection, identity):
    return any(
        connection.execute(
            "SELECT 1 FROM holdout_identities WHERE identity_sha256 = ?",
            (fingerprint["sha256"],),
        ).fetchone()
        for fingerprint in identity["fingerprints"]
    )


def reject_used_holdout(benchmarks_dir, identity):
    validate_holdout_identity(identity)
    _index_previous_holdouts(benchmarks_dir)
    connection = _open_registry(benchmarks_dir)
    if connection is None:
        return
    try:
        if _overlap_exists(connection, identity):
            raise ValueError(
                "One or more final-test source groups or exact inputs were already reserved by another dataset version; choose a disjoint holdout"
            )
    finally:
        connection.close()


def assert_rows_unseen(rows, benchmarks_dir, context):
    identity = create_holdout_identity(rows)
    _index_previous_holdouts(benchmarks_dir)
    connection = _open_registry(benchmarks_dir)
    if connection is None:
        return
    try:
        if _overlap_exists(connection, identity):
            raise ValueError(
                f"{context} includes a source group or input previously used in a final-test holdout; use new source groups"
            )
    finally:
        connection.close()


def _write_private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(payload)


def reserve_holdout(benchmarks_dir, reservation_path, reservation, identity):
    validate_holdout_identity(identity)
    _index_previous_holdouts(benchmarks_dir)
    connection = _open_registry(benchmarks_dir, create=True)
    try:
        connection.execute("BEGIN IMMEDIATE")
        version_exists = connection.execute(
            "SELECT 1 FROM holdout_versions WHERE dataset_id = ? AND dataset_sha256 = ?",
            (reservation["dataset_id"], reservation["dataset_sha256"]),
        ).fetchone()
        if version_exists or _overlap_exists(connection, identity):
            raise ValueError(
                "A final-test source group or exact input is already reserved or was used by a previous run; choose a disjoint holdout"
            )
        for fingerprint in identity["fingerprints"]:
            connection.execute(
                "INSERT INTO holdout_identities "
                "(identity_sha256, identity_kind, dataset_id, dataset_sha256, holdout_sha256, reserved_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    fingerprint["sha256"], fingerprint["kind"], reservation["dataset_id"],
                    reservation["dataset_sha256"], identity["sha256"], reservation["reserved_at"],
                ),
            )
        _write_private_json(reservation_path, reservation)
        connection.execute(
            "INSERT INTO holdout_versions (dataset_id, dataset_sha256, holdout_sha256) VALUES (?, ?, ?)",
            (reservation["dataset_id"], reservation["dataset_sha256"], identity["sha256"]),
        )
        connection.commit()
    except FileExistsError as exc:
        connection.rollback()
        raise ValueError(
            "A frozen test run is already reserved and may have accessed this holdout; create a disjoint dataset version before another run"
        ) from exc
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
