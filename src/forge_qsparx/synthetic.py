"""Deterministic, fictional NCR communications mission generator."""

from __future__ import annotations

import gzip
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from forge_qsparx.canonical import canonical_digest, canonical_json
from forge_qsparx.models import (
    SCHEMA_VERSION,
    CryptoAsset,
    CryptoRelationship,
    MissionContext,
    MissionImpact,
    MissionService,
    Observation,
    RelationshipType,
)

FIXED_EPOCH = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
SCALE_ADAPTERS = (
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
)
SCALE_ALGORITHMS = (
    "RSA-1024",
    "RSA-2048",
    "ECDSA-P256",
    "AES-256-GCM",
    "SHA-1",
    "ML-KEM-768",
    "ML-DSA-65",
)


@dataclass(frozen=True)
class SyntheticMission:
    seed: int
    context: MissionContext
    assets: tuple[CryptoAsset, ...]
    relationships: tuple[CryptoRelationship, ...]
    observations: tuple[Observation, ...]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def generate_scale_corpus(
    output_dir: Path, *, seed: int = 577, assets: int = 10_000, observations: int = 1_000_000
) -> dict[str, Any]:
    """Stream a deterministic compressed scale corpus and frozen truth manifest."""

    if assets < 1 or observations < 1:
        raise ValueError("assets and observations must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_path = output_dir / "assets.ndjson.gz"
    observations_path = output_dir / "observations.ndjson.gz"
    modality_distribution = {adapter: 0 for adapter in SCALE_ADAPTERS}

    with (
        assets_path.open("wb") as raw_assets,
        gzip.GzipFile(fileobj=raw_assets, mode="wb", mtime=0) as compressed_assets,
    ):
        for index in range(assets):
            adapter = SCALE_ADAPTERS[(index + seed) % len(SCALE_ADAPTERS)]
            modality_distribution[adapter] += 1
            asset_record = {
                "asset_id": f"asset:scale-v1:{index:05d}",
                "service_id": f"svc-scale-{index % 40:02d}",
                "adapter": adapter,
                "algorithm": SCALE_ALGORITHMS[(index * 3 + seed) % len(SCALE_ALGORITHMS)],
                "severity": ("low", "medium", "high", "critical")[(index + seed) % 4],
                "expected_inventory": index % 211 != 0,
                "ground_truth": True,
                "data_label": "synthetic",
                "authority_label": "non_authoritative",
            }
            compressed_assets.write(canonical_json(asset_record) + b"\n")

    fixture_counts = {"duplicates": 0, "stale": 0, "malformed": 0, "expected_omissions": 0}
    with (
        observations_path.open("wb") as raw_observations,
        gzip.GzipFile(fileobj=raw_observations, mode="wb", mtime=0) as compressed_observations,
    ):
        for index in range(observations):
            asset_index = (index * 37 + seed) % assets
            duplicate = index > 0 and index % 997 == 0
            stale = index % 991 == 0
            malformed = index % 4999 == 0
            expected_omission = asset_index % 211 == 0
            fixture_counts["duplicates"] += int(duplicate)
            fixture_counts["stale"] += int(stale)
            fixture_counts["malformed"] += int(malformed)
            fixture_counts["expected_omissions"] += int(expected_omission)
            observation_record: dict[str, Any] = {
                "observation_id": f"observation:scale-v1:{index:07d}",
                "asset_id": f"asset:scale-v1:{asset_index:05d}",
                "adapter": SCALE_ADAPTERS[(asset_index + seed) % len(SCALE_ADAPTERS)],
                "observed_at": (
                    FIXED_EPOCH - timedelta(days=400)
                    if stale
                    else FIXED_EPOCH + timedelta(seconds=index)
                ).isoformat(),
                "duplicate_of": (f"observation:scale-v1:{index - 1:07d}" if duplicate else None),
                "malformed_fixture": malformed,
                "expected_omission": expected_omission,
                "data_label": "synthetic",
                "authority_label": "non_authoritative",
            }
            compressed_observations.write(canonical_json(observation_record) + b"\n")

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "profile": "scale-v1",
        "seed": seed,
        "asset_count": assets,
        "observation_count": observations,
        "modality_distribution": modality_distribution,
        "fixture_counts": fixture_counts,
        "file_digests": {
            "assets.ndjson.gz": _sha256_file(assets_path),
            "observations.ndjson.gz": _sha256_file(observations_path),
        },
        "data_label": "synthetic",
        "authority_label": "non_authoritative",
        "claim_state": "background_implemented",
        "limitation": "Generator output only; acceptance metrics require a sealed evaluation run.",
    }
    (output_dir / "truth.json").write_bytes(canonical_json(manifest) + b"\n")
    return manifest


