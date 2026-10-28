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
    manifest_path = run_dir / "manifest.json"
    adapter_path = run_dir / "adapter"
    if not manifest_path.is_file() or not (adapter_path / "adapter_config.json").is_file():
        raise ValueError("Trained adapter is not available")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "completed" or manifest.get("run_id") != run_id:
        raise ValueError("Trained adapter is not available")
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
            "metrics": manifest["metrics"]["adapter"],
        })
    return results
