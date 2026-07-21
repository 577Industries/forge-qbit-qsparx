"""Versioned public records for the cryptographic mission twin.

Every public record inherits :class:`EvidenceRecord`.  That makes evidence
metadata a schema-level obligation rather than a convention for callers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

SchemaVersion = Literal["1.0.0"]
SCHEMA_VERSION: Final[SchemaVersion] = "1.0.0"

ArtifactDigest = Annotated[
    str,
    Field(pattern=r"^sha256:[0-9a-f]{64}$"),
]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Severity = Literal["info", "low", "medium", "high", "critical"]
CryptoAssetType = Literal[
    "application",
    "algorithm",
    "library",
    "container",
    "protocol",
    "certificate",
    "key",
    "keystore",
    "kms_reference",
    "data_store",
    "operating_system",
]
RelationshipType = Literal[
    "depends_on",
    "protects",
    "authenticates",
    "stores",
    "issued_by",
    "communicates_with",
]
MissionImpact = Literal["none", "degraded", "outage"]
ClaimState = Literal[
    "external_authority",
    "background_implemented",
    "measured_synthetic",
    "publicly_reproduced",
    "independently_validated",
    "government_validated",
    "planned_phase_i",
    "planned_phase_ii",
    "non_authoritative",
]


class StrictModel(BaseModel):
    """Base model that rejects silent schema drift."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Provenance(StrictModel):
    source_type: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    collected_at: datetime
    collector: str = Field(min_length=1)


class EvidenceRecord(StrictModel):
    record_id: str = Field(min_length=1)
    schema_version: SchemaVersion
    provenance: Provenance
    source_confidence: Confidence
    valid_from: datetime
    valid_until: datetime | None = None
    artifact_digest: ArtifactDigest
    data_label: Literal["synthetic", "authoritative"]
    authority_label: ClaimState

    @field_validator("valid_until")
    @classmethod
    def validate_window(cls, value: datetime | None, info: ValidationInfo) -> datetime | None:
        valid_from = info.data.get("valid_from")
        if value is not None and isinstance(valid_from, datetime) and value < valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        return value

    @model_validator(mode="after")
    def validate_evidence_labels(self) -> EvidenceRecord:
        if self.data_label == "synthetic" and self.authority_label in {
            "external_authority",
            "government_validated",
        }:
            raise ValueError("synthetic records cannot claim external or government authority")
        return self


class MissionService(StrictModel):
    service_id: str
    name: str
    criticality: Literal["support", "important", "mission_essential"]
    description: str


class MissionContext(EvidenceRecord):
    name: str
    description: str
    fictional_basis: str = "Public mission descriptions; fictional implementation"
    services: list[MissionService] = Field(default_factory=list)
    migration_constraints: list[str] = Field(default_factory=list)


class CryptoAsset(EvidenceRecord):
    name: str
    asset_type: CryptoAssetType
    mission_service_id: str
    platform: str
    implementation: str
    algorithm: str | None = None
    key_size: int | None = Field(default=None, ge=0)
    protocol_version: str | None = None
    data_lifetime_years: int = Field(default=0, ge=0)
    internet_exposed: bool = False
    vendor: str | None = None
    discovery_modality: Literal[
        "source",
        "dependency",
        "binary",
        "container",
        "protocol",
        "pki",
        "sbom_cbom",
        "cloud_export",
        "synthetic_manifest",
    ]
    tags: list[str] = Field(default_factory=list)


class CryptoRelationship(EvidenceRecord):
    source_asset_id: str
    target_asset_id: str
    relationship_type: RelationshipType
    mission_impact: MissionImpact


class Observation(EvidenceRecord):
    asset_id: str
    modality: Literal[
        "source",
        "dependency",
        "binary",
        "container",
        "protocol",
        "pki",
        "sbom_cbom",
        "cloud_export",
        "synthetic_manifest",
    ]
    summary: str
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Finding(EvidenceRecord):
    asset_id: str
    finding_type: str
    title: str
    severity: Severity
    evidence_ids: list[str] = Field(min_length=1)
    limitation: str | None = None


class RiskFactor(StrictModel):
    factor_id: str
    label: str
    points: float = Field(ge=0.0)
    evidence_ids: list[str] = Field(min_length=1)
    rationale: str


class RiskAssessment(EvidenceRecord):
    asset_id: str
    score: float = Field(ge=0.0, le=100.0)
    severity: Severity
    factors: list[RiskFactor] = Field(min_length=1)
    uncertainty: Confidence
    policy_pack: str


