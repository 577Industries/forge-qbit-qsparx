"""Build the read-only reviewer console from precomputed evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

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


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'">
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
    <section class="station" id="step-scenario" aria-labelledby="scenario-title">
      <div class="station-label">Station 01</div><div><h2 id="scenario-title">Mission scenario</h2><p class="lede" id="mission-description"></p></div>
      <div class="metric-strip" id="summary" role="group" aria-label="Mission summary"></div>
      <figure class="mission-trace"><img src="mission-graph.svg" alt="Precomputed cryptographic mission dependency graph"><figcaption>Precomputed from the synthetic release bundle; no runtime graph service.</figcaption></figure>
    </section>
    <section class="station" id="step-risk" aria-labelledby="risk-title">
      <div class="station-label">Station 02</div><div><h2 id="risk-title">Risk queue</h2><p class="lede">Filter the deterministic queue; every score opens into named factors.</p></div>
      <div class="filter-row" id="risk-filters" role="group" aria-label="Risk severity filters"></div>
      <div class="table-wrap"><table><thead><tr><th>Asset</th><th>Score</th><th>Severity</th><th>Evidence factors</th></tr></thead><tbody id="risks"></tbody></table></div>
    </section>
    <section class="station" id="step-migration" aria-labelledby="migration-title">
      <div class="station-label">Station 03</div><div><h2 id="migration-title">Migration simulation</h2><p class="lede">Compare reversible waves and inspect the failure surface before approval.</p></div>
      <div class="split"><article><h3>Wave comparison</h3><div id="waves"></div></article><article><h3>Failure cases</h3><div id="failures"></div><h3>Simulation state</h3><dl id="simulation"></dl></article></div>
    </section>
    <section class="station" id="step-evidence" aria-labelledby="evidence-title">
      <div class="station-label">Station 04</div><div><h2 id="evidence-title">Claim / evidence drill-down</h2><p class="lede">Reproduction state, limitations, and content digests travel with every claim.</p></div>
      <div class="split"><article><div id="claims"></div></article><aside class="artifact-index"><h3>Release artifacts</h3><a href="evidence/bundle.json">Evidence bundle JSON</a><a href="mission-graph.svg">Mission graph SVG</a><p>Bundle digest</p><code id="digest"></code><p>Validator state</p><strong id="validator-state"></strong></aside></div>
    </section>
  </main>
  <footer>Read-only release evidence · all effects disabled · <span id="footer-tag"></span></footer>
  <noscript>This console requires local JavaScript to render the embedded precomputed bundle.</noscript>
  <script src="app.js" defer></script>
</body>
</html>
"""

