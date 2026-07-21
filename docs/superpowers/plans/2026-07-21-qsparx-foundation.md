# QSPARX Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deterministic, synthetic-only public cryptographic mission-twin foundation and a private approval-gated Forge adapter without asserting unmeasured Phase I outcomes.

**Architecture:** A standalone Python package owns evidence-bearing domain models and a side-effect-free pipeline. A private TypeScript plugin invokes a digest-pinned core over loopback, binds every request to a world, and requires approval tokens for state-changing simulation requests. Content-addressed artifacts connect claims to reproducible outputs.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI, Typer, SQLite, NetworkX, scikit-learn, SHAP, pytest, TypeScript, TypeBox, Vitest.

## Global Constraints

- All public fixtures and outputs are synthetic, unclassified, non-CUI, and non-authoritative.
- The public core performs no active scanning, connector calls, live remediation, or cryptographic key operations.
- Deterministic rules own scores and policy decisions; ML output is advisory evaluation evidence only.
- liboqs and oqs-provider are excluded from the core and may appear only in separately labeled experimental interoperability tests.
- Maturity defaults to independently assessable TRL 4; TRL 5 and government validation are not claimed.
- Existing Forge Qbit optimization, deployment, FIPS, accreditation, and benchmark assertions are excluded from QSPARX evidence.

---

### Task 1: Evidence-bearing public types

**Files:** `src/forge_qsparx/models.py`, `tests/test_models.py`

- [ ] Write tests proving all eleven public records require a common evidence envelope and reject invalid confidence, validity, and digest values.
- [ ] Run `uv run pytest tests/test_models.py -q` and observe import failure.
- [ ] Implement strict, versioned Pydantic models and rerun the tests.

### Task 2: Deterministic synthetic mission and CBOM boundary

**Files:** `src/forge_qsparx/canonical.py`, `src/forge_qsparx/synthetic.py`, `src/forge_qsparx/cyclonedx.py`, `tests/test_synthetic.py`, `tests/test_cyclonedx.py`

- [ ] Test repeated generation, content-addressed persistence, defense-balanced coverage, CycloneDX 1.6/1.7 import, and canonical 1.7 export.
- [ ] Observe missing-module failures, implement the minimum behavior, and validate exported CBOM against the official 1.7 schema fixture.

### Task 3: Explainable pipeline and persistence

**Files:** `src/forge_qsparx/engine.py`, `src/forge_qsparx/repository.py`, `tests/test_engine.py`, `tests/test_repository.py`

- [ ] Test inventory, decomposable risk factors, detections, migration waves, rollback-bearing simulations, manifests, and isolated SQLite worlds.
- [ ] Observe failures, implement deterministic rules and graph-derived context, then rerun the suite.

### Task 4: Public CLI and REST surface

**Files:** `src/forge_qsparx/cli.py`, `src/forge_qsparx/api.py`, `tests/test_cli.py`, `tests/test_api.py`

- [ ] Test all nine named CLI commands and corresponding `/v1` resources.
- [ ] Observe failures, implement orchestration-only adapters, and rerun interface tests.

### Task 5: Private world and approval gate

**Files:** `platform/plugins/forge-qsparx/**`

- [ ] Write Vitest coverage for loopback enforcement, digest pinning, world binding, and approval-token requirements.
- [ ] Observe failure, implement the plugin, regenerate the pack catalog, and rerun platform policy tests.

### Task 6: Reviewer release and verification

**Files:** `Makefile`, `Dockerfile`, `.github/workflows/**`, `docs/**`, release metadata

- [ ] Add reviewer, verify, smoke benchmark, audit, Linux/Windows CI, CodeQL, SBOM, signing, and restricted-data gates.
- [ ] Run format, lint, type, tests, reviewer demo, verify, benchmark smoke, and audit from clean artifacts.
- [ ] Record measured outputs and retain every unmet six-month gate as `planned_phase_i` or a future background-IP milestone.