class Detection(EvidenceRecord):
    asset_id: str
    detection_type: str
    severity: Severity
    explanation: str
    evidence_ids: list[str] = Field(min_length=1)
    detector: Literal["deterministic_rule", "isolation_forest", "gradient_boosted", "graph"]
    advisory_only: bool = True


class MigrationAction(StrictModel):
    asset_id: str
    from_state: str
    target_state: str
    rationale: str
    rollback: str


class MigrationWave(StrictModel):
    wave: int = Field(ge=1)
    objective: str
    actions: list[MigrationAction] = Field(min_length=1)
    entry_criteria: list[str] = Field(min_length=1)
    exit_criteria: list[str] = Field(min_length=1)


class MigrationPlan(EvidenceRecord):
    title: str
    world_id: str
    waves: list[MigrationWave] = Field(min_length=1)
    approval_required: bool = True
    live_remediation_allowed: Literal[False] = False


class SimulationRun(EvidenceRecord):
    plan_id: str
    world_id: str
    status: Literal["completed", "failed", "rolled_back"]
    latency_delta_ms: float
    compatibility_failures: list[str] = Field(default_factory=list)
    mission_impact: Literal["none", "degraded", "outage"]
    rollback_verified: bool
    effects_applied: Literal[False] = False


class PolicyResult(EvidenceRecord):
    policy_id: str
    subject_id: str
    passed: bool
    rationale: str
    evidence_ids: list[str] = Field(min_length=1)


class EvidenceEntry(StrictModel):
    path: str
    digest: ArtifactDigest
    media_type: str
    claim_state: ClaimState
    limitation: str | None = None


class EvidenceManifest(EvidenceRecord):
    release_id: str
    entries: list[EvidenceEntry] = Field(min_length=1)
    root_digest: ArtifactDigest
    claim_states: list[ClaimState] = Field(min_length=1)
    validator_status: Literal["not_started", "in_progress", "independently_validated"]


class EvaluationManifest(EvidenceRecord):
    """Immutable bindings for a preregistered evaluation release."""

    release_tag: str = Field(pattern=r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    image_digest: ArtifactDigest
    preregistration_digest: ArtifactDigest
    corpus_digest: ArtifactDigest
    labels_digest: ArtifactDigest
    split_digest: ArtifactDigest
    model_digest: ArtifactDigest
    environment_digest: ArtifactDigest
    raw_outputs_digest: ArtifactDigest
    threshold_revision: int = Field(ge=0, le=1)
    results_digest: ArtifactDigest
    limitations: list[str] = Field(min_length=1)
    validator_report_digests: list[ArtifactDigest] = Field(default_factory=list)
    validator_status: Literal["not_started", "in_progress", "independently_validated"]

    @model_validator(mode="after")
    def validate_independent_reports(self) -> EvaluationManifest:
        if (
            self.validator_status == "independently_validated"
            and len(set(self.validator_report_digests)) < 2
        ):
            raise ValueError("independent validation requires two distinct validator reports")
        if self.authority_label == "independently_validated" and self.validator_status != (
            "independently_validated"
        ):
            raise ValueError("independently_validated claims require completed validator reports")
        return self


class BenchmarkReport(EvidenceRecord):
    """Evidence-bearing summary for one benchmark suite."""

    suite: Literal["smoke", "scale", "interop"]
    release_tag: str = Field(pattern=r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    image_digest: ArtifactDigest
    evaluation_manifest_digest: ArtifactDigest
    repetitions: int = Field(ge=1)
    metrics: dict[str, float] = Field(min_length=1)
    result_digest: ArtifactDigest
    limitations: list[str] = Field(min_length=1)
    validator_report_digests: list[ArtifactDigest] = Field(default_factory=list)


class InteropCaseResult(EvidenceRecord):
    """One native or experimental PQC interoperability case result."""

    case_id: str = Field(min_length=1)
    matrix: Literal["native_openssl_3_5", "experimental_oqs"]
    algorithm: str = Field(min_length=1)
    expected_outcome: Literal["compatible", "incompatible"]
    observed_outcome: Literal["passed", "failed"]
    diagnostic_class: str = Field(min_length=1)
    repetitions: int = Field(ge=1)
    confidence_level: Literal["95%"] = "95%"
    latency_ci_ms: tuple[float, float]
    cpu_seconds: float = Field(ge=0.0)
    peak_rss_mib: float = Field(ge=0.0)
    throughput_per_second: float = Field(ge=0.0)
    handshake_or_message_bytes: int = Field(ge=0)
    exit_status: int
    provider_inventory_digest: ArtifactDigest
    raw_command_digest: ArtifactDigest
    limitation: str = Field(min_length=1)
