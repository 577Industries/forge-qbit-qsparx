from datetime import UTC, datetime

from forge_qsparx.canonical import ContentAddressedStore, canonical_digest
from forge_qsparx.engine import QsparxEngine, build_evidence_manifest
from forge_qsparx.synthetic import generate_mission


def test_risk_assessments_are_ranked_and_fully_decomposable() -> None:
    engine = QsparxEngine(generate_mission(seed=577))

    assessments = engine.assess()

    assert assessments == sorted(assessments, key=lambda item: (-item.score, item.asset_id))
    assert assessments[0].asset_id == "asset:directory-jks"
    assert all(
        assessment.score == min(100.0, sum(factor.points for factor in assessment.factors))
        for assessment in assessments
    )
    assert all(factor.evidence_ids for item in assessments for factor in item.factors)
    assert all(0.0 <= item.uncertainty <= 1.0 for item in assessments)
    assert any(
        factor.factor_id == "graph_mission_impact"
        for item in assessments
        for factor in item.factors
    )


def test_detections_are_evidence_grounded_and_rules_own_policy() -> None:
    engine = QsparxEngine(generate_mission(seed=577))

    detections = engine.detect()

    assert {item.detection_type for item in detections} >= {
        "prohibited_legacy_primitive",
        "harvest_now_decrypt_later_exposure",
    }
    assert all(item.detector == "deterministic_rule" for item in detections)
    assert all(item.advisory_only for item in detections)
    assert all(item.evidence_ids for item in detections)


def test_migration_simulation_is_world_bound_deterministic_and_effect_free() -> None:
    engine = QsparxEngine(generate_mission(seed=577))

    plan = engine.plan(world_id="world-reviewer")
    first = engine.simulate(plan)
    second = engine.simulate(plan)

    assert plan.world_id == "world-reviewer"
    assert plan.approval_required is True
    assert plan.live_remediation_allowed is False
    assert all(action.rollback for wave in plan.waves for action in wave.actions)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.world_id == plan.world_id
    assert first.rollback_verified is True
    assert first.effects_applied is False


def test_evidence_manifest_root_digest_covers_ordered_entries(tmp_path: object) -> None:
    store = ContentAddressedStore(tmp_path)  # type: ignore[arg-type]
    inventory = store.put_json({"kind": "inventory", "count": 14})
    risks = store.put_json({"kind": "risk", "count": 14})

    manifest = build_evidence_manifest(
        release_id="v0.1.1-reviewer",
        artifacts=[inventory, risks],
        valid_from=datetime(2026, 7, 21, tzinfo=UTC),
    )

    expected = canonical_digest(
        [
            {"digest": item.digest, "media_type": item.media_type, "path": item.path}
            for item in manifest.entries
        ]
    )
    assert manifest.root_digest == expected
    assert manifest.validator_status == "not_started"
    assert manifest.claim_states == ["background_implemented", "measured_synthetic"]
