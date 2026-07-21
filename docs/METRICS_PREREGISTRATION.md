# Metrics Preregistration

Status: development preregistration, corpus not sealed.

## Acceptance thresholds

- Inventory: precision >= 0.95, recall >= 0.90, modality recall >= 0.85.
- Detection: AUCPR >= 0.90, critical recall >= 0.95, FPR <= 0.01, Brier <= 0.15.
- Prioritization: nDCG@10 >= 0.90 and critical top-ten recall >= 0.90.
- Scale: 10,000 assets, 1,000,000 observations, ingest >= 10,000 observations/minute,
  common-query p95 < 500 ms, incremental detection/scoring p95 < 2 seconds.
- Interoperability: expected-compatible pass; expected-incompatible fail with
  expected diagnosis; 30 repetitions with 95 percent confidence intervals,
  CPU, memory, latency, throughput, and message-size overhead.
- Reproducibility: matching canonical digests across three clean runs.
- Security: no unwaived critical/high finding, embedded secret, restricted data,
  approval bypass, or unverified simulation rollback.

## Frozen decisions

- Split seed: 577.
- Held-out fraction: 0.25, stratified where labels apply.
- Rules are the policy baseline; Isolation Forest, gradient boosting, and graph
  features are advisory comparisons.
- nDCG gains, classifier thresholds, and exclusions must be committed before seal.
- One numerical revision is permitted after the feasibility baseline and before seal.
- No post-seal threshold change is permitted.

Current smoke and development outputs set `acceptance_gate: false`; they cannot
be used to mark any threshold as passed.
