from datetime import UTC, datetime
from pathlib import Path

from forge_qsparx.reviewer import build_reviewer_site


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
