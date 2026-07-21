# Threat Model

## Protected properties

- Synthetic evidence cannot be mislabeled as external or government authority.
- A world-bound private tool cannot read or mutate a different world.
- State-changing private operations cannot reach the core without an approval token.
- The plugin cannot call a remote core or accept an unattested core digest.
- Public simulation never performs a real connector call or remediation write.
- A claim remains traceable to content-addressed evidence and its limitation.

## Primary threats and controls

| Threat | Control | Verification |
|---|---|---|
| Synthetic evidence promoted as operational | Cross-field Pydantic label validation and explicit claim states | `tests/test_models.py` |
| Cross-world confused deputy | Ambient `FORGE_WORLD_ID` must exactly match tool input | private approval/world tests |
| Approval bypass | Approval token required before private ingest, plan, or simulate transport | private approval/world tests |
| Core substitution | HTTP loopback allowlist plus request/response SHA-256 digest pin | private core-client tests |
| Active external reach from public world | No connector packages or active scanner; simulation encodes `effects_applied=false` | verification command and world policy tests |
| Artifact tampering | Canonical JSON, content addressing, manifest root digest | engine and reviewer tests |
| Malformed or drifting schemas | `extra="forbid"`, version literal, bounded fields, unsafe world-id rejection | model/API/repository tests |
| ML policy takeover | Rules own scores and policy; ML results labeled advisory development ablations | evaluation schema and reviewer claim states |
| Secret or restricted-data commit | CI secret/restricted markers, dependency review, CodeQL | `make audit`, workflows |

## Residual risks

- The private token is opaque to this adapter; the future approval service must
  validate issuer, audience, expiry, nonce, operation, plan digest, and world.
- A response digest header is not a substitute for container signature and
  runtime measurement. Release attestations and deployment admission controls
  must verify the image digest independently.
- The synthetic corpus is small and development-selected. It cannot establish
  operational detection performance, sponsor relevance, or TRL 5.
- CycloneDX export is covered by structural tests but full upstream schema and
  interoperability validation remains a release gate.
