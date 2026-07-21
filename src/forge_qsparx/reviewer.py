"""Build the read-only reviewer console from precomputed evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

from forge_qsparx.canonical import ContentAddressedStore, canonical_digest, canonical_json
from forge_qsparx.cyclonedx import export_cbom
from forge_qsparx.engine import QsparxEngine, build_evidence_manifest
from forge_qsparx.evaluation import evaluate_detectors
from forge_qsparx.synthetic import generate_mission


@dataclass(frozen=True)
class ReviewerSite:
    output_dir: Path
    bundle: dict[str, Any]
    bundle_digest: str


REPOSITORY_URL = "https://github.com/577Industries/forge-qbit-qsparx"
RELEASE_VERSION = "0.1.0"


def _artifact_urls(release_tag: str, source_commit: str) -> dict[str, str]:
    encoded_tag = quote(release_tag, safe="")
    encoded_commit = quote(source_commit, safe="")
    release_assets = f"{REPOSITORY_URL}/releases/download/{encoded_tag}"
    return {
        "release": f"{REPOSITORY_URL}/releases/tag/{encoded_tag}",
        "checksums": f"{release_assets}/SHA256SUMS",
        "spdx_sbom": f"{release_assets}/forge-qbit-qsparx.spdx.json",
        "cyclonedx_sbom": f"{release_assets}/forge-qbit-qsparx.cdx.json",
        "benchmark": f"{release_assets}/benchmark-smoke.json",
        "source_commit": f"{REPOSITORY_URL}/commit/{encoded_commit}",
        "wheel": f"{release_assets}/forge_qbit_qsparx-{RELEASE_VERSION}-py3-none-any.whl",
        "sdist": f"{release_assets}/forge_qbit_qsparx-{RELEASE_VERSION}.tar.gz",
        "reviewer_bundle": f"{release_assets}/reviewer-bundle.tar.gz",
        "evidence_manifest": f"{release_assets}/evidence-manifest.json",
        "evidence_bundle": f"{release_assets}/reviewer-evidence-bundle.json",
        "mission_graph": "mission-graph.svg",
    }


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Read-only synthetic QSPARX reviewer console">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='8' fill='%23152536'/%3E%3Ctext x='32' y='43' text-anchor='middle' font-size='36' fill='%239ee1dc'%3EQ%3C/text%3E%3C/svg%3E">
  <link rel="stylesheet" href="styles.css">
  <title>Forge Qbit QSPARX — Synthetic Reviewer Console</title>
</head>
<body>
  <div class="boundary-banner" role="note"><strong>Synthetic · non-authoritative</strong><span>No government network, CUI, active scan, live remediation, FIPS-module validation, or operational performance.</span></div>
  <header class="masthead">
    <div><p class="kicker">Cryptographic mission twin / reviewer release</p><h1>Follow the evidence,<br>not the claim.</h1></div>
    <dl class="release-plate" id="release-metadata" aria-label="Release metadata"></dl>
  </header>
  <main>
    <nav class="review-rail" aria-label="Four-step reviewer path">
      <a href="#step-scenario"><span>01</span>Mission scenario</a>
      <a href="#step-risk"><span>02</span>Risk queue</a>
      <a href="#step-migration"><span>03</span>Migration simulation</a>
      <a href="#step-evidence"><span>04</span>Claim / evidence</a>
    </nav>
    <section class="reviewer-orientation" aria-labelledby="orientation-title">
      <div><p class="kicker">Release orientation</p><h2 id="orientation-title">What this proves / does not prove</h2></div>
      <div class="orientation-grid">
        <article><h3>What this proves</h3><p>The release deterministically produces a synthetic cryptographic inventory, evidence-decomposable risk queue, effect-free migration simulation, and content-addressed claim evidence.</p></article>
        <article><h3>What this does not prove</h3><p>It does not establish operational performance, sponsor-environment compatibility, FIPS validation, authorization to operate, or independent validation.</p></article>
      </div>
      <div class="verification-path">
        <h3>Ten-minute verification path</h3>
        <p>From a clean checkout, bind the source, install the locked development environment, and run the deterministic gates:</p>
        <pre><code>git checkout --detach @@SOURCE_COMMIT@@
uv sync --frozen --extra dev
make verify
make benchmark-smoke
make reviewer-demo
make public-boundary</code></pre>
      </div>
      <ol class="custody-rail" aria-label="Release chain of custody">
        <li><span>01</span><a href="@@RELEASE_URL@@">Protected release</a></li>
        <li><span>02</span><a href="@@CHECKSUMS_URL@@">SHA256 checksums</a></li>
        <li><span>03</span><a href="@@SPDX_URL@@">SPDX SBOM</a> + <a href="@@CYCLONEDX_URL@@">CycloneDX SBOM</a></li>
        <li><span>04</span><a href="@@EVIDENCE_MANIFEST_URL@@">Evidence manifest</a></li>
      </ol>
    </section>
    <section class="station" id="step-scenario" aria-labelledby="scenario-title">
      <div class="station-label">Station 01</div><div><h2 id="scenario-title">Mission scenario</h2><p class="lede" id="mission-description"></p></div>
      <div class="metric-strip" id="summary" role="group" aria-label="Mission summary"></div>
      <figure class="mission-trace"><img src="mission-graph.svg" alt="Precomputed cryptographic mission dependency graph"><figcaption>Precomputed from the synthetic release bundle; no runtime graph service.</figcaption></figure>
    </section>
    <section class="station" id="step-risk" aria-labelledby="risk-title">
      <div class="station-label">Station 02</div><div><h2 id="risk-title">Risk queue</h2><p class="lede">Filter the deterministic queue; every score opens into named factors.</p></div>
      <div class="risk-controls">
        <div class="filter-row" id="risk-filters" role="group" aria-label="Risk severity filters">
          <button type="button" data-severity="all" aria-pressed="true">All</button>
          <button type="button" data-severity="critical" aria-pressed="false">Critical</button>
          <button type="button" data-severity="high" aria-pressed="false">High</button>
          <button type="button" data-severity="medium" aria-pressed="false">Medium</button>
          <button type="button" data-severity="low" aria-pressed="false">Low</button>
        </div>
        <label class="sort-control" for="risk-sort">Sort risks
          <select id="risk-sort"><option value="score">Score, high to low</option><option value="severity">Severity, critical to low</option></select>
        </label>
      </div>
      <p class="result-count" id="risk-count" role="status" aria-live="polite"><span class="sr-only">Result count: </span>Showing N of M risks</p>
      <div class="table-wrap"><table class="risk-table"><thead><tr><th scope="col">Risk rank</th><th scope="col">Asset name<br><span>Asset ID</span></th><th scope="col">Mission service<br><span>Service ID</span></th><th scope="col">Score</th><th scope="col">Severity</th><th scope="col">Factor count / Factor labels</th></tr></thead><tbody id="risks"></tbody></table></div>
    </section>
    <section class="station" id="step-migration" aria-labelledby="migration-title">
      <div class="station-label">Station 03</div><div><h2 id="migration-title">Migration simulation</h2><p class="lede">Compare reversible waves and inspect the failure surface before approval.</p></div>
      <div class="split"><article><h3>Wave comparison</h3><div id="waves"></div></article><article><h3>Failure cases</h3><div id="failures"></div><h3>Simulation state</h3><dl id="simulation"></dl></article></div>
    </section>
    <section class="station" id="step-evidence" aria-labelledby="evidence-title">
      <div class="station-label">Station 04</div><div><h2 id="evidence-title">Claim / evidence drill-down</h2><p class="lede">Reproduction state, limitations, and content digests travel with every claim.</p></div>
      <p class="field-guide"><strong>Claim fields:</strong> Claim · Requirement · Implementation · Command · State · Limitation · Validator status · Evidence digest</p>
      <div class="split"><article><div id="claims"></div></article><aside class="artifact-index"><h3>Immutable artifact map</h3>
        <a href="@@RELEASE_URL@@">Release @@RELEASE_TAG@@</a>
        <a href="@@CHECKSUMS_URL@@">SHA256SUMS</a>
        <a href="@@SPDX_URL@@">SPDX SBOM</a>
        <a href="@@CYCLONEDX_URL@@">CycloneDX SBOM</a>
        <a href="@@BENCHMARK_URL@@">Smoke benchmark</a>
        <a href="@@SOURCE_COMMIT_URL@@">Source commit</a>
        <a href="@@WHEEL_URL@@">Python wheel</a>
        <a href="@@SDIST_URL@@">Source distribution</a>
        <a href="@@REVIEWER_BUNDLE_URL@@">Reviewer bundle</a>
        <a href="@@EVIDENCE_MANIFEST_URL@@">Evidence manifest</a>
        <a href="@@EVIDENCE_BUNDLE_URL@@">Reviewer evidence bundle</a>
        <a href="@@MISSION_GRAPH_URL@@">Mission graph</a>
        <p>Bundle digest</p><div id="digest"></div><p>Validator state</p><strong id="validator-state"></strong>
      </aside></div>
    </section>
  </main>
  <p class="copy-status" id="copy-status" role="status" aria-live="polite"></p>
  <footer>Read-only release evidence · all effects disabled · <span id="footer-tag"></span></footer>
  <noscript>This console requires local JavaScript to render the embedded precomputed bundle.</noscript>
  <script src="app.js" defer></script>
</body>
</html>
"""


