import json
from pathlib import Path

from typer.testing import CliRunner

from forge_qsparx.cli import app

runner = CliRunner()


def test_cli_exposes_all_public_pipeline_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "seed",
        "ingest",
        "inventory",
        "assess",
        "detect",
        "plan",
        "simulate",
        "benchmark",
        "verify",
    ):
        assert command in result.stdout


def test_seed_and_verify_commands_emit_machine_readable_evidence(tmp_path: Path) -> None:
    database = tmp_path / "qsparx.sqlite3"
    seed_result = runner.invoke(
        app,
        ["seed", "--world", "world-reviewer", "--database", str(database), "--seed", "577"],
    )
    verify_result = runner.invoke(app, ["verify", "--runs", "3", "--seed", "577"])

    assert seed_result.exit_code == 0, seed_result.output
    seeded = json.loads(seed_result.stdout)
    assert seeded["world_id"] == "world-reviewer"
    assert seeded["data_label"] == "synthetic"
    assert seeded["authority_label"] == "non_authoritative"
    assert seeded["records"] > 0

    assert verify_result.exit_code == 0, verify_result.output
    verified = json.loads(verify_result.stdout)
    assert verified["canonical_digests_match"] is True
    assert verified["effects_applied"] is False
    assert verified["runs"] == 3


def test_ingest_and_remaining_commands_are_executable(tmp_path: Path) -> None:
    cbom = tmp_path / "fixture.cdx.json"
    cbom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.7",
                "components": [
                    {
                        "type": "cryptographic-asset",
                        "bom-ref": "crypto:test",
                        "name": "RSA-2048",
                        "cryptoProperties": {"assetType": "algorithm"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    invocations = [
        ["ingest", str(cbom)],
        ["inventory", "--seed", "577"],
        ["assess", "--seed", "577"],
        ["detect", "--seed", "577"],
        ["plan", "--world", "world-reviewer", "--seed", "577"],
        ["simulate", "--world", "world-reviewer", "--seed", "577"],
        ["benchmark", "--repetitions", "2", "--seed", "577"],
    ]

    for arguments in invocations:
        result = runner.invoke(app, arguments)
        assert result.exit_code == 0, f"{arguments}: {result.output}"
        assert json.loads(result.stdout)


def test_benchmark_supports_named_suite_and_output_file(tmp_path: Path) -> None:
    output = tmp_path / "benchmark.json"

    result = runner.invoke(
        app,
        [
            "benchmark",
            "--suite",
            "smoke",
            "--repetitions",
            "2",
            "--seed",
            "577",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["suite"] == "smoke"
    assert report["repetitions"] == 2


def test_ingest_supports_every_passive_adapter_without_connector_calls(tmp_path: Path) -> None:
    fixture = tmp_path / "synthetic-export.json"
    fixture.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.7",
                "components": [
                    {
                        "type": "cryptographic-asset",
                        "bom-ref": "crypto:test",
                        "name": "ML-KEM-768",
                        "cryptoProperties": {"assetType": "algorithm"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    adapters = [
        "auto",
        "source",
        "dependency",
        "binary",
        "container",
        "tls",
        "ssh",
        "pki",
        "keystore",
        "aws-kms",
        "azure-pki",
        "cyclonedx",
    ]

    for adapter in adapters:
        result = runner.invoke(app, ["ingest", str(fixture), "--adapter", adapter])
        assert result.exit_code == 0, f"{adapter}: {result.output}"
        report = json.loads(result.stdout)
        assert report["requested_adapter"] == adapter
        assert report["passive"] is True
        assert report["real_connector_calls"] == 0
        assert report["records"]


def test_seed_scale_profile_writes_streamed_corpus(tmp_path: Path) -> None:
    output = tmp_path / "scale"

    result = runner.invoke(
        app,
        [
            "seed",
            "--profile",
            "scale-v1",
            "--assets",
            "10",
            "--observations",
            "100",
            "--output",
            str(output),
            "--seed",
            "577",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads(result.stdout)
    assert manifest["asset_count"] == 10
    assert manifest["observation_count"] == 100
    assert (output / "observations.ndjson.gz").is_file()


def test_verify_binds_an_evaluation_manifest(tmp_path: Path) -> None:
    digest = lambda character: "sha256:" + character * 64  # noqa: E731
    manifest_path = tmp_path / "evaluation-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "record_id": "evaluation:v0.2.0-rc.1",
                "schema_version": "1.0.0",
                "provenance": {
                    "source_type": "sealed_release",
                    "source_uri": "github://577Industries/forge-qbit-qsparx/v0.2.0-rc.1",
                    "collected_at": "2026-07-21T12:00:00Z",
                    "collector": "pytest",
                },
                "source_confidence": 1.0,
                "valid_from": "2026-07-21T12:00:00Z",
                "artifact_digest": digest("a"),
                "data_label": "synthetic",
                "authority_label": "measured_synthetic",
                "release_tag": "v0.2.0-rc.1",
                "source_commit": "b" * 40,
                "image_digest": digest("b"),
                "preregistration_digest": digest("c"),
                "corpus_digest": digest("d"),
                "labels_digest": digest("e"),
                "split_digest": digest("f"),
                "model_digest": digest("1"),
                "environment_digest": digest("2"),
                "raw_outputs_digest": digest("3"),
                "threshold_revision": 1,
                "results_digest": digest("4"),
                "limitations": ["Synthetic sealed corpus only."],
                "validator_report_digests": [],
                "validator_status": "not_started",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["verify", "--manifest", str(manifest_path), "--runs", "3"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["manifest_valid"] is True
    assert report["manifest_release_tag"] == "v0.2.0-rc.1"