STYLES_CSS = """:root{--paper:#eef1ed;--ink:#152536;--muted:#5b6872;--teal:#117c7e;--teal-soft:#c9e3df;--amber:#b66a2c;--line:#aeb9b7;--white:#f9faf7}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 "Segoe UI",Tahoma,sans-serif}.boundary-banner{position:sticky;top:0;z-index:5;display:flex;gap:18px;justify-content:center;padding:9px 18px;background:var(--ink);color:var(--white);font-size:.78rem;letter-spacing:.02em}.boundary-banner strong{text-transform:uppercase;color:#9ee1dc}.masthead{display:grid;grid-template-columns:1fr minmax(280px,420px);gap:48px;width:min(1240px,calc(100% - 40px));margin:0 auto;padding:64px 0 46px;border-bottom:2px solid var(--ink)}.kicker,.station-label{font:700 .72rem/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.16em;text-transform:uppercase;color:var(--teal)}h1{margin:10px 0 0;font:700 clamp(2.8rem,7vw,6.7rem)/.88 "Arial Narrow","Segoe UI",sans-serif;letter-spacing:-.055em;text-transform:uppercase}h2{margin:0;font:700 clamp(2rem,4vw,3.8rem)/.95 "Arial Narrow","Segoe UI",sans-serif;letter-spacing:-.035em}h3{font-size:.82rem;text-transform:uppercase;letter-spacing:.12em}.release-plate{display:grid;grid-template-columns:max-content 1fr;align-content:end;gap:8px 18px;margin:0;font:500 .75rem/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.release-plate dt{color:var(--muted);text-transform:uppercase}.release-plate dd{margin:0;overflow-wrap:anywhere}main{width:min(1240px,calc(100% - 40px));margin:auto}.review-rail{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.review-rail a{display:flex;gap:10px;padding:18px 10px;color:var(--ink);text-decoration:none;border-right:1px solid var(--line);font-weight:650}.review-rail a:last-child{border-right:0}.review-rail span{color:var(--teal);font-family:ui-monospace,monospace}.station{display:grid;grid-template-columns:110px 1fr;gap:24px;padding:62px 0;border-bottom:1px solid var(--line)}.station>:nth-child(n+3){grid-column:2}.lede{max-width:720px;color:var(--muted);font-size:1.06rem}.metric-strip{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line)}.metric-card{padding:18px;border-right:1px solid var(--line)}.metric-card:last-child{border-right:0}.metric{font:700 2.2rem/1 ui-monospace,monospace;color:var(--teal)}.metric-label{margin-top:8px;color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em}.mission-trace{margin:24px 0 0;padding:16px;background:var(--white);border:1px solid var(--line)}.mission-trace img{display:block;width:100%;height:auto}.mission-trace figcaption{margin-top:8px;color:var(--muted);font-size:.75rem}.filter-row{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.filter-row button{padding:8px 13px;border:1px solid var(--ink);background:transparent;color:var(--ink);font:650 .78rem ui-monospace,monospace;text-transform:uppercase}.filter-row button[aria-pressed="true"]{background:var(--ink);color:var(--white)}button:focus-visible,a:focus-visible{outline:3px solid var(--amber);outline-offset:3px}.table-wrap{overflow:auto;background:var(--white);border:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:680px}th,td{text-align:left;padding:12px;border-bottom:1px solid #d7dedb;vertical-align:top}th{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}td code,code{font:500 .73rem/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.severity{font:700 .7rem ui-monospace,monospace;text-transform:uppercase}.severity-critical,.severity-high{color:#8e351e}.split{display:grid;grid-template-columns:1.35fr .85fr;gap:22px}.split article,.artifact-index{padding:20px;background:var(--white);border:1px solid var(--line)}.wave{display:grid;grid-template-columns:52px 1fr;gap:12px;padding:14px 0;border-top:1px solid var(--line)}.wave-number{font:700 1.4rem ui-monospace,monospace;color:var(--teal)}dl{display:grid;grid-template-columns:max-content 1fr;gap:7px 14px}dd{margin:0}.failure{padding:10px 0;border-top:1px solid var(--line);color:var(--amber)}details{border-top:1px solid var(--line);padding:14px 0}summary{cursor:pointer;font-weight:700}details p{color:var(--muted)}.claim-meta{display:flex;gap:12px;flex-wrap:wrap;font:600 .7rem ui-monospace,monospace;text-transform:uppercase;color:var(--teal)}.artifact-index{align-self:start;display:grid;gap:10px}.artifact-index a{color:var(--teal)}footer{padding:28px 20px 80px;text-align:center;color:var(--muted);font:500 .75rem ui-monospace,monospace}@media(max-width:800px){.boundary-banner{align-items:flex-start;flex-direction:column;gap:2px}.masthead,.station{grid-template-columns:1fr}.station>:nth-child(n+3){grid-column:1}.review-rail{grid-template-columns:1fr 1fr}.metric-strip,.split{grid-template-columns:1fr 1fr}.release-plate{margin-top:10px}}@media(max-width:520px){.metric-strip,.split,.review-rail{grid-template-columns:1fr}.metric-card{border-right:0;border-bottom:1px solid var(--line)}h1{font-size:2.8rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}"""