def _render_index_html(
    artifact_urls: dict[str, str], *, release_tag: str, source_commit: str
) -> str:
    replacements = {
        "@@RELEASE_TAG@@": release_tag,
        "@@SOURCE_COMMIT@@": source_commit,
        "@@RELEASE_URL@@": artifact_urls["release"],
        "@@CHECKSUMS_URL@@": artifact_urls["checksums"],
        "@@SPDX_URL@@": artifact_urls["spdx_sbom"],
        "@@CYCLONEDX_URL@@": artifact_urls["cyclonedx_sbom"],
        "@@BENCHMARK_URL@@": artifact_urls["benchmark"],
        "@@SOURCE_COMMIT_URL@@": artifact_urls["source_commit"],
        "@@WHEEL_URL@@": artifact_urls["wheel"],
        "@@SDIST_URL@@": artifact_urls["sdist"],
        "@@REVIEWER_BUNDLE_URL@@": artifact_urls["reviewer_bundle"],
        "@@EVIDENCE_MANIFEST_URL@@": artifact_urls["evidence_manifest"],
        "@@EVIDENCE_BUNDLE_URL@@": artifact_urls["evidence_bundle"],
        "@@MISSION_GRAPH_URL@@": artifact_urls["mission_graph"],
    }
    rendered = INDEX_HTML
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, escape(value, quote=True))
    return rendered

