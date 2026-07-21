from datetime import UTC, datetime
from pathlib import Path

from forge_qsparx.reviewer import ReviewerSite, build_reviewer_site

REPOSITORY_URL = "https://github.com/577Industries/forge-qbit-qsparx"
RELEASE_TAG = "v0.1.0"
SOURCE_COMMIT = "b" * 40
IMAGE_DIGEST = "sha256:" + "c" * 64


def build_bound_reviewer(output_dir: Path) -> ReviewerSite:
    return build_reviewer_site(
        output_dir,
        seed=577,
        generated_at=datetime(2026, 7, 21, tzinfo=UTC),
        release_tag=RELEASE_TAG,
        source_commit=SOURCE_COMMIT,
        image_digest=IMAGE_DIGEST,
    )


def test_reviewer_site_is_deterministic_traceable_and_non_authoritative(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    generated_at = datetime(2026, 7, 21, tzinfo=UTC)

    first = build_reviewer_site(
        first_dir,
        seed=577,
        generated_at=generated_at,
        release_tag="v0.1.0",
        source_commit="b" * 40,
        image_digest="sha256:" + "c" * 64,
    )
    second = build_reviewer_site(
        second_dir,
        seed=577,
        generated_at=generated_at,
        release_tag="v0.1.0",
        source_commit="b" * 40,
        image_digest="sha256:" + "c" * 64,
    )

    assert first.bundle_digest == second.bundle_digest
    assert (first_dir / "evidence" / "bundle.json").read_bytes() == (
        second_dir / "evidence" / "bundle.json"
    ).read_bytes()
    assert (first_dir / "index.html").is_file()
    assert (first_dir / "app.js").is_file()
    assert (first_dir / "styles.css").is_file()
    assert (first_dir / "mission-graph.svg").is_file()
    assert 'rel="icon" href="data:image/svg+xml' in (first_dir / "index.html").read_text()
    assert first.bundle["mission"]["authority_label"] == "non_authoritative"
    assert first.bundle["simulation"]["effects_applied"] is False
    assert first.bundle["manifest"]["root_digest"].startswith("sha256:")
    assert first.bundle["review_path"] == [
        "open_scenario",
        "inspect_risk_queue",
        "simulate_migration",
        "follow_claim_evidence",
    ]
    assert all(
        claim["state"] in {"background_implemented", "measured_synthetic"}
        for claim in first.bundle["claims"]
    )
    assert first.bundle["release"] == {
        "tag": "v0.1.0",
        "source_commit": "b" * 40,
        "image_digest": "sha256:" + "c" * 64,
        "claim_state": "measured_synthetic",
        "validation_state": "not_started",
    }


def test_reviewer_site_uses_safe_network_independent_rendering(tmp_path: Path) -> None:
    build_reviewer_site(tmp_path, seed=577, generated_at=datetime(2026, 7, 21, tzinfo=UTC))

    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    javascript = (tmp_path / "app.js").read_text(encoding="utf-8")

    assert "Content-Security-Policy" in html
    assert 'id="step-scenario"' in html
    assert 'id="step-risk"' in html
    assert 'id="step-migration"' in html
    assert 'id="step-evidence"' in html
    assert "innerHTML" not in javascript
    assert "fetch(" not in javascript
    assert "textContent" in javascript


def test_reviewer_orients_evaluators_and_links_immutable_release_artifacts(
    tmp_path: Path,
) -> None:
    reviewer = build_bound_reviewer(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    release_assets = f"{REPOSITORY_URL}/releases/download/{RELEASE_TAG}"
    expected_artifacts = {
        "release": f"{REPOSITORY_URL}/releases/tag/{RELEASE_TAG}",
        "checksums": f"{release_assets}/SHA256SUMS",
        "spdx_sbom": f"{release_assets}/forge-qbit-qsparx.spdx.json",
        "cyclonedx_sbom": f"{release_assets}/forge-qbit-qsparx.cdx.json",
        "benchmark": f"{release_assets}/benchmark-smoke.json",
        "source_commit": f"{REPOSITORY_URL}/commit/{SOURCE_COMMIT}",
        "wheel": f"{release_assets}/forge_qbit_qsparx-0.1.0-py3-none-any.whl",
        "sdist": f"{release_assets}/forge_qbit_qsparx-0.1.0.tar.gz",
        "reviewer_bundle": f"{release_assets}/reviewer-bundle.tar.gz",
        "evidence_manifest": f"{release_assets}/evidence-manifest.json",
        "evidence_bundle": f"{release_assets}/reviewer-evidence-bundle.json",
        "mission_graph": "mission-graph.svg",
    }

    assert reviewer.bundle["artifacts"] == expected_artifacts
    assert "What this proves" in html
    assert "What this does not prove" in html
    assert "Ten-minute verification path" in html
    assert "uv sync --frozen --extra dev" in html
    assert "make verify" in html
    assert "make benchmark-smoke" in html
    assert "make reviewer-demo" in html
    assert "make public-boundary" in html
    for label, url in expected_artifacts.items():
        assert f'href="{url}"' in html, label


def test_reviewer_risk_queue_is_joined_ranked_filterable_and_accessible(tmp_path: Path) -> None:
    build_bound_reviewer(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    javascript = (tmp_path / "app.js").read_text(encoding="utf-8")

    for label in (
        "Risk rank",
        "Asset name",
        "Asset ID",
        "Mission service",
        "Service ID",
        "Score",
        "Severity",
        "Factor count",
        "Factor labels",
        "Result count",
    ):
        assert label in html
    assert 'id="risk-count"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-pressed="true"' in html
    assert "Showing N of M risks" in html
    assert "Choose another severity" in javascript
    assert "inventory" in javascript
    assert "mission.services" in javascript
    assert ".slice()" in javascript
    assert "score" in javascript
    assert "severity" in javascript
    assert "asset_id" in javascript
    assert "localeCompare" in javascript
    assert "ariaPressed" in javascript


def test_reviewer_exposes_complete_claim_evidence_and_copyable_full_digests(
    tmp_path: Path,
) -> None:
    build_bound_reviewer(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    javascript = (tmp_path / "app.js").read_text(encoding="utf-8")

    for field in (
        "Claim",
        "Requirement",
        "Implementation",
        "Command",
        "State",
        "Limitation",
        "Validator status",
        "Evidence digest",
    ):
        assert field in html
    assert 'id="copy-status"' in html
    assert 'aria-live="polite"' in html
    assert "navigator.clipboard.writeText" in javascript
    assert "document.createElement(\"textarea\")" in javascript
    assert 'document.execCommand("copy")' in javascript
    assert "shortDigest" in javascript
    assert "title" in javascript
    assert "aria-label" in javascript
    assert "data-full-digest" in javascript
    assert "Copy failed" in javascript
    assert "Copy failed" in javascript and "throw" not in javascript


def test_reviewer_keeps_offline_security_accessibility_and_disclosure_guards(
    tmp_path: Path,
) -> None:
    build_bound_reviewer(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    javascript = (tmp_path / "app.js").read_text(encoding="utf-8")
    css = (tmp_path / "styles.css").read_text(encoding="utf-8")

    assert "synthetic" in html.lower()
    assert "non-authoritative" in html.lower()
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css and "reduce" in css
    assert "max-width" in css
    assert "data-label" in css
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "innerHTML"):
        assert forbidden not in javascript
    assert '<script src="https://' not in html
    assert '<script src="http://' not in html
    assert '<link rel="stylesheet" href="https://' not in html
    assert '<link rel="stylesheet" href="http://' not in html
    assert "@import" not in css
    assert "url(https://" not in css
    assert "url(http://" not in css