def _envelope(record_id: str, seed: int, payload: Any) -> dict[str, Any]:
    collected_at = FIXED_EPOCH + timedelta(seconds=seed % 3600)
    return {
        "record_id": record_id,
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "source_type": "synthetic_generator",
            "source_uri": f"forge-qsparx://synthetic/ncr-communications?seed={seed}",
            "collected_at": collected_at,
            "collector": "forge_qsparx.synthetic.generate_mission",
        },
        "source_confidence": 1.0,
        "valid_from": collected_at,
        "valid_until": collected_at + timedelta(days=365),
        "artifact_digest": canonical_digest(payload),
        "data_label": "synthetic",
        "authority_label": "non_authoritative",
    }


def generate_mission(seed: int = 577) -> SyntheticMission:
    """Build a stable, non-authoritative communications mission fixture."""

    services = [
        MissionService(
            service_id="svc-messaging",
            name="Executive Messaging Relay",
            criticality="mission_essential",
            description="Fictional command messaging and notification relay.",
        ),
        MissionService(
            service_id="svc-directory",
            name="Identity and Directory",
            criticality="mission_essential",
            description="Fictional authentication and directory service.",
        ),
        MissionService(
            service_id="svc-records",
            name="Long-Lived Records Exchange",
            criticality="important",
            description="Fictional exchange for records with extended confidentiality life.",
        ),
        MissionService(
            service_id="svc-portal",
            name="Mission Support Portal",
            criticality="support",
            description="Fictional internal mission support application.",
        ),
    ]
    context_payload = {
        "seed": seed,
        "services": [item.model_dump(mode="json") for item in services],
    }
    context = MissionContext(
        **_envelope("mission:fictional-ncr-comms", seed, context_payload),
        name="Fictional NCR Communications Mission",
        description=(
            "A fictional, non-authoritative communications mission twin informed only by "
            "public descriptions of NCR communications support responsibilities."
        ),
        services=services,
        migration_constraints=[
            "No live remediation or active target scanning",
            "At least one tested rollback path per migration wave",
            "Legacy consumers may require hybrid compatibility windows",
            "Synthetic world changes require explicit approval",
        ],
    )

    specs: list[dict[str, Any]] = [
        {
            "id": "asset:message-api",
            "name": "Messaging API",
            "asset_type": "application",
            "service": "svc-messaging",
            "platform": "Windows Server 2022",
            "implementation": ".NET 8",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "modality": "source",
            "lifetime": 8,
            "exposed": True,
            "vendor": "Fictional Integrator",
        },
        {
            "id": "asset:directory-service",
            "name": "Directory Broker",
            "asset_type": "application",
            "service": "svc-directory",
            "platform": "RHEL 9",
            "implementation": "Java 21",
            "algorithm": "SHA-1",
            "modality": "dependency",
            "lifetime": 1,
            "vendor": "Fictional Integrator",
        },
        {
            "id": "asset:records-worker",
            "name": "Records Transfer Worker",
            "asset_type": "application",
            "service": "svc-records",
            "platform": "RHEL 9",
            "implementation": "Python 3.12",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "modality": "binary",
            "lifetime": 15,
            "vendor": "Open Source",
        },
        {
            "id": "asset:support-portal",
            "name": "Support Portal Container",
            "asset_type": "container",
            "service": "svc-portal",
            "platform": "RHEL 9",
            "implementation": "JavaScript/Node.js 22",
            "algorithm": "ECDSA-P256",
            "key_size": 256,
            "modality": "container",
            "lifetime": 2,
            "vendor": "Fictional Integrator",
        },
        {
            "id": "asset:tls-relay",
            "name": "TLS Relay",
            "asset_type": "protocol",
            "service": "svc-messaging",
            "platform": "RHEL 9",
            "implementation": "OpenSSL 3",
            "algorithm": "ECDHE-P256",
            "key_size": 256,
            "protocol_version": "TLS 1.2",
            "modality": "protocol",
            "lifetime": 8,
            "exposed": True,
            "vendor": "OpenSSL",
        },
        {
            "id": "asset:ssh-admin",
            "name": "Administrative SSH",
            "asset_type": "protocol",
            "service": "svc-directory",
            "platform": "RHEL 9",
            "implementation": "OpenSSH 9",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "protocol_version": "SSH 2",
            "modality": "protocol",
            "lifetime": 0,
            "vendor": "OpenBSD",
        },
        {
            "id": "asset:relay-cert",
            "name": "Relay X.509 Certificate",
            "asset_type": "certificate",
            "service": "svc-messaging",
            "platform": "Windows Server 2022",
            "implementation": "AD CS export",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "modality": "pki",
            "lifetime": 8,
            "vendor": "Fictional CA",
        },
        {
            "id": "asset:relay-key",
            "name": "Relay Private Key Reference",
            "asset_type": "key",
            "service": "svc-messaging",
            "platform": "Windows Server 2022",
            "implementation": "CNG key reference",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "modality": "pki",
            "lifetime": 8,
            "vendor": "Fictional CA",
        },
        {
            "id": "asset:directory-jks",
            "name": "Directory Java Keystore",
            "asset_type": "keystore",
            "service": "svc-directory",
            "platform": "RHEL 9",
            "implementation": "JKS metadata export",
            "algorithm": "RSA-1024",
            "key_size": 1024,
            "modality": "binary",
            "lifetime": 1,
            "vendor": "Fictional Integrator",
        },
        {
            "id": "asset:aws-kms-export",
            "name": "Passive AWS KMS Key Export",
            "asset_type": "kms_reference",
            "service": "svc-records",
            "platform": "AWS commercial fixture",
            "implementation": "AWS KMS metadata export",
            "algorithm": "RSA-2048",
            "key_size": 2048,
            "modality": "cloud_export",
            "lifetime": 15,
            "vendor": "Synthetic AWS",
        },
        {
            "id": "asset:azure-pki-export",
            "name": "Passive Azure Key Vault Export",
            "asset_type": "kms_reference",
            "service": "svc-portal",
            "platform": "Azure commercial fixture",
            "implementation": "Azure Key Vault metadata export",
            "algorithm": "ECDSA-P256",
            "key_size": 256,
            "modality": "cloud_export",
            "lifetime": 2,
            "vendor": "Synthetic Azure",
        },
        {
            "id": "asset:archive-store",
            "name": "Encrypted Archive Store",
            "asset_type": "data_store",
            "service": "svc-records",
            "platform": "RHEL 9",
            "implementation": "LUKS2 metadata",
            "algorithm": "AES-256-GCM",
            "key_size": 256,
            "modality": "sbom_cbom",
            "lifetime": 15,
            "vendor": "Open Source",
        },
        {
            "id": "asset:crypto-library",
            "name": "Application Crypto Dependency",
            "asset_type": "library",
            "service": "svc-portal",
            "platform": "RHEL 9",
            "implementation": "OpenSSL 3",
            "algorithm": "AES-128-CBC",
            "key_size": 128,
            "modality": "dependency",
            "lifetime": 2,
            "vendor": "OpenSSL",
        },
        {
            "id": "asset:ml-kem-lab",
            "name": "ML-KEM-768 Compatibility Fixture",
            "asset_type": "algorithm",
            "service": "svc-records",
            "platform": "RHEL 9",
            "implementation": "Native standards-capable test harness",
            "algorithm": "ML-KEM-768",
            "key_size": 768,
            "modality": "synthetic_manifest",
            "lifetime": 15,
            "vendor": "Synthetic Lab",
        },
    ]

    assets: list[CryptoAsset] = []
    observations: list[Observation] = []
    for spec in specs:
        payload = {"seed": seed, **spec}
        asset = CryptoAsset(
            **_envelope(spec["id"], seed, payload),
            name=spec["name"],
            asset_type=spec["asset_type"],
            mission_service_id=spec["service"],
            platform=spec["platform"],
            implementation=spec["implementation"],
            algorithm=spec.get("algorithm"),
            key_size=spec.get("key_size"),
            protocol_version=spec.get("protocol_version"),
            data_lifetime_years=spec.get("lifetime", 0),
            internet_exposed=spec.get("exposed", False),
            vendor=spec.get("vendor"),
            discovery_modality=spec["modality"],
            tags=["synthetic", "non-authoritative", spec["service"]],
        )
        assets.append(asset)
        observation_id = f"observation:{spec['id'].split(':', 1)[1]}"
        observations.append(
            Observation(
                **_envelope(
                    observation_id, seed, {"asset": spec["id"], "modality": spec["modality"]}
                ),
                asset_id=spec["id"],
                modality=spec["modality"],
                summary=f"Synthetic passive {spec['modality']} observation for {spec['name']}",
                attributes={"algorithm": spec.get("algorithm", "unknown")},
            )
        )

    relationship_specs: list[tuple[str, str, RelationshipType, MissionImpact]] = [
        ("asset:message-api", "asset:tls-relay", "depends_on", "outage"),
        ("asset:tls-relay", "asset:relay-cert", "authenticates", "outage"),
        ("asset:relay-cert", "asset:relay-key", "depends_on", "outage"),
        ("asset:directory-service", "asset:directory-jks", "depends_on", "outage"),
        ("asset:records-worker", "asset:archive-store", "stores", "degraded"),
        ("asset:records-worker", "asset:aws-kms-export", "depends_on", "outage"),
        ("asset:support-portal", "asset:azure-pki-export", "depends_on", "degraded"),
        ("asset:message-api", "asset:directory-service", "communicates_with", "degraded"),
    ]
    relationships = tuple(
        CryptoRelationship(
            **_envelope(
                f"relationship:{index}",
                seed,
                {"source": source, "target": target, "type": relation},
            ),
            source_asset_id=source,
            target_asset_id=target,
            relationship_type=relation,
            mission_impact=impact,
        )
        for index, (source, target, relation, impact) in enumerate(relationship_specs, start=1)
    )
    return SyntheticMission(
        seed=seed,
        context=context,
        assets=tuple(assets),
        relationships=relationships,
        observations=tuple(observations),
    )