STYLES_CSS = """:root{--paper:#eef1ed;--ink:#152536;--muted:#5b6872;--teal:#117c7e;--teal-soft:#c9e3df;--amber:#b66a2c;--line:#aeb9b7;--white:#f9faf7}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 "Segoe UI",Tahoma,sans-serif}.boundary-banner{position:sticky;top:0;z-index:5;display:flex;gap:18px;justify-content:center;padding:9px 18px;background:var(--ink);color:var(--white);font-size:.78rem;letter-spacing:.02em}.boundary-banner strong{text-transform:uppercase;color:#9ee1dc}.masthead{display:grid;grid-template-columns:1fr minmax(280px,420px);gap:48px;width:min(1240px,calc(100% - 40px));margin:0 auto;padding:64px 0 46px;border-bottom:2px solid var(--ink)}.kicker,.station-label{font:700 .72rem/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--teal)}h1{margin:10px 0 0;font:700 clamp(2.8rem,7vw,6.7rem)/.88 "Arial Narrow","Segoe UI",sans-serif;letter-spacing:-.055em;text-transform:uppercase}h2{margin:0;font:700 clamp(2rem,4vw,3.8rem)/.95 "Arial Narrow","Segoe UI",sans-serif;letter-spacing:-.035em}h3{font-size:.82rem;text-transform:uppercase;letter-spacing:.12em}.release-plate{display:grid;grid-template-columns:max-content 1fr;align-content:end;gap:8px 18px;margin:0;font:500 .75rem/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.release-plate dt{color:var(--muted);text-transform:uppercase}.release-plate dd{margin:0;overflow-wrap:anywhere}main{width:min(1240px,calc(100% - 40px));margin:auto}.review-rail{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.review-rail a{display:flex;gap:10px;padding:18px 10px;color:var(--ink);text-decoration:none;border-right:1px solid var(--line);font-weight:650}.review-rail a:last-child{border-right:0}.review-rail span{color:var(--teal);font-family:ui-monospace,monospace}.station{display:grid;grid-template-columns:110px 1fr;gap:24px;padding:62px 0;border-bottom:1px solid var(--line)}.station>:nth-child(n+3){grid-column:2}.lede{max-width:720px;color:var(--muted);font-size:1.06rem}.metric-strip{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line)}.metric-card{padding:18px;border-right:1px solid var(--line)}.metric-card:last-child{border-right:0}.metric{font:700 2.2rem/1 ui-monospace,monospace;color:var(--teal)}.metric-label{margin-top:8px;color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em}.mission-trace{margin:24px 0 0;padding:16px;background:var(--white);border:1px solid var(--line)}.mission-trace img{display:block;width:100%;height:auto}.mission-trace figcaption{margin-top:8px;color:var(--muted);font-size:.75rem}.filter-row{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.filter-row button{padding:8px 13px;border:1px solid var(--ink);background:transparent;color:var(--ink);font:650 .78rem ui-monospace,monospace;text-transform:uppercase}.filter-row button[aria-pressed="true"]{background:var(--ink);color:var(--white)}button:focus-visible,a:focus-visible{outline:3px solid var(--amber);outline-offset:3px}.table-wrap{overflow:auto;background:var(--white);border:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:680px}th,td{text-align:left;padding:12px;border-bottom:1px solid #d7dedb;vertical-align:top}th{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}td code,code{font:500 .73rem/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.severity{font:700 .7rem ui-monospace,monospace;text-transform:uppercase}.severity-critical,.severity-high{color:#8e351e}.split{display:grid;grid-template-columns:1.35fr .85fr;gap:22px}.split article,.artifact-index{padding:20px;background:var(--white);border:1px solid var(--line)}.wave{display:grid;grid-template-columns:52px 1fr;gap:12px;padding:14px 0;border-top:1px solid var(--line)}.wave-number{font:700 1.4rem ui-monospace,monospace;color:var(--teal)}dl{display:grid;grid-template-columns:max-content 1fr;gap:7px 14px}dd{margin:0}.failure{padding:10px 0;border-top:1px solid var(--line);color:var(--amber)}details{border-top:1px solid var(--line);padding:14px 0}summary{cursor:pointer;font-weight:700}details p{color:var(--muted)}.claim-meta{display:flex;gap:12px;flex-wrap:wrap;font:600 .7rem ui-monospace,monospace;text-transform:uppercase;color:var(--teal)}.artifact-index{align-self:start;display:grid;gap:10px}.artifact-index a{color:var(--teal)}footer{padding:28px 20px 80px;text-align:center;color:var(--muted);font:500 .75rem ui-monospace,monospace}@media(max-width:800px){.boundary-banner{align-items:flex-start;flex-direction:column;gap:2px}.masthead,.station{grid-template-columns:1fr}.station>:nth-child(n+3){grid-column:1}.review-rail{grid-template-columns:1fr 1fr}.metric-strip,.split{grid-template-columns:1fr 1fr}.release-plate{margin-top:10px}}@media(max-width:520px){.metric-strip,.split,.review-rail{grid-template-columns:1fr}.metric-card{border-right:0;border-bottom:1px solid var(--line)}h1{font-size:2.8rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}"""

