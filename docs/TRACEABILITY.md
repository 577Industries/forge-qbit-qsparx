# Requirements-to-Evidence Traceability

| Requirement | State | Implementation | Test or command | Limitation |
|---|---|---|---|---|
| Versioned public records with common evidence envelope | `background_implemented` | `models.py` | `pytest tests/test_models.py` | v1 schema only |
| Deterministic fictional NCR communications mission | `measured_synthetic` | `synthetic.py` | `pytest tests/test_synthetic.py` | not an AFDW inventory |
| Windows/Linux and language/modality balance | `measured_synthetic` | `synthetic.py` | coverage assertions | synthetic breadth, not recall |
| CycloneDX 1.6/1.7 import and 1.7 CBOM export | `background_implemented` | `cyclonedx.py` | `pytest tests/test_cyclonedx.py` | full upstream schema gate pending |
| Decomposable deterministic risk ranking | `measured_synthetic` | `engine.py` | `pytest tests/test_engine.py` | weights not calibrated to sponsor data |
| Rules/ML/graph ablation | `measured_synthetic` | `evaluation.py` | `pytest tests/test_evaluation.py` | development corpus, not acceptance |
| Approval-gated effect-free simulation | `background_implemented` | engine and private plugin | Python and Vitest gate tests | private issuer verification pending |
| CLI and `/v1` API | `background_implemented` | `cli.py`, `api.py` | CLI/API tests | no production service SLO |
| Read-only ten-minute reviewer path | `measured_synthetic` | `reviewer.py` | `make reviewer-demo` | usability study pending |
| Pinned dependency vulnerability audit | `background_implemented` | `pyproject.toml`, `uv.lock`, `Makefile` | `make audit` | point-in-time advisory database; local container scan not run |
| Scale and interoperability thresholds | `planned_phase_i` | preregistration | future sealed benchmark | not measured |
| AFDW elicitation and sponsor integrations | `planned_phase_i` | future SOW Tasks 1-2 | sponsor acceptance | no government access assumed |
| Independent reports and signed immutable release | `planned_phase_i` | validation protocol and release workflow | two signed reports | validators not engaged |
