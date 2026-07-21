# Sealed Corpus Protocol

1. Assign immutable corpus, label-guide, generator, and split-manifest digests.
2. Separate corpus authors from final evaluators; record every access.
3. Freeze thresholds, exclusions, model versions, random seeds, and reference machine.
4. Encrypt the held-out labels outside the normal development workspace.
5. Run three clean reproductions from the signed release image.
6. Preserve raw output, environment inventory, CPU/memory samples, commands,
   timestamps, and content digests without manual correction.
7. Have two independent validators reproduce the release and sign reports on
   correctness, limitations, safety, and TRL.
8. Publish only synthetic, unclassified, non-CUI artifacts approved for release.

The corpus is not sealed. No file in this repository may claim a sealed result
until the manifest includes independent custodian and validator signatures.