STYLES_CSS = STYLES_CSS.replace("#117c7e", "#086d70").replace("#b66a2c", "#914711")

STYLES_CSS += """.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.reviewer-orientation{padding:48px 0 0;border-bottom:1px solid var(--line)}.reviewer-orientation>div:first-child{display:grid;grid-template-columns:110px 1fr;gap:24px}.orientation-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:28px 0 0;background:var(--line);border:1px solid var(--line)}.orientation-grid article{padding:20px;background:var(--white)}.orientation-grid h3{margin-top:0}.verification-path{display:grid;grid-template-columns:1fr 2fr;gap:24px;padding:24px 0}.verification-path h3,.verification-path p{margin-top:0}.verification-path pre{grid-column:2;margin:0;padding:16px;overflow:auto;background:var(--ink);color:var(--white);border-left:4px solid var(--teal)}.verification-path code{white-space:pre}.custody-rail{display:grid;grid-template-columns:repeat(4,1fr);margin:0;padding:0;list-style:none;border:1px solid var(--line);border-bottom:0}.custody-rail li{position:relative;display:grid;gap:5px;padding:16px 18px;background:var(--white);border-right:1px solid var(--line)}.custody-rail li:not(:last-child)::after{content:"";position:absolute;right:-7px;top:27px;width:12px;height:12px;z-index:1;background:var(--white);border-top:1px solid var(--line);border-right:1px solid var(--line);transform:rotate(45deg)}.custody-rail li:last-child{border-right:0}.custody-rail span{font:700 .7rem ui-monospace,monospace;color:var(--teal)}.custody-rail a{color:var(--ink);font-weight:700}.risk-controls{display:flex;align-items:end;justify-content:space-between;gap:20px}.sort-control{display:grid;gap:5px;padding-bottom:18px;color:var(--muted);font:650 .72rem ui-monospace,monospace;text-transform:uppercase}.sort-control select{min-width:210px;padding:8px;border:1px solid var(--ink);border-radius:0;background:var(--white);color:var(--ink);font:inherit}.result-count{margin:0 0 10px;color:var(--muted);font:600 .75rem ui-monospace,monospace}.risk-table{min-width:980px}.risk-table th span{font-size:.62rem}.identity-cell{display:grid;gap:3px;min-width:150px}.identity-cell code{color:var(--muted)}.factor-list{display:grid;gap:3px;min-width:190px}.factor-count{color:var(--muted);font:650 .68rem ui-monospace,monospace;text-transform:uppercase}.empty-result{padding:30px;text-align:center;color:var(--muted)}.field-guide{color:var(--muted);font-size:.8rem}.claim-fields{grid-template-columns:132px 1fr;margin-bottom:0}.claim-fields dt{color:var(--muted);font-size:.72rem;text-transform:uppercase}.claim-fields dd{overflow-wrap:anywhere}.claim-fields code{color:var(--ink)}.digest-value{display:inline-flex;align-items:center;gap:8px;max-width:100%}.digest-value code{overflow-wrap:anywhere}.copy-button{padding:4px 7px;border:1px solid var(--line);background:transparent;color:var(--teal);font:700 .65rem ui-monospace,monospace;text-transform:uppercase}.copy-status{position:fixed;right:18px;bottom:18px;z-index:4;min-height:1.5rem;margin:0;padding:7px 10px;background:var(--ink);color:var(--white);font:600 .72rem ui-monospace,monospace}.copy-status:empty{display:none}.artifact-index p{margin:12px 0 0}.artifact-index .digest-value{display:grid;justify-items:start}select:focus-visible,summary:focus-visible,.copy-button:focus-visible{outline:3px solid var(--amber);outline-offset:3px}@media(max-width:800px){.reviewer-orientation>div:first-child,.verification-path{grid-template-columns:1fr}.verification-path pre{grid-column:1}.custody-rail{grid-template-columns:1fr 1fr}.custody-rail li:nth-child(2){border-right:0}.risk-controls{align-items:stretch;flex-direction:column;gap:0}.sort-control{justify-self:start}.orientation-grid{grid-template-columns:1fr}}@media(max-width:720px){.risk-table{min-width:0}.risk-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}.risk-table,.risk-table tbody,.risk-table tr,.risk-table td{display:block;width:100%}.risk-table tr{padding:8px 12px;border-bottom:1px solid var(--line)}.risk-table td{display:grid;grid-template-columns:minmax(92px,35%) 1fr;gap:12px;padding:8px 0;border:0}.risk-table td::before{content:attr(data-label);color:var(--muted);font:650 .66rem ui-monospace,monospace;text-transform:uppercase}.risk-table .empty-result{display:block;padding:22px 4px}.risk-table .empty-result::before{content:none}.identity-cell,.factor-list{min-width:0}}@media(max-width:520px){.custody-rail{grid-template-columns:1fr}.custody-rail li{border-right:0;border-bottom:1px solid var(--line)}.custody-rail li:not(:last-child)::after{display:none}}@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}"""

