"""Runtime details for reproducing local model runs."""

import importlib.metadata
import platform
import subprocess
from pathlib import Path


RUNTIME_PACKAGES = (
    "torch",
    "transformers",
    "peft",
    "trl",
    "datasets",
    "accelerate",
    "bitsandbytes",
    "optimum-quanto",
)


def _source_state():
    root = Path(__file__).resolve().parents[1]
    try:
        result = subprocess.run(
            [
                "git", "-C", str(root), "status", "--porcelain=v2", "--branch",
                "--untracked-files=normal",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    lines = result.stdout.splitlines()
    revision = next(
        (line.removeprefix("# branch.oid ") for line in lines if line.startswith("# branch.oid ")),
        None,
    )
    dirty = any(line and not line.startswith("#") for line in lines)
    return revision if revision and revision != "(initial)" else None, dirty


def runtime_metadata(device):
    packages = {}
    for name in RUNTIME_PACKAGES:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    source_revision, source_dirty = _source_state()
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "device": device,
        "source_revision": source_revision,
        "source_dirty": source_dirty,
        "packages": packages,
    }
