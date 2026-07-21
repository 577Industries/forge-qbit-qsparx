from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_public_boundary.py"


def run_boundary(
    root: Path, *, scan_history: bool = False, require_manifest: bool = False
) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable, str(SCRIPT), "--root", str(root)]
    if not scan_history:
        arguments.append("--skip-history")
    if not require_manifest:
        arguments.append("--skip-manifest")
    return subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
    )


def test_public_boundary_rejects_proposal_directory(tmp_path: Path) -> None:
    proposal = tmp_path / "proposal"
    proposal.mkdir()
    (proposal / "volume-2.md").write_text("private proposal", encoding="utf-8")

    result = run_boundary(tmp_path)

    assert result.returncode == 1
    assert "proposal/volume-2.md" in result.stderr


def test_public_boundary_rejects_secret_and_restricted_markings(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text(
        "SEC" + "RET//NOFORN\n" + "gh" + "p_abcdefghijklmnopqrstuvwxyz123456",
        encoding="utf-8",
    )

    result = run_boundary(tmp_path)

    assert result.returncode == 1
    assert "notes.txt: restricted marking" in result.stderr
    assert "notes.txt: credential pattern" in result.stderr


@pytest.mark.parametrize(
    ("relative_path", "reason"),
    [
        ("solicitation-working/topic.docx", "private or solicitation path"),
        ("personnel/passport.png", "private or solicitation path"),
        ("financial-backup/rates.csv", "private or solicitation path"),
        ("reviewer-notes.pdf", "opaque document or archive"),
        ("data/observations.ndjson", "non-synthetic dataset path"),
    ],
)
def test_public_boundary_rejects_nonpublic_file_classes(
    tmp_path: Path, relative_path: str, reason: str
) -> None:
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("fictional", encoding="utf-8")

    result = run_boundary(tmp_path)

    assert result.returncode == 1
    assert f"{relative_path}: {reason}" in result.stderr


def test_public_boundary_allows_labeled_synthetic_dataset(tmp_path: Path) -> None:
    target = tmp_path / "data" / "synthetic" / "observations.ndjson"
    target.parent.mkdir(parents=True)
    target.write_text('{"data_label":"synthetic"}\n', encoding="utf-8")

    result = run_boundary(tmp_path)

    assert result.returncode == 0


def test_public_boundary_rejects_prohibited_paths_in_reachable_history(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "boundary@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Boundary Test"], cwd=tmp_path, check=True)
    proposal = tmp_path / "proposal"
    proposal.mkdir()
    source = proposal / "volume-2.md"
    source.write_text("private", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "add proposal"], cwd=tmp_path, check=True)
    source.unlink()
    proposal.rmdir()
    subprocess.run(["git", "add", "-u"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "remove proposal"], cwd=tmp_path, check=True)

    result = run_boundary(tmp_path, scan_history=True)

    assert result.returncode == 1
    assert "history:proposal/volume-2.md" in result.stderr


def test_public_boundary_rejects_credentials_in_reachable_history(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "boundary@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Boundary Test"], cwd=tmp_path, check=True)
    source = tmp_path / "notes.txt"
    source.write_text("gh" + "p_abcdefghijklmnopqrstuvwxyz123456", encoding="utf-8")
    subprocess.run(["git", "add", "notes.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "add leaked token"], cwd=tmp_path, check=True)
    source.write_text("redacted", encoding="utf-8")
    subprocess.run(["git", "add", "notes.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "redact token"], cwd=tmp_path, check=True)

    result = run_boundary(tmp_path, scan_history=True)

    assert result.returncode == 1
    assert "history:notes.txt: credential pattern" in result.stderr


def test_public_boundary_requires_a_valid_manifest(tmp_path: Path) -> None:
    result = run_boundary(tmp_path, require_manifest=True)

    assert result.returncode == 1
    assert "PUBLIC_BOUNDARY.json: missing manifest" in result.stderr


def test_public_boundary_rejects_incomplete_manifest(tmp_path: Path) -> None:
    (tmp_path / "PUBLIC_BOUNDARY.json").write_text("{}\n", encoding="utf-8")

    result = run_boundary(tmp_path, require_manifest=True)

    assert result.returncode == 1
    assert "PUBLIC_BOUNDARY.json: invalid manifest" in result.stderr


def test_public_boundary_accepts_orphan_history_manifest(tmp_path: Path) -> None:
    manifest = {
        "schema_version": "1.0.0",
        "source_snapshot": "9277ee7d6a9acc8085ec56f5ea6150d39165e73c",
        "source_tree": "a" * 40,
        "public_history": "orphan_root",
        "excluded_paths": ["proposal/"],
        "data_policy": "synthetic_only",
    }
    (tmp_path / "PUBLIC_BOUNDARY.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )

    result = run_boundary(tmp_path, require_manifest=True)

    assert result.returncode == 0


def test_public_boundary_ignores_generated_python_cache(tmp_path: Path) -> None:
    cache = tmp_path / "tests" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "canary.pyc").write_bytes(b"gh" + b"p_abcdefghijklmnopqrstuvwxyz123456")

    result = run_boundary(tmp_path)

    assert result.returncode == 0
