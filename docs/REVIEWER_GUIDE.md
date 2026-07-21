# Ten-Minute Reviewer Guide

1. Run `make reviewer-demo` and serve `site/` with any local static server, or
   use the GitHub Pages artifact after publication.
2. Read the synthetic/non-authoritative banner, release bindings, and mission graph.
3. Filter the deterministic top-ten risk queue and inspect its evidence factors.
4. Compare migration waves and the effect-free simulation, including the expected
   JKS incompatibility and verified rollback.
5. Expand each claim to inspect its state, artifact digest, limitation, and
   validator status, then download the canonical evidence bundle if needed.
6. Run `make verify`, `make benchmark-smoke`, and `make audit` locally.

The static console makes no runtime API call. Its canonical bundle is embedded
at build time, and its only browser requests are the same-origin HTML, CSS,
JavaScript, and mission-graph SVG. It has no write controls and cannot contact a
target system.
