# Security Policy

## Supported versions

No production-supported release exists yet. Security fixes target the latest
development branch until the first signed release is published.

## Reporting

Do not open a public issue for a suspected vulnerability, secret, restricted
data exposure, approval bypass, or cross-world isolation failure. Use the
private security-reporting channel configured on the GitHub repository.

Include the affected version or digest, reproduction steps, impact, and any
evidence that real systems or data were contacted. Do not include real keys,
credentials, CUI, classified data, or target details in the report.

## Public safety boundary

The public core is synthetic-only and has no active scanners, real connector
calls, key generation, live remediation, or effectors. Any code path that
changes that boundary requires a threat-model update, approval-bypass tests,
release review, and a major schema-version decision.
