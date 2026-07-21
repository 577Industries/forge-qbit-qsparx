# Ten-Minute Reviewer Guide

1. Run `make reviewer-demo` and serve `site/` with any local static server, or
   use the GitHub Pages artifact after publication.
2. Read the synthetic/non-authoritative banner and mission card.
3. Inspect the top-ten risk queue; expand its evidence factors.
4. Review the migration waves and effect-free simulation, including the expected
   JKS incompatibility and verified rollback.
5. Follow each claim to its requirement, implementation, command, artifact
   digest, limitation, and validator status in the bundle.
6. Run `make verify`, `make benchmark-smoke`, and `make audit` locally.

The static console performs no API call except loading its own precomputed local
JSON bundle. It has no write controls and cannot contact a target system.
