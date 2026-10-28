import hashlib
import json
import re
from pathlib import Path


RUNS_DIR = Path(__file__).parent / "runs"
RUN_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def get_adapter_path(run_id):
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("Trained adapter id is invalid")
    run_dir = (RUNS_DIR / run_id).resolve()
    if run_dir.parent != RUNS_DIR.resolve():
        raise ValueError("Trained adapter path is invalid")
    manifest_path = (run_dir / "manifest.json").resolve()
    adapter_path = (run_dir / "adapter").resolve()
    if manifest_path.parent != run_dir or adapter_path.parent != run_dir:
        raise ValueError("Trained adapter paths are invalid")
    if not manifest_path.is_file() or not (adapter_path / "adapter_config.json").is_file():
        raise ValueError("Trained adapter is not available")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "completed" or manifest.get("run_id") != run_id:
        raise ValueError("Trained adapter is not available")
    return adapter_path, manifest


def artifact_tree_sha256(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Adapter artifact must not contain symlinks")
    root = root.resolve()
    files = sorted(root.rglob("*"))
    digest = hashlib.sha256()
    file_count = 0
    for path in files:
        if path.is_symlink():
            raise ValueError("Adapter artifact must not contain symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as artifact:
            for block in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(block)
        file_count += 1
    if not file_count:
        raise ValueError("Adapter artifact is empty")
    return digest.hexdigest()


def get_benchmark_adapter(run_id, dataset_id, dataset_digest):
    adapter_path, manifest = get_adapter_path(run_id)
    if manifest.get("schema_version") != 3:
        raise ValueError("This adapter manifest lacks the frozen-benchmark provenance")
    if manifest.get("metrics_split") != "validation" or manifest.get("test_split_used") is not False:
        raise ValueError("Only validation-selected adapters are eligible for final benchmarking")
    if manifest.get("dataset_id") != dataset_id or manifest.get("dataset_sha256") != dataset_digest:
        raise ValueError("Adapter was trained on a different dataset fingerprint")
    if not manifest.get("base_revision") or manifest.get("tokenizer_revision") != manifest.get("base_revision"):
        raise ValueError("Adapter base and tokenizer revisions are incomplete or inconsistent")
    expected_digest = manifest.get("adapter_sha256")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
        raise ValueError("Adapter manifest has no valid artifact fingerprint")
    if artifact_tree_sha256(adapter_path) != expected_digest:
        raise ValueError("Adapter files do not match the saved artifact fingerprint")
    return adapter_path, manifest


def list_adapters():
    if not RUNS_DIR.exists():
        return []
    results = []
    for run_dir in sorted(RUNS_DIR.iterdir(), key=lambda path: path.name, reverse=True):
        try:
            _, manifest = get_adapter_path(run_dir.name)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        results.append({
            "id": f"trained:{run_dir.name}",
            "run_id": run_dir.name,
            "base_model": manifest["base_model"],
            "dataset_id": manifest["dataset_id"],
            "dataset_sha256": manifest["dataset_sha256"],
            "created_at": manifest["created_at"],
            "metrics_split": manifest.get("metrics_split", "legacy_test"),
            "benchmark_manifest_ready": (
                manifest.get("schema_version") == 3
                and manifest.get("metrics_split") == "validation"
                and manifest.get("test_split_used") is False
                and bool(manifest.get("base_revision"))
                and manifest.get("tokenizer_revision") == manifest.get("base_revision")
                and isinstance(manifest.get("adapter_sha256"), str)
                and re.fullmatch(r"[a-f0-9]{64}", manifest["adapter_sha256"]) is not None
            ),
            "metrics": manifest["metrics"]["adapter"],
        })
    return results
