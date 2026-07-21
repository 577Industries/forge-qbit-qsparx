from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CANONICAL_IMAGE_NAME = "577industries/forge-qbit-qsparx"
RELEASE_VERSION = "0.1.0"


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def job(workflow_text: str, name: str, next_name: str | None = None) -> str:
    marker = f"  {name}:\n"
    assert marker in workflow_text, f"missing workflow job: {name}"
    body = workflow_text.split(marker, 1)[1]
    if next_name is not None:
        next_marker = f"  {next_name}:\n"
        assert next_marker in body, f"missing following workflow job: {next_name}"
        body = body.split(next_marker, 1)[0]
    return body


def local_image(job_text: str) -> str:
    match = re.search(r"^\s+LOCAL_IMAGE:\s+(.+)$", job_text, re.MULTILINE)
    assert match is not None, "workflow must declare one explicit local image tag"
    image = match.group(1).strip()
    assert not image.startswith("ghcr.io/"), "pre-scan image tag must remain local"
    return image


def test_release_uses_the_lowercase_canonical_oci_name() -> None:
    release = workflow("release.yml")

    assert f"IMAGE_NAME: {CANONICAL_IMAGE_NAME}" in release
    assert "IMAGE_NAME: ${{ github.repository }}" not in release
    assert CANONICAL_IMAGE_NAME.lower() == CANONICAL_IMAGE_NAME


def test_release_trigger_notes_and_package_assets_share_one_version() -> None:
    release = workflow("release.yml")
    release_tag = f"v{RELEASE_VERSION}"

    assert f'tags: ["{release_tag}"]' in release
    assert 'tags: ["v*"]' not in release
    assert f"body_path: docs/releases/{release_tag}.md" in release
    assert f"release/forge_qbit_qsparx-{RELEASE_VERSION}-py3-none-any.whl" in release
    assert f"release/forge_qbit_qsparx-{RELEASE_VERSION}.tar.gz" in release


def test_release_notes_limit_determinism_claim_to_mission_and_demo_data() -> None:
    notes = (ROOT / "docs" / "releases" / "v0.1.0.md").read_text(encoding="utf-8")

    assert "All included mission and demo data is deterministic" in notes
    assert "All included data is deterministic" not in notes


def test_ci_container_audit_builds_loads_and_blocks_without_registry_access() -> None:
    ci = workflow("ci.yml")
    audit = job(ci, "container-audit", "public-boundary")
    image = local_image(audit)

    assert "pull_request:" in ci
    assert "name: Container audit" in audit
    assert audit.count("docker/build-push-action@") == 1
    assert "load: true" in audit
    assert "push: false" in audit
    assert image.startswith("forge-qbit-qsparx:")
    assert "${{ github.sha }}" in image
    assert "tags: ${{ env.LOCAL_IMAGE }}" in audit
    assert "docker/login-action@" not in audit
    assert "docker push" not in audit
    assert "anchore/scan-action@" in audit
    assert "image: ${{ env.LOCAL_IMAGE }}" in audit
    assert "fail-build: true" in audit
    assert "severity-cutoff: high" in audit
    assert audit.index("docker/build-push-action@") < audit.index("anchore/scan-action@")


def test_release_scans_and_generates_both_sboms_before_registry_login() -> None:
    release = job(workflow("release.yml"), "release", "publish-pages")
    image = local_image(release)

    assert image.startswith("forge-qbit-qsparx:")
    assert "${{ github.sha }}" in image
    assert release.count("docker/build-push-action@") == 1
    assert "load: true" in release
    assert "push: false" in release
    assert "tags: ${{ env.LOCAL_IMAGE }}" in release
    assert "image: ${{ env.LOCAL_IMAGE }}" in release
    assert "severity-cutoff: high" in release
    assert "fail-build: true" in release
    assert "format: spdx-json" in release
    assert "format: cyclonedx-json" in release
    assert release.count("image: ${{ env.LOCAL_IMAGE }}") == 3

    build = release.index("docker/build-push-action@")
    scan = release.index("anchore/scan-action@")
    spdx = release.index("name: Generate SPDX SBOM")
    cyclonedx = release.index("name: Generate CycloneDX SBOM")
    login = release.index("docker/login-action@")
    assert build < scan < spdx < cyclonedx < login


def test_release_pushes_only_version_and_full_source_sha_tags() -> None:
    release = job(workflow("release.yml"), "release", "publish-pages")

    assert (
        "VERSION_IMAGE: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.ref_name }}"
        in release
    )
    assert (
        "SHA_IMAGE: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}"
        in release
    )
    assert 'docker tag "${LOCAL_IMAGE}" "${VERSION_IMAGE}"' in release
    assert 'docker tag "${LOCAL_IMAGE}" "${SHA_IMAGE}"' in release
    assert 'docker push "${VERSION_IMAGE}"' in release
    assert 'docker push "${SHA_IMAGE}"' in release
    assert release.count("docker push ") == 2
    assert ":latest" not in release.lower()


def test_release_resolves_matching_remote_digests_before_all_consumers() -> None:
    release_workflow = workflow("release.yml")
    release = job(release_workflow, "release", "publish-pages")

    assert "image_digest: ${{ steps.image.outputs.digest }}" in release
    assert "id: image" in release
    assert release.count("docker buildx imagetools inspect") == 2
    assert 'test "${VERSION_DIGEST}" = "${SHA_DIGEST}"' in release
    assert 'test "${VERSION_DIGEST#sha256:}" != "${VERSION_DIGEST}"' in release
    assert 'test "${#VERSION_DIGEST}" -eq 71' in release
    assert 'echo "digest=${VERSION_DIGEST}" >> "${GITHUB_OUTPUT}"' in release

    resolved = release.index("id: image")
    attestation = release.index("name: Attest OCI image")
    reviewer = release.index("name: Build reviewer bundle with immutable release identity")
    publication = release.index("name: Publish immutable release files")
    assert resolved < attestation
    assert resolved < reviewer
    assert resolved < publication
    assert "subject-digest: ${{ steps.image.outputs.digest }}" in release
    assert "FORGE_QSPARX_IMAGE_DIGEST: ${{ steps.image.outputs.digest }}" in release
    assert "image_digest: ${{ needs.release.outputs.image_digest }}" in release_workflow


def test_release_uses_explicit_notes_and_publishes_the_complete_asset_set() -> None:
    release = job(workflow("release.yml"), "release", "publish-pages")
    expected_assets = {
        "release/forge_qbit_qsparx-0.1.0-py3-none-any.whl",
        "release/forge_qbit_qsparx-0.1.0.tar.gz",
        "release/container-vulnerabilities.json",
        "release/forge-qbit-qsparx.spdx.json",
        "release/forge-qbit-qsparx.cdx.json",
        "release/benchmark-smoke.json",
        "release/reviewer-evidence-bundle.json",
        "release/evidence-manifest.json",
        "release/reviewer-bundle.tar.gz",
        "release/SHA256SUMS",
    }

    assert "body_path: docs/releases/v0.1.0.md" in release
    assert "generate_release_notes:" not in release
    for asset in expected_assets:
        assert asset in release, f"release is missing required asset: {asset}"
    assert "! -name SHA256SUMS" in release
    assert "sort -z" in release
    assert "sha256sum -c SHA256SUMS" in release
    assert release.index("name: Create release checksums") < release.index(
        "name: Attest release files"
    )
