from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_all_actions_are_pinned_to_full_commit_shas() -> None:
    uses = []
    for path in WORKFLOWS.glob("*.yml"):
        uses.extend(re.findall(r"uses:\s*[^@\s]+@([^\s#]+)", path.read_text(encoding="utf-8")))

    assert uses
    assert all(FULL_SHA.fullmatch(reference) for reference in uses)


def test_pages_deploys_release_tags_with_separate_jobs() -> None:
    pages = workflow("pages.yml")

    assert "workflow_call:" in pages
    assert "release_tag:" in pages
    assert "branches: [main]" not in pages
    assert "configure-pages" in pages
    assert "upload-pages-artifact" in pages
    assert re.search(r"^  build:\n", pages, re.MULTILINE)
    assert re.search(r"^  deploy:\n", pages, re.MULTILINE)
    assert "needs: build" in pages
    assert "name: github-pages" in pages


def test_release_blocks_high_vulnerabilities_and_avoids_latest_tag() -> None:
    release = workflow("release.yml")

    assert "anchore/scan-action" in release
    assert "severity-cutoff: high" in release
    assert "fail-build: true" in release
    assert "actions/attest" in release
    assert "actions/attest-build-provenance" not in release
    assert ":latest" not in release
    assert "uses: ./.github/workflows/pages.yml" in release
    assert "needs: release" in release


def test_ci_exposes_required_branch_protection_checks() -> None:
    ci = workflow("ci.yml")

    for job_name in [
        "Linux CI",
        "Windows CI",
        "Dependency audit",
        "Public boundary",
        "Release manifest",
    ]:
        assert f"name: {job_name}" in ci
