# Independent Validation Protocol

Validators are evaluators, not proposal-delivery personnel. Each receives only
the signed release, checksums, public instructions, sealed-corpus access process,
and the selected TRL rubric.

Two uncompensated community evaluators are required: Track A covers software
reproducibility and security, while Track B covers applied cryptography and PQC
interoperability. Candidates must disclose a public identity and conflicts,
have made no code or proposal contribution, show relevant expertise and suitable
hardware, and commit to a written schedule. Selection scores independence 30,
expertise 30, reproducibility capacity 20, and schedule 20; a score of at least
80/100 is required, with the highest qualifying candidate selected per track.

Each signed report must state:

- validator identity and conflicts;
- release tag, source commit, image digest, and platform;
- exact commands and whether three clean digests matched;
- passed and failed functional, malformed-input, approval, rollback, security,
  and benchmark cases;
- differences from preregistered intervals;
- known limitations and any unreproduced claim;
- a TRL conclusion with rubric-specific evidence.

Each validator must verify checksums and attestations, run three clean
reproductions, execute malformed-input and approval-bypass tests, run or review
the full benchmark suites, document unreproduced claims, and assess limitations
and safety. Reports separate `reproduced`, `not reproduced`, `failed`, and `out
of scope` findings.

Default maturity language is TRL 4 after independent assessment. TRL 5 is
permitted only when the validators formally determine that the synthetic
environment is relevant under the selected rubric. Government validation
requires government-authored evidence and cannot be inferred from a validator.
If either qualifying report is missing, the engineering evidence may still be
published but the release remains short of `independently_validated`.
