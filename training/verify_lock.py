"""Verify that the local training environment matches its platform-specific lock."""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import sys
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


DEFAULT_LOCK = Path(__file__).resolve().parents[1] / "requirements-training-macos-arm64.lock"


def read_exact_pins(lock_path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line_number, raw_line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            raise ValueError(f"Invalid requirement on line {line_number}: {exc}") from exc
        specs = list(requirement.specifier)
        if (
            requirement.marker
            or requirement.url
            or requirement.extras
            or len(specs) != 1
            or specs[0].operator != "=="
            or "*" in specs[0].version
        ):
            raise ValueError(f"Line {line_number} must contain one exact version pin without a marker or URL")
        name = canonicalize_name(requirement.name)
        if name in pins:
            raise ValueError(f"Duplicate normalized package name on line {line_number}: {name}")
        pins[name] = specs[0].version
    if not pins:
        raise ValueError("The training lock contains no package pins")
    return pins


def compare_pins(
    expected: dict[str, str], installed: dict[str, str]
) -> tuple[list[str], list[tuple[str, str, str]]]:
    normalized_installed = {
        canonicalize_name(name): version for name, version in installed.items()
    }
    missing = sorted(name for name in expected if name not in normalized_installed)
    mismatched = sorted(
        (name, version, normalized_installed[name])
        for name, version in expected.items()
        if name in normalized_installed and normalized_installed[name] != version
    )
    return missing, mismatched


def platform_issues(python_version: tuple[int, int], system: str, machine: str) -> list[str]:
    issues = []
    if python_version != (3, 12):
        issues.append(f"requires Python 3.12; found {python_version[0]}.{python_version[1]}")
    if system != "darwin":
        issues.append(f"requires macOS; found {system}")
    if machine.lower() not in {"arm64", "aarch64"}:
        issues.append(f"requires ARM64; found {machine}")
    return issues


def installed_versions() -> dict[str, str]:
    return {
        canonicalize_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK, help="path to the training lock file")
    args = parser.parse_args()

    issues = platform_issues(sys.version_info[:2], sys.platform, platform.machine())
    if issues:
        for issue in issues:
            print(f"Unsupported verification environment: {issue}.", file=sys.stderr)
        return 2

    try:
        expected = read_exact_pins(args.lock)
    except (OSError, ValueError) as exc:
        print(f"Could not read training lock: {exc}", file=sys.stderr)
        return 2

    missing, mismatched = compare_pins(expected, installed_versions())
    if missing or mismatched:
        if missing:
            print("Missing locked packages:", ", ".join(missing), file=sys.stderr)
        if mismatched:
            details = ", ".join(f"{name} expected {wanted}, found {actual}" for name, wanted, actual in mismatched)
            print("Version mismatches: " + details, file=sys.stderr)
        return 1

    print(
        f"Verified {len(expected)} exact training lock pins against the installed environment "
        f"(Python {platform.python_version()}, macOS ARM64)."
    )
    print("This checks the current environment only; it does not prove a clean install succeeds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
