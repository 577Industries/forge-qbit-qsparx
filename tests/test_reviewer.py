import subprocess
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


def run_reviewer_logic(app_path: Path, assertions: str) -> None:
    script = f"""
const assert = require("node:assert/strict");
const {{ ReviewerLogic, BUNDLE }} = require(process.argv[1]);
{assertions}
"""
    result = subprocess.run(
        ["node", "-e", script, str(app_path.resolve())],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


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
    assert '<p class="copy-status" id="copy-status" role="status" aria-live="polite">' in html
    assert "throw" not in javascript


def test_reviewer_logic_executes_risk_joins_and_stable_sorting(tmp_path: Path) -> None:
    build_bound_reviewer(tmp_path)

    run_reviewer_logic(
        tmp_path / "app.js",
        """
const defaultView = ReviewerLogic.riskView(BUNDLE);
assert.deepEqual(
  defaultView.rows.slice(0, 4).map(({ rank, assetId }) => [rank, assetId]),
  [
    [1, "asset:directory-jks"],
    [2, "asset:aws-kms-export"],
    [3, "asset:message-api"],
    [4, "asset:records-worker"],
  ],
);
assert.deepEqual(defaultView.rows[0], {
  rank: 1,
  assetId: "asset:directory-jks",
  assetName: "Directory Java Keystore",
  serviceId: "svc-directory",
  serviceName: "Identity and Directory",
  score: 95,
  severity: "critical",
  factorCount: 3,
  factorLabels: [
    "Legacy cryptographic primitive",
    "Quantum-vulnerable public-key primitive",
    "Mission graph outage propagation",
  ],
});
const joined = ReviewerLogic.joinRisks(BUNDLE).reverse();
const sourceOrder = joined.map(({ risk }) => risk.asset_id);
const scoreOrder = ReviewerLogic.sortRisks(joined, "score");
assert.deepEqual(joined.map(({ risk }) => risk.asset_id), sourceOrder);
assert.deepEqual(
  scoreOrder.filter(({ risk }) => risk.score === 70).map(({ risk }) => risk.asset_id),
  ["asset:aws-kms-export", "asset:message-api", "asset:records-worker", "asset:tls-relay"],
);
const severityView = ReviewerLogic.riskView(BUNDLE, "severity", "all", 100);
assert.deepEqual(
  [...new Set(severityView.rows.map(({ severity }) => severity))],
  ["critical", "high", "medium", "low", "info"],
);
assert.deepEqual(
  severityView.rows.map(({ rank }) => rank),
  Array.from({ length: 14 }, (_, index) => index + 1),
);
""",
    )


def test_reviewer_logic_executes_filter_count_pressed_and_empty_states(tmp_path: Path) -> None:
    build_bound_reviewer(tmp_path)

    run_reviewer_logic(
        tmp_path / "app.js",
        """
const lowView = ReviewerLogic.riskView(BUNDLE, "score", "low");
assert.equal(lowView.countText, "Showing 2 of 14 risks");
assert.deepEqual(lowView.rows.map(({ rank }) => rank), [12, 13]);
assert.equal(lowView.filters.find(({ severity }) => severity === "low").pressed, true);
assert.equal(lowView.filters.filter(({ pressed }) => pressed).length, 1);
assert.equal(lowView.emptyMessage, null);
const criticalOnly = {
  ...BUNDLE,
  risks: BUNDLE.risks.filter(({ severity }) => severity === "critical"),
};
const emptyView = ReviewerLogic.riskView(criticalOnly, "score", "low");
assert.equal(emptyView.countText, "Showing 0 of 1 risks");
assert.deepEqual(emptyView.rows, []);
assert.equal(emptyView.filters.find(({ severity }) => severity === "low").pressed, true);
assert.equal(emptyView.emptyMessage, "No risks match this filter. Choose another severity.");
""",
    )


def test_reviewer_logic_executes_claim_rendering_and_exact_digest_copy_paths(
    tmp_path: Path,
) -> None:
    build_bound_reviewer(tmp_path)

    run_reviewer_logic(
        tmp_path / "app.js",
        """
(async () => {
  const claimFields = [
    "claim", "requirement", "implementation", "command", "state", "limitation",
    "validator_status", "evidence_digest",
  ];
  const claims = ReviewerLogic.claimViews(BUNDLE);
  assert.equal(claims.length, BUNDLE.claims.length);
  claims.forEach((claim, index) => {
    claimFields.forEach((field) => assert.equal(claim[field], BUNDLE.claims[index][field]));
    assert.deepEqual(Object.keys(claim), claimFields);
  });
  assert.equal(claims[0].requirement, "QSPARX-INV-001");
  assert.equal(claims[1].implementation, "forge_qsparx.engine.QsparxEngine.assess");
  assert.equal(claims[2].command, "forge-qsparx simulate --world world-reviewer --seed 577");

  const fullDigest = claims[0].evidence_digest;
  const primaryWrites = [];
  const unusedFallbackWrites = [];
  const primaryField = { hidden: true, value: "", focus() {}, select() {} };
  const primaryStatus = { textContent: "" };
  const primaryResult = await ReviewerLogic.copyWithDisclosure(
    fullDigest,
    "inventory evidence digest",
    { writeText: async (value) => primaryWrites.push(value) },
    (value) => { unusedFallbackWrites.push(value); return true; },
    primaryField,
    primaryStatus,
  );
  assert.equal(primaryResult, true);
  assert.deepEqual(primaryWrites, [fullDigest]);
  assert.deepEqual(unusedFallbackWrites, []);
  assert.equal(primaryField.hidden, true);
  assert.equal(primaryStatus.textContent, "inventory evidence digest copied.");

  const rejectedWrites = [];
  const fallbackWrites = [];
  const fallbackField = { hidden: true, value: "", focus() {}, select() {} };
  const fallbackStatus = { textContent: "" };
  const fallbackResult = await ReviewerLogic.copyWithDisclosure(
    fullDigest,
    "inventory evidence digest",
    { writeText: async (value) => {
      rejectedWrites.push(value);
      return Promise.reject(new Error("denied"));
    } },
    (value) => { fallbackWrites.push(value); return true; },
    fallbackField,
    fallbackStatus,
  );
  assert.equal(fallbackResult, true);
  assert.deepEqual(rejectedWrites, [fullDigest]);
  assert.deepEqual(fallbackWrites, [fullDigest]);
  assert.equal(fallbackField.hidden, true);
  assert.equal(fallbackStatus.textContent, "inventory evidence digest copied.");

  const manualField = {
    hidden: true,
    readOnly: false,
    value: "",
    focused: false,
    selected: false,
    focus() { this.focused = true; },
    select() { this.selected = true; },
  };
  const failureStatus = { textContent: "" };
  const failureResult = await ReviewerLogic.copyWithDisclosure(
    fullDigest,
    "inventory evidence digest",
    { writeText: async () => Promise.reject(new Error("denied")) },
    () => false,
    manualField,
    failureStatus,
  );
  assert.equal(failureResult, false);
  assert.equal(manualField.hidden, false);
  assert.equal(manualField.readOnly, true);
  assert.equal(manualField.value, fullDigest);
  assert.equal(manualField.focused, true);
  assert.equal(manualField.selected, true);
  assert.equal(
    failureStatus.textContent,
    "Copy failed for inventory evidence digest. " +
      "The full value is revealed below for manual copy.",
  );
})().catch((error) => { console.error(error); process.exit(1); });
""",
    )


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
