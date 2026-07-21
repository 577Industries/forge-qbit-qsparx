# Ten-Minute Reviewer Guide

The reviewer is a deterministic, read-only evidence room for the synthetic
v0.1.0 release. It proves that the release produces a synthetic cryptographic
inventory, evidence-decomposable risk queue, effect-free migration simulation,
and content-addressed claim evidence. It does not prove operational performance,
sponsor-environment compatibility, FIPS validation, authorization to operate,
or independent validation.

## Verification path

Python 3.12, [uv](https://docs.astral.sh/uv/), and Node.js 22 or newer are
prerequisites for reviewer verification. Node is used only by the executable
reviewer tests; it is not an application runtime dependency. CI and release
automation pin Node.js 24. Use the source commit displayed in the release plate.
From a clean checkout, confirm Node before running the path:

```console
node --version  # requires v22+; CI/release pin v24
git checkout --detach <source commit displayed in the reviewer>
uv sync --frozen --extra dev
make verify
make benchmark-smoke
make reviewer-demo
make public-boundary
```

Then serve `site/` with any local static server, or use the GitHub Pages artifact
after publication:

1. Confirm the persistent synthetic/non-authoritative banner and release bindings.
2. Inspect the mission graph and filter or sort the deterministic risk queue.
3. Confirm each risk's rank, asset and mission-service identities, score, severity,
   and named evidence factors.
4. Compare migration waves with the effect-free simulation, including the expected
   JKS incompatibility and verified rollback.
5. Expand each claim and inspect its requirement, implementation, command, state,
   limitation, validator status, and full copyable evidence digest.
6. Follow the release chain of custody and verify downloaded files with
   `sha256sum -c SHA256SUMS`.

## Immutable v0.1.0 artifact map

Release assets share this immutable prefix:

`https://github.com/577Industries/forge-qbit-qsparx/releases/download/v0.1.0/`

| Artifact | Immutable path |
| --- | --- |
| Protected release | `https://github.com/577Industries/forge-qbit-qsparx/releases/tag/v0.1.0` |
| Checksums | `SHA256SUMS` |
| SPDX SBOM | `forge-qbit-qsparx.spdx.json` |
| CycloneDX SBOM | `forge-qbit-qsparx.cdx.json` |
| Smoke benchmark | `benchmark-smoke.json` |
| Source commit | `https://github.com/577Industries/forge-qbit-qsparx/commit/<source commit displayed in the reviewer>` |
| Python wheel | `forge_qbit_qsparx-0.1.0-py3-none-any.whl` |
| Source distribution | `forge_qbit_qsparx-0.1.0.tar.gz` |
| Reviewer bundle | `reviewer-bundle.tar.gz` |
| Evidence manifest | `evidence-manifest.json` |
| Reviewer evidence bundle | `reviewer-evidence-bundle.json` |
| Mission graph | `mission-graph.svg` inside the reviewer bundle and deployed site |

The release workflow supplies the protected tag, exact source commit, and image
digest when it builds the site. The static console makes no runtime API call. Its
canonical bundle is embedded at build time, and its only browser requests are the
same-origin HTML, CSS, JavaScript, and mission-graph SVG. It has no write controls
and cannot contact a target system.
