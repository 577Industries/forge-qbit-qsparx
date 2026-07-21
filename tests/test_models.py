from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from forge_qsparx.models import (
    BenchmarkReport,
    CryptoAsset,
    CryptoRelationship,
    Detection,
    EvaluationManifest,
    EvidenceManifest,
    Finding,
    InteropCaseResult,
    MigrationPlan,
    MissionContext,
    Observation,
    PolicyResult,
    RiskAssessment,
    SimulationRun,
)

PUBLIC_MODELS = (
    MissionContext,
    CryptoAsset,
    CryptoRelationship,
    Observation,
    Finding,
    RiskAssessment,
    Detection,
    MigrationPlan,
    SimulationRun,
    PolicyResult,
    EvidenceManifest,
    EvaluationManifest,
    BenchmarkReport,
    InteropCaseResult,
)


def evidence_envelope() -> dict[str, object]:
    valid_from = datetime(2026, 7, 21, tzinfo=UTC)
    return {
        "record_id": "asset:example",
        "schema_version": "1.0.0",
        "provenance": {
            "source_type": "synthetic_generator",
            "source_uri": "forge-qsparx://synthetic/test",
            "collected_at": valid_from,
            "collector": "pytest",
        },
        "source_confidence": 1.0,
        "valid_from": valid_from,
        "valid_until": valid_from + timedelta(days=1),
        "artifact_digest": "sha256:" + "a" * 64,
        "data_label": "synthetic",
        "authority_label": "non_authoritative",
    }


@pytest.mark.parametrize("model", PUBLIC_MODELS)
def test_every_public_record_requires_the_evidence_envelope(model: type[object]) -> None:
    with pytest.raises(ValidationError) as error:
        model.model_validate({})  # type: ignore[attr-defined]

    missing = {item["loc"][0] for item in error.value.errors()}
    assert {
        "record_id",
        "schema_version",
        "provenance",
        "source_confidence",
        "valid_from",
        "artifact_digest",
        "data_label",
        "authority_label",
    } <= missing


def test_evidence_envelope_rejects_invalid_digest_confidence_and_window() -> None:
    payload = evidence_envelope()
    payload.update(
        {
            "name": "Fictional service",
            "description": "Synthetic mission context",
            "source_confidence": 1.1,
            "artifact_digest": "not-a-digest",
            "valid_until": datetime(2026, 7, 20, tzinfo=UTC),
        }
    )

    with pytest.raises(ValidationError) as error:
        MissionContext.model_validate(payload)

    messages = " ".join(item["msg"] for item in error.value.errors())
    assert "less than or equal to 1" in messages
    assert "sha256" in messages
    assert "valid_until" in messages


def test_synthetic_records_cannot_claim_government_authority() -> None:
    payload = evidence_envelope()
    payload.update(
        {
            "name": "Fictional service",
            "description": "Synthetic mission context",
            "authority_label": "government_validated",
        }
    )

    with pytest.raises(ValidationError, match="synthetic records cannot claim"):
        MissionContext.model_validate(payload)


def evaluation_manifest_payload() -> dict[str, object]:
    payload = evidence_envelope()
    payload.update(
        {
            "record_id": "evaluation:v0.2.0-rc.1",
            "authority_label": "measured_synthetic",
            "release_tag": "v0.2.0-rc.1",
            "source_commit": "b" * 40,
            "image_digest": "sha256:" + "b" * 64,
            "preregistration_digest": "sha256:" + "c" * 64,
            "corpus_digest": "sha256:" + "d" * 64,
            "labels_digest": "sha256:" + "e" * 64,
            "split_digest": "sha256:" + "f" * 64,
            "model_digest": "sha256:" + "1" * 64,
            "environment_digest": "sha256:" + "2" * 64,
            "raw_outputs_digest": "sha256:" + "3" * 64,
            "threshold_revision": 1,
            "results_digest": "sha256:" + "4" * 64,
            "limitations": ["Synthetic sealed corpus only."],
            "validator_status": "not_started",
        }
    )
    return payload


def test_evaluation_manifest_binds_all_frozen_inputs() -> None:
    manifest = EvaluationManifest.model_validate(evaluation_manifest_payload())

    assert manifest.release_tag == "v0.2.0-rc.1"
    assert manifest.threshold_revision == 1
    assert manifest.labels_digest != manifest.corpus_digest


def test_evaluation_manifest_allows_at_most_one_threshold_revision() -> None:
    payload = evaluation_manifest_payload()
    payload["threshold_revision"] = 2

    with pytest.raises(ValidationError, match="less than or equal to 1"):
        EvaluationManifest.model_validate(payload)


def test_independent_validation_requires_two_distinct_reports() -> None:
    payload = evaluation_manifest_payload()
    payload["authority_label"] = "independently_validated"
    payload["validator_status"] = "independently_validated"
    payload["validator_report_digests"] = ["sha256:" + "5" * 64]

    with pytest.raises(ValidationError, match="two distinct validator reports"):
        EvaluationManifest.model_validate(payload)