STYLES_CSS = STYLES_CSS.replace("#117c7e", "#086d70").replace("#b66a2c", "#914711")

APP_JS = """const byId=(id)=>document.getElementById(id);
const make=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=String(text);return node;};
const addDefinition=(list,term,value)=>{list.append(make('dt','',term),make('dd','',value));};
const b=BUNDLE;
const release=byId('release-metadata');
[['Release',b.release.tag],['Commit',b.release.source_commit],['Image',b.release.image_digest],['Bundle',b.bundle_digest],['Claim',b.release.claim_state],['Validation',b.release.validation_state]].forEach(([term,value])=>addDefinition(release,term,value));
byId('mission-description').textContent=b.mission.description;
[['Assets',b.inventory.length],['Detections',b.detections.length],['Migration waves',b.plan.waves.length],['Real effects',b.simulation.effects_applied?'YES':'None']].forEach(([label,value])=>{const card=make('article','metric-card');card.append(make('div','metric',value),make('div','metric-label',label));byId('summary').append(card);});
const riskBody=byId('risks');
const renderRisks=(severity)=>{riskBody.replaceChildren();b.risks.filter((risk)=>severity==='all'||risk.severity===severity).slice(0,10).forEach((risk)=>{const row=make('tr');const factors=make('td');risk.factors.forEach((factor)=>factors.append(make('div','',factor.label)));row.append(make('td','',risk.asset_id),make('td','',risk.score),make('td',`severity severity-${risk.severity}`,risk.severity),factors);riskBody.append(row);});};
['all','critical','high','medium','low'].forEach((severity,index)=>{const button=make('button','',severity);button.type='button';button.setAttribute('aria-pressed',index===0?'true':'false');button.addEventListener('click',()=>{byId('risk-filters').querySelectorAll('button').forEach((item)=>item.setAttribute('aria-pressed','false'));button.setAttribute('aria-pressed','true');renderRisks(severity);});byId('risk-filters').append(button);});renderRisks('all');
b.plan.waves.forEach((wave)=>{const row=make('section','wave');row.append(make('div','wave-number',String(wave.wave).padStart(2,'0')));const copy=make('div');copy.append(make('strong','',wave.objective),make('p','',`${wave.actions.length} reversible actions · ${wave.exit_criteria.length} exit criteria`));row.append(copy);byId('waves').append(row);});
const failures=b.simulation.compatibility_failures.length?b.simulation.compatibility_failures:['No compatibility failure in this synthetic run. Expected-incompatible native PQC cases remain out of scope for v0.1.0.'];failures.forEach((failure)=>byId('failures').append(make('p','failure',failure)));
[['Status',b.simulation.status],['Mission impact',b.simulation.mission_impact],['Rollback verified',b.simulation.rollback_verified],['Effects applied',b.simulation.effects_applied]].forEach(([term,value])=>addDefinition(byId('simulation'),term,value));
b.claims.forEach((claim)=>{const details=make('details');const summary=make('summary','',claim.claim);const meta=make('div','claim-meta');meta.append(make('span','',claim.state),make('span','',`validator: ${claim.validator_status}`));details.append(summary,meta,make('p','',claim.limitation),make('code','',claim.evidence_digest));byId('claims').append(details);});
byId('digest').textContent=b.bundle_digest;byId('validator-state').textContent=b.release.validation_state;byId('footer-tag').textContent=b.release.tag;
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
    }
    bundle_digest = canonical_digest(bundle)
    bundle["bundle_digest"] = bundle_digest
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "bundle.json").write_bytes(canonical_json(bundle))
    (output_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (output_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (output_dir / "mission-graph.svg").write_text(_mission_graph_svg(mission), encoding="utf-8")
    (output_dir / "app.js").write_text(
        f"const BUNDLE={canonical_json(bundle).decode('utf-8')};\n{APP_JS}",
        encoding="utf-8",
    )
    return ReviewerSite(output_dir=output_dir, bundle=bundle, bundle_digest=bundle_digest)
