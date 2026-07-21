#!/usr/bin/env python3
"""Fail closed when prohibited material enters the public repository."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
FORBIDDEN_COMPONENTS = {
    "financial-backup",
    "originals",
    "personal-documents",
    "personnel",
    "proposal",
    "secure",
    "solicitation-baselines",
    "solicitation-working",
    "submission-originals",
}
OPAQUE_SUFFIXES = {".7z", ".bak", ".doc", ".docx", ".gz", ".pdf", ".rar", ".xls", ".xlsx", ".zip"}
RESTRICTED_MARKING = re.compile(rb"\b(?:SEC(?:RET)|TOP\s+SEC(?:RET)|CUI)//", re.IGNORECASE)
CREDENTIAL_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(rb"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}\b"),
)
MAX_SCAN_BYTES = 10 * 1024 * 1024
SOURCE_SNAPSHOT = "9277ee7d6a9acc8085ec56f5ea6150d39165e73c"


def content_reasons(content: bytes) -> list[str]:
    reasons: list[str] = []
    if RESTRICTED_MARKING.search(content):
        reasons.append("restricted marking")
    if any(pattern.search(content) for pattern in CREDENTIAL_PATTERNS):
        reasons.append("credential pattern")
    return reasons


def scan_paths(root: Path) -> list[str]:
    violations: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue
        if not path.is_file():
            continue
        display_path = relative.as_posix()
        normalized_parts = {part.casefold() for part in relative.parts}
        if normalized_parts & FORBIDDEN_COMPONENTS:
            violations.append(f"{display_path}: private or solicitation path")
        if path.suffix.casefold() in OPAQUE_SUFFIXES:
            violations.append(f"{display_path}: opaque document or archive")
        if normalized_parts & {"data", "datasets"} and "synthetic" not in normalized_parts:
            violations.append(f"{display_path}: non-synthetic dataset path")
        content = path.read_bytes()
        violations.extend(f"{display_path}: {reason}" for reason in content_reasons(content))
    return violations


def scan_history(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-list", "--objects", "--all"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ["git history unavailable"]
    violations: set[str] = set()
    for line in result.stdout.splitlines():
        object_id, separator, historical_path = line.partition(" ")
        if not separator:
            continue
        normalized_parts = {part.casefold() for part in Path(historical_path).parts}
        if normalized_parts & FORBIDDEN_COMPONENTS:
            violations.add(f"history:{historical_path}: private or solicitation path")
        object_type = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-t", object_id],
            check=False,
            capture_output=True,
            text=True,
        )
        if object_type.returncode != 0:
            violations.add(f"history:{historical_path}: unreadable object")
            continue
        if object_type.stdout.strip() != "blob":
            continue
        size = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-s", object_id],
            check=False,
            capture_output=True,
            text=True,
        )
        if size.returncode != 0 or not size.stdout.strip().isdigit():
            violations.add(f"history:{historical_path}: unreadable blob size")
            continue
        if int(size.stdout.strip()) > MAX_SCAN_BYTES:
            violations.add(f"history:{historical_path}: blob exceeds scan limit")
            continue
        blob = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", object_id],
            check=False,
            capture_output=True,
        )
        if blob.returncode != 0:
            violations.add(f"history:{historical_path}: unreadable blob")
            continue
        violations.update(
            f"history:{historical_path}: {reason}" for reason in content_reasons(blob.stdout)
        )
    return sorted(violations)


def validate_manifest(root: Path) -> list[str]:
    path = root / "PUBLIC_BOUNDARY.json"
    if not path.is_file():
        return ["PUBLIC_BOUNDARY.json: missing manifest"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["PUBLIC_BOUNDARY.json: invalid manifest"]
    valid = (
        isinstance(manifest, dict)
        and manifest.get("schema_version") == "1.0.0"
        and manifest.get("source_snapshot") == SOURCE_SNAPSHOT
        and isinstance(manifest.get("source_tree"), str)
        and re.fullmatch(r"[0-9a-f]{40}", manifest["source_tree"]) is not None
        and manifest.get("public_history") == "orphan_root"
        and manifest.get("excluded_paths") == ["proposal/"]
        and manifest.get("data_policy") == "synthetic_only"
    )
    return [] if valid else ["PUBLIC_BOUNDARY.json: invalid manifest"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--skip-history", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    violations = scan_paths(root)
    if not args.skip_history:
        violations.extend(scan_history(root))
    if not args.skip_manifest:
        violations.extend(validate_manifest(root))
    if violations:
        for violation in violations:
            print(f"public-boundary violation: {violation}", file=sys.stderr)
        return 1
    print("public-boundary: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