APP_JS = """const byId = (id) => document.getElementById(id);
const make = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
};
const addDefinition = (list, term, value) => {
  list.append(make("dt", "", term), make("dd", "", value));
};
const addDefinitionNode = (list, term, value) => {
  const definition = make("dd");
  definition.append(value);
  list.append(make("dt", "", term), definition);
};
const shortDigest = (value) => value.length > 27 ? `${value.slice(0, 19)}…${value.slice(-6)}` : value;
const copyStatus = byId("copy-status");
const legacyCopy = (value) => {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  try {
    textarea.select();
    return document.execCommand("copy");
  } catch (error) {
    return false;
  } finally {
    textarea.remove();
  }
};
const copyText = async (value, label) => {
  let copied = false;
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(value);
      copied = true;
    } else {
      copied = legacyCopy(value);
    }
  } catch (error) {
    copied = legacyCopy(value);
  }
  copyStatus.textContent = copied ? `${label} copied.` : `Copy failed for ${label}. Select the full value from its accessible label.`;
};
const digestControl = (value, label) => {
  const wrapper = make("span", "digest-value");
  const digest = make("code", "", shortDigest(value));
  digest.title = value;
  digest.setAttribute("aria-label", `${label}, full value: ${value}`);
  digest.setAttribute("data-full-digest", value);
  const button = make("button", "copy-button", "Copy");
  button.type = "button";
  button.setAttribute("aria-label", `Copy full ${label}: ${value}`);
  button.addEventListener("click", () => { void copyText(value, label); });
  wrapper.append(digest, button);
  return wrapper;
};

const b = BUNDLE;
const release = byId("release-metadata");
addDefinition(release, "Release", b.release.tag);
addDefinitionNode(release, "Commit", digestControl(b.release.source_commit, "source commit"));
addDefinitionNode(release, "Image", digestControl(b.release.image_digest, "image digest"));
addDefinitionNode(release, "Bundle", digestControl(b.bundle_digest, "bundle digest"));
addDefinition(release, "Claim", b.release.claim_state);
addDefinition(release, "Validation", b.release.validation_state);
byId("mission-description").textContent = b.mission.description;
[["Assets", b.inventory.length], ["Detections", b.detections.length], ["Migration waves", b.plan.waves.length], ["Real effects", b.simulation.effects_applied ? "YES" : "None"]].forEach(([label, value]) => {
  const card = make("article", "metric-card");
  card.append(make("div", "metric", value), make("div", "metric-label", label));
  byId("summary").append(card);
});

const inventoryById = new Map(b.inventory.map((asset) => [asset.record_id, asset]));
const servicesById = new Map(b.mission.services.map((service) => [service.service_id, service]));
const joinedRisks = b.risks.map((risk) => {
  const asset = inventoryById.get(risk.asset_id);
  const service = asset ? servicesById.get(asset.mission_service_id) : undefined;
  return { risk, asset, service };
});
const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
let selectedSeverity = "all";
let selectedSort = "score";
const sortRisks = () => {
  const sorted = joinedRisks.slice();
  sorted.sort((left, right) => {
    if (selectedSort === "severity") {
      const severityDifference = severityOrder[left.risk.severity] - severityOrder[right.risk.severity];
      if (severityDifference !== 0) return severityDifference;
    }
    const scoreDifference = right.risk.score - left.risk.score;
    if (scoreDifference !== 0) return scoreDifference;
    return left.risk.asset_id.localeCompare(right.risk.asset_id);
  });
  return sorted;
};
const tableCell = (label, text, className = "") => {
  const cell = make("td", className, text);
  cell.setAttribute("data-label", label);
  return cell;
};
const identityCell = (label, name, recordId) => {
  const cell = tableCell(label, undefined, "identity-cell");
  cell.append(make("strong", "", name), make("code", "", recordId));
  return cell;
};
const riskBody = byId("risks");
const renderRisks = () => {
  riskBody.replaceChildren();
  const sortedRisks = sortRisks();
  const filteredRisks = sortedRisks.filter(({ risk }) => selectedSeverity === "all" || risk.severity === selectedSeverity);
  const visibleRisks = filteredRisks.slice(0, 10);
  byId("risk-count").textContent = `Showing ${visibleRisks.length} of ${joinedRisks.length} risks`;
  if (visibleRisks.length === 0) {
    const row = make("tr");
    const empty = tableCell("Result", "No risks match this filter. Choose another severity.", "empty-result");
    empty.colSpan = 6;
    row.append(empty);
    riskBody.append(row);
    return;
  }
  visibleRisks.forEach(({ risk, asset, service }) => {
    const row = make("tr");
    const factors = tableCell("Factor count / Factor labels", undefined, "factor-list");
    factors.append(make("span", "factor-count", `${risk.factors.length} factors`));
    risk.factors.forEach((factor) => factors.append(make("span", "", factor.label)));
    row.append(
      tableCell("Risk rank", sortedRisks.findIndex(({ risk: item }) => item.asset_id === risk.asset_id) + 1),
      identityCell("Asset name / Asset ID", asset ? asset.name : "Unknown asset", risk.asset_id),
      identityCell("Mission service / Service ID", service ? service.name : "Unknown service", asset ? asset.mission_service_id : "Unknown service ID"),
      tableCell("Score", risk.score),
      tableCell("Severity", risk.severity, `severity severity-${risk.severity}`),
      factors,
    );
    riskBody.append(row);
  });
};
byId("risk-filters").querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    selectedSeverity = button.dataset.severity;
    byId("risk-filters").querySelectorAll("button").forEach((item) => { item.ariaPressed = String(item === button); });
    renderRisks();
  });
});
byId("risk-sort").addEventListener("change", (event) => {
  selectedSort = event.target.value;
  renderRisks();
});
renderRisks();

b.plan.waves.forEach((wave) => {
  const row = make("section", "wave");
  row.append(make("div", "wave-number", String(wave.wave).padStart(2, "0")));
  const copy = make("div");
  copy.append(make("strong", "", wave.objective), make("p", "", `${wave.actions.length} reversible actions · ${wave.exit_criteria.length} exit criteria`));
  row.append(copy);
  byId("waves").append(row);
});
const failures = b.simulation.compatibility_failures.length ? b.simulation.compatibility_failures : ["No compatibility failure in this synthetic run. Expected-incompatible native PQC cases remain out of scope for v0.1.0."];
failures.forEach((failure) => byId("failures").append(make("p", "failure", failure)));
[["Status", b.simulation.status], ["Mission impact", b.simulation.mission_impact], ["Rollback verified", b.simulation.rollback_verified], ["Effects applied", b.simulation.effects_applied]].forEach(([term, value]) => addDefinition(byId("simulation"), term, value));

b.claims.forEach((claim) => {
  const details = make("details");
  const summary = make("summary", "", claim.claim);
  const fields = make("dl", "claim-fields");
  addDefinition(fields, "State", claim.state);
  addDefinition(fields, "Requirement", claim.requirement);
  addDefinition(fields, "Implementation", claim.implementation);
  addDefinition(fields, "Command", claim.command);
  addDefinition(fields, "Limitation", claim.limitation);
  addDefinition(fields, "Validator status", claim.validator_status);
  addDefinitionNode(fields, "Evidence digest", digestControl(claim.evidence_digest, `${claim.requirement} evidence digest`));
  details.append(summary, fields);
  byId("claims").append(details);
});
byId("digest").append(digestControl(b.bundle_digest, "bundle digest"));
byId("validator-state").textContent = b.release.validation_state;
byId("footer-tag").textContent = b.release.tag;
"""


