"""Build the read-only reviewer console from precomputed evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Read-only synthetic QSPARX reviewer console">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2307111f'/%3E%3Ctext x='32' y='43' text-anchor='middle' font-size='36' fill='%236ee7d8'%3EQ%3C/text%3E%3C/svg%3E">
  <title>Forge Qbit QSPARX — Synthetic Reviewer Console</title>
  <style>
    :root { color-scheme: dark; --bg:#07111f; --panel:#0d1d30; --line:#28415d; --text:#e9f2fb; --muted:#9eb3c8; --accent:#6ee7d8; --warn:#ffcd70; }
    * { box-sizing:border-box } body { margin:0; font:16px/1.5 ui-sans-serif,system-ui; background:radial-gradient(circle at top right,#123451,var(--bg) 42%); color:var(--text) }
    main { width:min(1180px,calc(100% - 32px)); margin:auto; padding:42px 0 80px }
    header { display:grid; gap:12px; margin-bottom:28px } h1 { margin:0; font-size:clamp(2rem,5vw,4.4rem); line-height:1; letter-spacing:-.04em }
    h2 { margin:0 0 14px } .eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-weight:700; font-size:.78rem }
    .notice { padding:14px 16px; border:1px solid #805f26; background:#2a2112; color:var(--warn); border-radius:10px }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; margin:20px 0 }
    .card { background:color-mix(in srgb,var(--panel) 94%,transparent); border:1px solid var(--line); border-radius:14px; padding:18px; box-shadow:0 18px 50px #0004 }
    .metric { font-size:2rem; font-weight:750; color:var(--accent) } .muted { color:var(--muted) }
    table { width:100%; border-collapse:collapse } th,td { text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top }
    button { border:1px solid var(--accent); color:var(--accent); background:transparent; border-radius:8px; padding:8px 12px; cursor:pointer }
    button:hover { background:#6ee7d817 } code { color:#b9dcff; overflow-wrap:anywhere }
    @media (max-width:700px) { .table-wrap { overflow:auto } }
  </style>
</head>
<body><main>
  <header><div class="eyebrow">Cryptographic mission twin · reviewer build</div><h1>QSPARX</h1><p class="muted">Discover → normalize → contextualize → detect → prioritize → simulate → verify.</p></header>
  <div class="notice"><strong>Synthetic and non-authoritative.</strong> No government network, CUI, active scan, live remediation, accreditation, FIPS module validation, or operational performance is represented.</div>
  <section class="grid" id="summary" aria-label="Mission summary"></section>
  <section class="card"><h2>Risk queue</h2><div class="table-wrap"><table><thead><tr><th>Asset</th><th>Score</th><th>Severity</th><th>Evidence factors</th></tr></thead><tbody id="risks"></tbody></table></div></section>
  <section class="grid"><article class="card"><h2>Migration simulation</h2><div id="simulation"></div></article><article class="card"><h2>Claim traceability</h2><div id="claims"></div></article></section>
  <p class="muted">Bundle digest: <code id="digest"></code></p>
  <noscript>This read-only console requires JavaScript to render its local precomputed JSON bundle.</noscript>
  <script src="app.js" defer></script>
</main></body></html>
"""

APP_JS = """const esc = (v) => String(v).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
fetch('./evidence/bundle.json').then(r => { if (!r.ok) throw new Error(`bundle HTTP ${r.status}`); return r.json(); }).then(b => {
  const cards = [['Assets',b.inventory.length],['Detections',b.detections.length],['Migration waves',b.plan.waves.length],['Real effects',b.simulation.effects_applied ? 'YES' : 'None']];
  document.querySelector('#summary').innerHTML = cards.map(([k,v]) => `<article class="card"><div class="metric">${esc(v)}</div><div class="muted">${esc(k)}</div></article>`).join('');
  document.querySelector('#risks').innerHTML = b.risks.slice(0,10).map(r => `<tr><td>${esc(r.asset_id)}</td><td>${esc(r.score)}</td><td>${esc(r.severity)}</td><td>${r.factors.map(f=>esc(f.label)).join('<br>')}</td></tr>`).join('');
  const s=b.simulation; document.querySelector('#simulation').innerHTML=`<p>Status: <strong>${esc(s.status)}</strong></p><p>Mission impact: ${esc(s.mission_impact)}</p><p>Rollback verified: ${esc(s.rollback_verified)}</p><p>Effects applied: ${esc(s.effects_applied)}</p>`;
  document.querySelector('#claims').innerHTML=b.claims.map(c=>`<details><summary>${esc(c.claim)} · ${esc(c.state)}</summary><p>${esc(c.limitation)}</p><code>${esc(c.evidence_digest)}</code></details>`).join('');
  document.querySelector('#digest').textContent=b.bundle_digest;
}).catch(error => { document.querySelector('#summary').textContent=`Unable to load evidence: ${error.message}`; });
"""


def build_reviewer_site(
    output_dir: Path,
    *,
    seed: int = 577,
    generated_at: datetime | None = None,
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
        release_id="v0.1.0-reviewer",
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
    (output_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    return ReviewerSite(output_dir=output_dir, bundle=bundle, bundle_digest=bundle_digest)
