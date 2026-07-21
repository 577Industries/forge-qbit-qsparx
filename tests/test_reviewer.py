from datetime import UTC, datetime
from pathlib import Path

from forge_qsparx.reviewer import build_reviewer_site


def test_reviewer_site_is_deterministic_traceable_and_non_authoritative(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    generated_at = datetime(2026, 7, 21, tzinfo=UTC)

    first = build_reviewer_site(first_dir, seed=577, generated_at=generated_at)
    second = build_reviewer_site(second_dir, seed=577, generated_at=generated_at)

    assert first.bundle_digest == second.bundle_digest
    assert (first_dir / "evidence" / "bundle.json").read_bytes() == (
        second_dir / "evidence" / "bundle.json"
    ).read_bytes()
    assert (first_dir / "index.html").is_file()
    assert (first_dir / "app.js").is_file()
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
