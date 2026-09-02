from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CANONICAL_IMAGE_NAME = "577industries/forge-qbit-qsparx"
RELEASE_VERSION = "0.1.2"
# Empty since 2026-09-01: Wolfi python-3.12 3.12.14 carries the fixes the six
# earlier waivers covered. Adding a waiver back means adding its CVE here, in
# scripts/check_container_waivers.py, and in the assessment document.
EXPECTED_CONTAINER_WAIVERS: set[str] = set()


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
    assert re.fullmatch(
        r"forge-qbit-qsparx:(?:ci|release)-\$\{\{ github\.sha \}\}", image
    ), "pre-scan image tag must use the exact local repository"
    return image


def named_step_script(workflow_text: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    assert marker in workflow_text, f"missing workflow step: {name}"
    step = workflow_text.split(marker, 1)[1].split("\n      - ", 1)[0]
    run_marker = "        run: |\n"
    assert run_marker in step, f"workflow step has no shell script: {name}"
    return textwrap.dedent(step.split(run_marker, 1)[1])


def published_release_assets(workflow_text: str) -> set[str]:
    marker = "          files: |\n"
    assert marker in workflow_text, "release workflow has no explicit upload list"
    lines = workflow_text.split(marker, 1)[1].splitlines()
    return {line.strip() for line in lines if line.startswith("            release/")}


def runtime_waiver_scope_digest() -> str:
    # Mirrors scripts/check_container_waivers.py: Dockerfile + product code
    # only; dependency manifests left the scope on 2026-09-01.
    paths = [
        ROOT / "Dockerfile",
        *sorted((ROOT / "src" / "forge_qsparx").glob("*.py")),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_text(encoding="utf-8").encode())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


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


def test_product_release_surfaces_share_the_corrected_version() -> None:
    release_tag = f"v{RELEASE_VERSION}"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["version"] == RELEASE_VERSION
    assert f"version: {RELEASE_VERSION}" in (ROOT / "CITATION.cff").read_text(
        encoding="utf-8"
    )
    assert f'version = "{RELEASE_VERSION}"' in (ROOT / "uv.lock").read_text(
        encoding="utf-8"
    )
    assert f'version="{RELEASE_VERSION}"' in (ROOT / "src/forge_qsparx/api.py").read_text(
        encoding="utf-8"
    )
    assert f'RELEASE_VERSION = "{RELEASE_VERSION}"' in (
        ROOT / "src/forge_qsparx/reviewer.py"
    ).read_text(encoding="utf-8")
    assert f'"version": "{RELEASE_VERSION}"' in (
        ROOT / "src/forge_qsparx/cyclonedx.py"
    ).read_text(encoding="utf-8")
    assert release_tag in (ROOT / "scripts/smoke_container.sh").read_text(encoding="utf-8")


def test_release_uses_commits_from_the_declared_action_repositories() -> None:
    release = workflow("release.yml")

    assert (
        "docker/login-action@af1e73f918a031802d376d3c8bbc3fe56130a9b0 # v4"
        in release
    )
    assert release.count(
        "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6 # v4"
    ) == 2
    assert "docker/login-action@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6" not in release
    assert "actions/attest@36051bcae73b7c2a8a6945a48cbf80953c6baa35" not in release


def test_pr_release_manifest_audits_action_pin_provenance() -> None:
    ci = job(workflow("ci.yml"), "release-manifest")

    assert "GITHUB_TOKEN: ${{ github.token }}" in ci
    assert "uv run python scripts/check_workflow_action_pins.py" in ci


def test_release_notes_limit_determinism_claim_to_mission_and_demo_data() -> None:
    notes = (ROOT / "docs" / "releases" / f"v{RELEASE_VERSION}.md").read_text(
        encoding="utf-8"
    )

    assert "All included mission and demo data is deterministic" in notes
    assert "All included data is deterministic" not in notes
    assert "unwaived high or critical vulnerabilities" in notes
    assert "container vulnerability waivers" in notes

    failed_notes = (ROOT / "docs" / "releases" / "v0.1.0.md").read_text(
        encoding="utf-8"
    )
    assert "Publication status: failed" in failed_notes
    assert "No GitHub Release, GHCR image" in failed_notes
    assert "use `v0.1.2`" in failed_notes

    partial_notes = (ROOT / "docs" / "releases" / "v0.1.1.md").read_text(
        encoding="utf-8"
    )
    assert "Publication status: partial" in partial_notes
    assert "Pages deployment was rejected" in partial_notes
    assert "use `v0.1.2`" in partial_notes


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
    assert "only-fixed: false" in audit
    assert "output-format: table" in audit
    assert "python3 scripts/check_container_waivers.py" in audit
    assert 'bash scripts/smoke_container.sh "${LOCAL_IMAGE}"' in audit
    assert "config: .grype.yaml" in audit
    build = audit.index("docker/build-push-action@")
    smoke = audit.index("scripts/smoke_container.sh")
    scan = audit.index("anchore/scan-action@")
    assert build < smoke < scan


def test_container_waivers_are_exact_versioned_exceptions_with_expiry() -> None:
    policy = json.loads((ROOT / ".grype.yaml").read_text(encoding="utf-8"))

    assert set(policy) == {"show-suppressed", "ignore"}
    assert policy["show-suppressed"] is True
    rules = policy["ignore"]
    assert {rule["vulnerability"] for rule in rules} == EXPECTED_CONTAINER_WAIVERS
    assert len(rules) == len(EXPECTED_CONTAINER_WAIVERS)
    if not rules:
        # No waiver in force: grype runs unfiltered at the high/critical cutoff.
        return
    # The expiry is read from the policy rather than pinned as a literal here.
    # Pinning it meant every renewal broke this test, and — worse — the literal
    # could drift out of step with `.grype.yaml` while the test still passed.
    # What actually matters is the invariant: one shared expiry, the current
    # scope digest on every rule, the date not yet passed, and the assessment
    # document naming the same date.
    expiries = {rule["reason"].split(";")[0].removeprefix("expires=") for rule in rules}
    assert len(expiries) == 1, f"waivers must share one expiry, got {sorted(expiries)}"
    expiry = date.fromisoformat(next(iter(expiries)))
    assert expiry >= datetime.now(UTC).date(), (
        f"container waivers expired on {expiry.isoformat()}; reassess and renew"
    )

    for rule in rules:
        assert set(rule) == {"vulnerability", "package", "reason"}
        assert rule["package"] == {
            "name": "python-3.12",
            "version": "3.12.14-r4",
            "type": "apk",
        }
        assert rule["reason"].startswith(
            f"expires={expiry.isoformat()}; scope={runtime_waiver_scope_digest()};"
        )
        assert "vulnerable_code_not_in_execute_path" in rule["reason"]

    assessment = (ROOT / "docs" / "security" / "container-vulnerability-waivers.md").read_text(
        encoding="utf-8"
    )
    assert expiry.isoformat() in assessment
    for vulnerability in EXPECTED_CONTAINER_WAIVERS:
        assert vulnerability in assessment


def test_container_runtime_and_waiver_checks_are_executable_contracts() -> None:
    smoke = (ROOT / "scripts" / "smoke_container.sh").read_text(encoding="utf-8")
    checker = (ROOT / "scripts" / "check_container_waivers.py").read_text(encoding="utf-8")

    assert "docker image inspect" in smoke
    assert "docker run" in smoke
    assert "/openapi.json" in smoke
    assert "/v1/inventory?seed=577" in smoke
    assert "datetime.now(UTC).date()" in checker
    assert 'Path(".grype.yaml")' in checker
    assert "runtime_scope_digest" in checker


def test_runtime_image_uses_wolfi_python_312_and_runs_as_nonroot() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.count("FROM cgr.dev/chainguard/wolfi-base:latest") == 2
    assert dockerfile.count("apk add --no-cache python-3.12=3.12.14-r4") == 2
    assert "FROM python:3.12-slim" not in dockerfile
    assert "USER nonroot" in dockerfile
    assert 'ENTRYPOINT ["/app/.venv/bin/python", "-m", "uvicorn"]' in dockerfile


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
    assert "only-fixed: false" in release
    assert "fail-build: true" in release
    assert "python3 scripts/check_container_waivers.py" in release
    assert 'bash scripts/smoke_container.sh "${LOCAL_IMAGE}"' in release
    assert "config: .grype.yaml" in release
    assert "format: spdx-json" in release
    assert "format: cyclonedx-json" in release
    assert release.count("image: ${{ env.LOCAL_IMAGE }}") == 3

    build = release.index("docker/build-push-action@")
    smoke = release.index("scripts/smoke_container.sh")
    scan = release.index("anchore/scan-action@")
    spdx = release.index("name: Generate SPDX SBOM")
    cyclonedx = release.index("name: Generate CycloneDX SBOM")
    login = release.index("docker/login-action@")
    assert build < smoke < scan < spdx < cyclonedx < login


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


def test_release_anonymously_pulls_and_health_checks_the_resolved_image() -> None:
    release = job(workflow("release.yml"), "release", "publish-pages")
    anonymous = named_step_script(release, "Verify anonymous immutable pull and health")

    assert 'ANONYMOUS_DOCKER_CONFIG="$(mktemp -d)"' in anonymous
    assert 'test ! -e "${ANONYMOUS_DOCKER_CONFIG}/config.json"' in anonymous
    assert 'export DOCKER_CONFIG="${ANONYMOUS_DOCKER_CONFIG}"' in anonymous
    assert "unset DOCKER_AUTH_CONFIG" in anonymous
    assert 'docker pull "${IMMUTABLE_IMAGE}"' in anonymous
    assert 'bash scripts/smoke_container.sh "${IMMUTABLE_IMAGE}"' in anonymous
    assert (
        "IMMUTABLE_IMAGE: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@"
        "${{ steps.image.outputs.digest }}"
        in release
    )

    resolved = release.index("id: image")
    anonymous_pull = release.index("name: Verify anonymous immutable pull and health")
    attestation = release.index("name: Attest OCI image")
    reviewer = release.index("name: Build reviewer bundle with immutable release identity")
    assert resolved < anonymous_pull < attestation
    assert anonymous_pull < reviewer


def test_release_uses_explicit_notes_and_publishes_the_complete_asset_set() -> None:
    release = job(workflow("release.yml"), "release", "publish-pages")
    expected_assets = {
        f"release/forge_qbit_qsparx-{RELEASE_VERSION}-py3-none-any.whl",
        f"release/forge_qbit_qsparx-{RELEASE_VERSION}.tar.gz",
        "release/container-vulnerabilities.json",
        "release/forge-qbit-qsparx.spdx.json",
        "release/forge-qbit-qsparx.cdx.json",
        "release/benchmark-smoke.json",
        "release/reviewer-evidence-bundle.json",
        "release/evidence-manifest.json",
        "release/reviewer-bundle.tar.gz",
        "release/SHA256SUMS",
    }

    assert f"body_path: docs/releases/v{RELEASE_VERSION}.md" in release
    assert "generate_release_notes:" not in release
    assert published_release_assets(release) == expected_assets
    assert "sha256sum -c SHA256SUMS" in release
    assert release.index("name: Create release checksums") < release.index(
        "name: Attest release files"
    )


def test_checksum_manifest_exactly_matches_published_assets_with_uv_gitignore(
    tmp_path: Path,
) -> None:
    if sys.platform == "win32" or shutil.which("bash") is None:
        pytest.skip("release checksum script requires the Linux release runner's shell")

    release = workflow("release.yml")
    published = published_release_assets(release)
    checksum_asset = "release/SHA256SUMS"
    expected_subjects = {Path(asset).name for asset in published - {checksum_asset}}
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    for subject in expected_subjects:
        (release_dir / subject).write_text(subject, encoding="utf-8")

    # uv 0.11.16 creates this hidden file when building into the release directory.
    (release_dir / ".gitignore").write_text("*\n", encoding="utf-8")
    assert (release_dir / ".gitignore").is_file()

    subprocess.run(
        [
            "bash",
            "-eu",
            "-o",
            "pipefail",
            "-c",
            named_step_script(release, "Create release checksums"),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    checksum_subjects = {
        line.split(maxsplit=1)[1].lstrip("*")
        for line in (release_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    }

    assert checksum_subjects == expected_subjects
    assert ".gitignore" not in checksum_subjects
