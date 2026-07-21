"""Explainable deterministic risk, detection, migration, and simulation engine."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import networkx as nx

from forge_qsparx.canonical import ArtifactReference, canonical_digest
from forge_qsparx.models import (
    SCHEMA_VERSION,
    CryptoAsset,
    Detection,
    EvidenceEntry,
    EvidenceManifest,
    MigrationAction,
    MigrationPlan,
    MigrationWave,
    Provenance,
    RiskAssessment,
    RiskFactor,
    Severity,
    SimulationRun,
)
from forge_qsparx.synthetic import SyntheticMission

PUBLIC_KEY_MARKERS = ("RSA", "ECDSA", "ECDH", "ECDHE", "DH-")
WEAK_MARKERS = ("RSA-1024", "SHA-1", "SHA1", "3DES", "DES-")


def _severity(score: float) -> Severity:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    if score > 0:
        return "low"
    return "info"


class QsparxEngine:
    """Side-effect-free public engine operating on one synthetic mission."""

    def __init__(self, mission: SyntheticMission) -> None:
        self.mission = mission
        self._assets = {asset.record_id: asset for asset in mission.assets}
        self._observations = {item.asset_id: item for item in mission.observations}
        self._graph = nx.DiGraph()
        self._graph.add_nodes_from(self._assets)
        self._graph.add_edges_from(
            (item.source_asset_id, item.target_asset_id, {"impact": item.mission_impact})
            for item in mission.relationships
        )

    def inventory(self) -> list[CryptoAsset]:
        return sorted(self.mission.assets, key=lambda item: item.record_id)

    def _envelope(self, record_id: str, payload: Any) -> dict[str, Any]:
        context = self.mission.context
        return {
            "record_id": record_id,
            "schema_version": SCHEMA_VERSION,
            "provenance": {
                "source_type": "deterministic_qsparx_engine",
                "source_uri": context.provenance.source_uri,
                "collected_at": context.provenance.collected_at,
                "collector": "forge_qsparx.engine.QsparxEngine",
            },
            "source_confidence": 1.0,
            "valid_from": context.valid_from,
            "valid_until": context.valid_until,
            "artifact_digest": canonical_digest(payload),
            "data_label": "synthetic",
            "authority_label": "measured_synthetic",
        }

    def _evidence_id(self, asset: CryptoAsset) -> str:
        observation = self._observations.get(asset.record_id)
        return observation.record_id if observation else asset.record_id

    def _risk_factors(self, asset: CryptoAsset) -> list[RiskFactor]:
        algorithm = (asset.algorithm or "").upper()
        evidence = [self._evidence_id(asset)]
        factors: list[RiskFactor] = []
        if any(marker in algorithm for marker in WEAK_MARKERS):
            points = 45.0 if "RSA-1024" in algorithm else 40.0
            factors.append(
                RiskFactor(
                    factor_id="prohibited_legacy_primitive",
                    label="Legacy cryptographic primitive",
                    points=points,
                    evidence_ids=evidence,
                    rationale=f"{asset.algorithm} is a deterministic legacy-risk trigger.",
                )
            )
        if any(marker in algorithm for marker in PUBLIC_KEY_MARKERS):
            factors.append(
                RiskFactor(
                    factor_id="quantum_vulnerable_public_key",
                    label="Quantum-vulnerable public-key primitive",
                    points=35.0,
                    evidence_ids=evidence,
                    rationale=f"{asset.algorithm} requires a migration path to approved PQC.",
                )
            )
        if asset.data_lifetime_years >= 10:
            factors.append(
                RiskFactor(
                    factor_id="long_lived_data",
                    label="Long-lived confidentiality requirement",
                    points=20.0,
                    evidence_ids=evidence,
                    rationale=f"Data lifetime is {asset.data_lifetime_years} years.",
                )
            )
        elif asset.data_lifetime_years >= 5:
            factors.append(
                RiskFactor(
                    factor_id="extended_data_lifetime",
                    label="Extended confidentiality requirement",
                    points=10.0,
                    evidence_ids=evidence,
                    rationale=f"Data lifetime is {asset.data_lifetime_years} years.",
                )
            )
        if asset.internet_exposed:
            factors.append(
                RiskFactor(
                    factor_id="external_exposure",
                    label="Externally reachable cryptographic surface",
                    points=10.0,
                    evidence_ids=evidence,
                    rationale="Synthetic inventory marks this surface internet exposed.",
                )
            )
        connected_outage = any(
            data.get("impact") == "outage"
            for _, _, data in list(self._graph.in_edges(asset.record_id, data=True))
            + list(self._graph.out_edges(asset.record_id, data=True))
        )
        if connected_outage:
            factors.append(
                RiskFactor(
                    factor_id="graph_mission_impact",
                    label="Mission graph outage propagation",
                    points=15.0,
                    evidence_ids=[
                        item.record_id
                        for item in self.mission.relationships
                        if asset.record_id in {item.source_asset_id, item.target_asset_id}
                        and item.mission_impact == "outage"
                    ],
                    rationale="An adjacent dependency is labeled as outage-propagating.",
                )
            )
        if not factors:
            factors.append(
                RiskFactor(
                    factor_id="no_rule_trigger",
                    label="No deterministic risk trigger",
                    points=0.0,
                    evidence_ids=evidence,
                    rationale="The current rule pack found no scored condition.",
                )
            )
        return factors

    def assess(self) -> list[RiskAssessment]:
        assessments: list[RiskAssessment] = []
        for asset in self.mission.assets:
            factors = self._risk_factors(asset)
            score = min(100.0, sum(factor.points for factor in factors))
            payload = {
                "asset_id": asset.record_id,
                "score": score,
                "factors": [factor.model_dump(mode="json") for factor in factors],
            }
            assessments.append(
                RiskAssessment(
                    **self._envelope(f"risk:{asset.record_id.split(':', 1)[1]}", payload),
                    asset_id=asset.record_id,
                    score=score,
                    severity=_severity(score),
                    factors=factors,
                    uncertainty=round(max(0.0, 1.0 - asset.source_confidence) + 0.1, 3),
                    policy_pack="forge-qsparx-baseline-1.0.0",
                )
            )
        return sorted(assessments, key=lambda item: (-item.score, item.asset_id))

    def detect(self) -> list[Detection]:
        detections: list[Detection] = []
        for asset in self.mission.assets:
            algorithm = (asset.algorithm or "").upper()
            evidence = [self._evidence_id(asset)]
            detection_specs: list[tuple[str, Severity, str]] = []
            if any(marker in algorithm for marker in WEAK_MARKERS):
                detection_specs.append(
                    (
                        "prohibited_legacy_primitive",
                        "critical",
                        f"Rule LEGACY-001 matched {asset.algorithm}.",
                    )
                )
            if asset.data_lifetime_years >= 5 and any(
                marker in algorithm for marker in PUBLIC_KEY_MARKERS
            ):
                detection_specs.append(
                    (
                        "harvest_now_decrypt_later_exposure",
                        "high",
                        (
                            f"Rule HNDL-001 matched {asset.algorithm} with a "
                            f"{asset.data_lifetime_years}-year data lifetime."
                        ),
                    )
                )
            for detection_type, severity, explanation in detection_specs:
                payload = {
                    "asset_id": asset.record_id,
                    "type": detection_type,
                    "explanation": explanation,
                }
                detections.append(
                    Detection(
                        **self._envelope(
                            f"detection:{asset.record_id.split(':', 1)[1]}:{detection_type}",
                            payload,
                        ),
                        asset_id=asset.record_id,
                        detection_type=detection_type,
                        severity=severity,
                        explanation=explanation,
                        evidence_ids=evidence,
                        detector="deterministic_rule",
                        advisory_only=True,
                    )
                )
        return sorted(detections, key=lambda item: (item.asset_id, item.detection_type))

    def _target_state(self, asset: CryptoAsset) -> str:
        algorithm = (asset.algorithm or "").upper()
        if "SHA" in algorithm:
            return "approved SHA-2/SHA-3 profile with crypto-agile configuration"
        if asset.asset_type in {"certificate", "key"} or any(
            marker in algorithm for marker in ("ECDSA", "RSA")
        ):
            return "hybrid signature profile leading to ML-DSA or SLH-DSA"
        if any(marker in algorithm for marker in ("ECDH", "ECDHE", "DH-")):
            return "hybrid key establishment profile leading to ML-KEM"
        return "crypto-agile approved algorithm profile"

    def plan(self, *, world_id: str) -> MigrationPlan:
        assessments = [item for item in self.assess() if item.score >= 35]
        weak_assets = {
            item.asset_id
            for item in assessments
            if any(factor.factor_id == "prohibited_legacy_primitive" for factor in item.factors)
        }
        long_lived_assets = {
            item.asset_id
            for item in assessments
            if any(
                factor.factor_id in {"long_lived_data", "extended_data_lifetime"}
                for factor in item.factors
            )
        } - weak_assets
        remaining_assets = {item.asset_id for item in assessments} - weak_assets - long_lived_assets
        groups = [
            ("Remove immediately weak primitives", weak_assets),
            ("Protect long-lived mission data", long_lived_assets),
            ("Complete dependency-aware crypto-agility migration", remaining_assets),
        ]
        waves: list[MigrationWave] = []
        for objective, asset_ids in groups:
            if not asset_ids:
                continue
            actions = [
                MigrationAction(
                    asset_id=asset_id,
                    from_state=self._assets[asset_id].algorithm or "unknown cryptographic state",
                    target_state=self._target_state(self._assets[asset_id]),
                    rationale=(
                        "Deterministic risk factors require a reversible migration experiment."
                    ),
                    rollback=(
                        "Restore the sealed pre-simulation asset snapshot and verify its digest."
                    ),
                )
                for asset_id in sorted(asset_ids)
            ]
            waves.append(
                MigrationWave(
                    wave=len(waves) + 1,
                    objective=objective,
                    actions=actions,
                    entry_criteria=[
                        "Approval token bound to this world and plan",
                        "Compatibility fixture and rollback snapshot available",
                    ],
                    exit_criteria=[
                        "Expected-compatible cases pass",
                        "Expected-incompatible cases fail with expected diagnosis",
                        "Rollback digest matches the sealed snapshot",
                    ],
                )
            )
        payload = {
            "world_id": world_id,
            "waves": [wave.model_dump(mode="json") for wave in waves],
        }
        return MigrationPlan(
            **self._envelope(f"plan:{canonical_digest(payload)[7:23]}", payload),
            title="Synthetic QSPARX PQC migration waves",
            world_id=world_id,
            waves=waves,
            approval_required=True,
            live_remediation_allowed=False,
        )

    def simulate(self, plan: MigrationPlan) -> SimulationRun:
        actions = [action for wave in plan.waves for action in wave.actions]
        incompatibilities = [
            f"{action.asset_id}: legacy JKS consumer lacks PQC support"
            for action in actions
            if self._assets[action.asset_id].asset_type == "keystore"
        ]
        payload = {
            "plan_id": plan.record_id,
            "world_id": plan.world_id,
            "actions": [action.model_dump(mode="json") for action in actions],
            "compatibility_failures": incompatibilities,
        }
        return SimulationRun(
            **self._envelope(f"simulation:{canonical_digest(payload)[7:23]}", payload),
            plan_id=plan.record_id,
            world_id=plan.world_id,
            status="completed",
            latency_delta_ms=round(len(actions) * 2.5, 3),
            compatibility_failures=incompatibilities,
            mission_impact="degraded" if incompatibilities else "none",
            rollback_verified=True,
            effects_applied=False,
        )


def build_evidence_manifest(
    *,
    release_id: str,
    artifacts: Iterable[ArtifactReference],
    valid_from: datetime,
) -> EvidenceManifest:
    references = sorted(artifacts, key=lambda item: item.digest)
    entries = [
        EvidenceEntry(
            path="/".join(reference.path.parts[-3:]),
            digest=reference.digest,
            media_type=reference.media_type,
            claim_state="measured_synthetic",
            limitation="Synthetic, non-authoritative evidence; independent validation not started.",
        )
        for reference in references
    ]
    covered = [
        {"digest": item.digest, "media_type": item.media_type, "path": item.path}
        for item in entries
    ]
    root_digest = canonical_digest(covered)
    return EvidenceManifest(
        record_id=f"manifest:{release_id}",
        schema_version=SCHEMA_VERSION,
        provenance=Provenance(
            source_type="content_addressed_manifest",
            source_uri=f"forge-qsparx://release/{release_id}",
            collected_at=valid_from,
            collector="forge_qsparx.engine.build_evidence_manifest",
        ),
        source_confidence=1.0,
        valid_from=valid_from,
        valid_until=None,
        artifact_digest=root_digest,
        data_label="synthetic",
        authority_label="background_implemented",
        release_id=release_id,
        entries=entries,
        root_digest=root_digest,
        claim_states=["background_implemented", "measured_synthetic"],
        validator_status="not_started",
    )
