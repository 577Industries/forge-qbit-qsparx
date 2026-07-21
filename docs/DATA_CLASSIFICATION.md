# Data Classification and Handling

| Class | Allowed in public repository | Label |
|---|---:|---|
| Generated fictional mission data | Yes | `synthetic`, `non_authoritative` |
| Public standards and public mission descriptions | Yes, with source | `authoritative`, `external_authority` only for the source record |
| Proprietary company background implementation details | Only after release review | `background_implemented` |
| CUI, classified, export-controlled target data, credentials, real key material | No | Prohibited |
| Sponsor inventory, topology, certificates, key metadata, logs | No public release | Private Phase I handling plan required |

No public fixture may contain a real host name, account identifier, certificate,
key, IP address, employee identifier, or target-specific configuration. Cloud
fixtures describe passive metadata exports and contain no credentials or SDK
calls.