def _mission_graph_svg(mission: Any) -> str:
    """Render a deterministic, precomputed mission graph without browser-side layout."""

    assets = sorted(mission.assets, key=lambda item: item.record_id)
    positions: dict[str, tuple[int, int]] = {}
    columns = 4
    for index, asset in enumerate(assets):
        positions[asset.record_id] = (120 + (index % columns) * 260, 110 + (index // columns) * 180)

    edges: list[str] = []
    for relationship in sorted(mission.relationships, key=lambda item: item.record_id):
        source = positions.get(relationship.source_asset_id)
        target = positions.get(relationship.target_asset_id)
        if source is None or target is None:
            continue
        edges.append(
            '<path class="edge" marker-end="url(#arrow)" '
            f'd="M {source[0] + 85} {source[1]} L {target[0] - 85} {target[1]}" />'
        )

    nodes: list[str] = []
    for asset in assets:
        x, y = positions[asset.record_id]
        nodes.append(
            f'<g transform="translate({x} {y})">'
            '<rect x="-92" y="-50" width="184" height="100" rx="8" />'
            f'<text class="name" text-anchor="middle" y="-8">{escape(asset.name)}</text>'
            f'<text class="meta" text-anchor="middle" y="17">{escape(asset.algorithm or "no algorithm")}</text>'
            f'<text class="meta" text-anchor="middle" y="36">{escape(asset.mission_service_id)}</text>'
            "</g>"
        )

    height = 220 + ((len(assets) - 1) // columns) * 180
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-labelledby="title description" viewBox="0 0 1100 '
        f'{height}">'
        '<title id="title">Synthetic cryptographic mission graph</title>'
        '<desc id="description">Precomputed assets and dependency relationships for the fictional reviewer scenario.</desc>'
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>'
        "<style>rect{fill:#f9faf7;stroke:#152536;stroke-width:2}.edge{fill:none;stroke:#117c7e;stroke-width:2;opacity:.72}.name{font:700 14px Segoe UI,Tahoma,sans-serif;fill:#152536}.meta{font:11px ui-monospace,Consolas,monospace;fill:#5b6872}marker path{fill:#117c7e}</style>"
        + "".join(edges)
        + "".join(nodes)
        + "</svg>"
    )


def build_reviewer_site(
    output_dir: Path,
    *,
    seed: int = 577,
    generated_at: datetime | None = None,
    release_tag: str = "unreleased",
    source_commit: str = "0" * 40,
    image_digest: str = "sha256:" + "0" * 64,
) -> ReviewerSite:
    timestamp = generated_at or datetime.now(UTC)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    store = ContentAddressedStore(evidence_dir / "artifacts")
    mission = generate_mission(seed=seed)
    engine = QsparxEngine(mission)
    inventory = engine.inventory()
    risks = engine.assess()
    detections = engine.detect()
    plan = engine.plan(world_id="world-reviewer")
    simulation = engine.simulate(plan)
    cbom = export_cbom(inventory, generated_at=timestamp)
    evaluation = evaluate_detectors(seed=seed, samples=160)
    artifact_urls = _artifact_urls(release_tag, source_commit)

    artifacts = [
        store.put_json(inventory),
        store.put_json(risks),
        store.put_json(detections),
        store.put_json(plan),
        store.put_json(simulation),
        store.put_json(cbom, media_type="application/vnd.cyclonedx+json"),
        store.put_json(evaluation),
    ]
    manifest = build_evidence_manifest(
        release_id=f"{release_tag}-reviewer",
        artifacts=artifacts,
        valid_from=timestamp,
    )
    claims = [
        {
            "claim": "Canonical synthetic cryptographic inventory implemented",
            "state": "background_implemented",
            "requirement": "QSPARX-INV-001",
            "implementation": "forge_qsparx.synthetic and forge_qsparx.cyclonedx",
            "command": "forge-qsparx inventory --seed 577",
            "evidence_digest": artifacts[0].digest,
            "limitation": "Synthetic passive modalities only; no real target scanning.",
            "validator_status": "not_started",
        },
        {
            "claim": "Every deterministic risk score is evidence-decomposable",
            "state": "measured_synthetic",
            "requirement": "QSPARX-RISK-001",
            "implementation": "forge_qsparx.engine.QsparxEngine.assess",
            "command": "forge-qsparx assess --seed 577",
            "evidence_digest": artifacts[1].digest,
            "limitation": "Development policy weights; sealed-corpus ranking gate not run.",
            "validator_status": "not_started",
        },
        {
            "claim": "Migration simulation applies no real effects and verifies rollback",
            "state": "measured_synthetic",
            "requirement": "QSPARX-SIM-001",
            "implementation": "forge_qsparx.engine.QsparxEngine.simulate",
            "command": "forge-qsparx simulate --world world-reviewer --seed 577",
            "evidence_digest": artifacts[4].digest,
            "limitation": "Synthetic compatibility model; no sponsor environment validation.",
            "validator_status": "not_started",
        },
    ]
    bundle: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "review_path": [
            "open_scenario",
            "inspect_risk_queue",
            "simulate_migration",
            "follow_claim_evidence",
        ],
        "release": {
            "tag": release_tag,
            "source_commit": source_commit,
            "image_digest": image_digest,
            "claim_state": "measured_synthetic",
            "validation_state": "not_started",
        },
        "mission": mission.context.model_dump(mode="json"),
        "inventory": [item.model_dump(mode="json") for item in inventory],
        "risks": [item.model_dump(mode="json") for item in risks],
        "detections": [item.model_dump(mode="json") for item in detections],
        "plan": plan.model_dump(mode="json"),
        "simulation": simulation.model_dump(mode="json"),
        "cbom": cbom,
        "evaluation": evaluation,
        "manifest": manifest.model_dump(mode="json"),
        "claims": claims,
        "artifacts": artifact_urls,
    }
    bundle_digest = canonical_digest(bundle)
    bundle["bundle_digest"] = bundle_digest
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "bundle.json").write_bytes(canonical_json(bundle))
    (output_dir / "index.html").write_text(
        _render_index_html(
            artifact_urls,
            release_tag=release_tag,
            source_commit=source_commit,
        ),
        encoding="utf-8",
    )
    (output_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (output_dir / "mission-graph.svg").write_text(_mission_graph_svg(mission), encoding="utf-8")
    (output_dir / "app.js").write_text(
        f"const BUNDLE={canonical_json(bundle).decode('utf-8')};\n{APP_JS}",
        encoding="utf-8",
    )
    return ReviewerSite(output_dir=output_dir, bundle=bundle, bundle_digest=bundle_digest)
