# Public-Boundary Manifest

This repository contains Apache-2.0 software, documentation, synthetic evidence,
and reviewer artifacts only. Its public history was created as a new root from
the tree of source snapshot
`9277ee7d6a9acc8085ec56f5ea6150d39165e73c`; the `proposal/` subtree was
excluded before the new Git repository was initialized.

The machine-readable manifest is [`PUBLIC_BOUNDARY.json`](PUBLIC_BOUNDARY.json).
`scripts/check_public_boundary.py` fails CI when it finds prohibited material in
the working tree or any reachable commit, including:

- proposal, personnel, financial-backup, sensitive-original, solicitation-
  working, or submission-original paths;
- opaque office documents, PDFs, backups, or archives;
- datasets not located beneath an explicit `synthetic` path;
- common credential/private-key patterns; or
- restricted/classification markings.

Opaque wheels, source archives, reviewer bundles, SBOMs, and checksums are built
only in the signed-tag release workflow and attached to releases. They are not
committed to source history.

The original local repository remains the background-IP archive. Never add it
as a public remote or push source commit `9277ee7` to this repository.
