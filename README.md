# Forge Qbit QSPARX

Forge Qbit QSPARX is an evidence-first cryptographic mission twin for planning
post-quantum migration. It operationalizes:

`Discover → Normalize → Contextualize → Detect → Prioritize → Simulate → Approve → Migrate → Verify → Monitor`

The public project uses only deterministic, fictional, unclassified, non-CUI
data and performs no active scanning or live remediation. It includes versioned
Pydantic records, CycloneDX 1.6/1.7 import and canonical CycloneDX 1.7 CBOM
export, deterministic policy and graph scoring, development-only ML ablations,
effect-free migration simulation, a Typer CLI, a FastAPI `/v1` surface, and a
read-only reviewer console built from content-addressed evidence.

This repository is background software under active development. Its synthetic
outputs are non-authoritative and do not demonstrate Air Force deployment,
government validation, FIPS 140 validation, accreditation, or operational
performance. The default maturity target is independently assessable TRL 4.

The public Git history begins at a sanitized orphan root derived from local
source snapshot `9277ee7d6a9acc8085ec56f5ea6150d39165e73c`. That source snapshot
is retained only as a local background-IP archive because it also contains a
private proposal subtree. See [the public-boundary manifest](PUBLIC_BOUNDARY.md)
for the enforced exclusion and data policy.

## Quick start

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required. Node.js 24 is a
development and reviewer-verification prerequisite for the executable static
reviewer tests; it is not an application runtime dependency.

```bash
uv sync --frozen --extra dev
uv run forge-qsparx inventory --seed 577
uv run forge-qsparx plan --world world-reviewer --seed 577
uv run forge-qsparx simulate --world world-reviewer --seed 577
uv run forge-qsparx seed --profile scale-v1 --assets 10000 --observations 1000000
uv run forge-qsparx ingest --adapter cyclonedx path/to/synthetic-cbom.json
```

Run the local API with a release/image digest supplied by the caller:

```bash
export FORGE_QSPARX_CORE_DIGEST="sha256:<64-lowercase-hex-characters>"
uv run uvicorn forge_qsparx.api:app --host 127.0.0.1 --port 8775
```

The private Forge adapter accepts only loopback HTTP and fails closed unless
the response attests the configured digest. Its mutating MCP tools additionally
require an approval token and an exact workspace-world binding.

## Reviewer path

```bash
node --version  # expected: v24.x
make reviewer-demo
uv run python -m http.server 8000 --directory site
```

Then open `http://127.0.0.1:8000`. The hosted build contains precomputed JSON
embedded in its same-origin JavaScript; it cannot contact targets or apply
changes. The four-step path covers the mission scenario, risk filtering,
migration waves/failures, and claim-to-evidence drill-down.

The release gates are:

```bash
make verify
make benchmark-smoke
make audit
```

The smoke benchmark is not an acceptance-gate result. Sealed-corpus evaluation,
the million-observation performance gate, full PQC interoperability,
representative environment validation, and independent validator reports remain
future work. The streaming generator itself has been exercised at exactly
10,000 assets and 1,000,000 observations; generation is not an ingest,
query-latency, or detector acceptance result.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Requirements-to-evidence traceability](docs/TRACEABILITY.md)
- [Metrics preregistration](docs/METRICS_PREREGISTRATION.md)
- [Sealed-corpus protocol](docs/SEALED_CORPUS_PROTOCOL.md)
- [Reviewer guide](docs/REVIEWER_GUIDE.md)
- [Reviewer console validation](docs/REVIEWER_CONSOLE_VALIDATION.md)
- [Limitations and claim boundaries](docs/LIMITATIONS.md)
- [Executable foundation plan](docs/superpowers/plans/2026-07-21-qsparx-foundation.md)
