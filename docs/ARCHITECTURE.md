# Architecture

## Boundary

The Apache-2.0 public core owns evidence-bearing records, deterministic
synthetic generation, CycloneDX interchange, explainable policy, advisory ML
evaluation, migration simulation, content-addressed artifacts, SQLite, CLI,
REST, and the read-only reviewer site. It has no active scanner, real cloud
connector, key operation, remediation write, tenant secret, or production
approval service.

The private `forge-qsparx` plugin in the unified platform owns tenancy,
deployment configuration, world binding, approval capabilities, audit, and
future effectors. It calls the core only through an HTTP loopback URL and
requires a matching SHA-256 deployment digest attestation.

## Pipeline

```text
Discover -> Normalize -> Contextualize -> Detect -> Prioritize
        -> Simulate -> Approve -> Migrate -> Verify -> Monitor
```

This release implements passive synthetic discovery, normalization,
contextualization, deterministic detection and prioritization, approval-gated
effect-free simulation, and verification. Real approval issuance, migration,
and continuous monitoring are private or future Phase I work.

## Data flow

1. `synthetic.generate_mission()` creates a fixed fictional communications mission.
2. `cyclonedx.import_cbom()` maps CycloneDX 1.6/1.7 into strict internal types.
3. `QsparxEngine` constructs the mission graph and emits decomposable policy outputs.
4. `ContentAddressedStore` writes immutable SHA-256-addressed artifacts.
5. `build_evidence_manifest()` binds reviewer claims to artifact digests and limitations.
6. CLI, REST, and reviewer transports serialize the same engine objects.

## Cryptographic boundary

The core inventories and reasons about cryptographic metadata; it does not
implement cryptographic primitives. Standard-library SHA-256 is used only for
artifact addressing. Experimental liboqs or oqs-provider paths are excluded
from this release and may not be described as FIPS validated without CMVP
evidence for the exact module and configuration.
