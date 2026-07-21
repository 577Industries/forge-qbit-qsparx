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
