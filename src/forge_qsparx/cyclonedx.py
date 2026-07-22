"""CycloneDX 1.6/1.7 CBOM interchange boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from forge_qsparx.canonical import canonical_digest
from forge_qsparx.models import SCHEMA_VERSION, CryptoAsset, CryptoAssetType, Provenance

SUPPORTED_IMPORT_VERSIONS = {"1.6", "1.7"}


def _properties(component: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("name")): str(item.get("value", ""))
        for item in component.get("properties", [])
        if isinstance(item, dict) and item.get("name")
    }


def import_cbom(
    document: dict[str, Any],
    *,
    source_uri: str = "memory://cyclonedx",
    collected_at: datetime | None = None,
) -> list[CryptoAsset]:
    if document.get("bomFormat") != "CycloneDX":
        raise ValueError("document is not a CycloneDX BOM")
    version = str(document.get("specVersion", ""))
    if version not in SUPPORTED_IMPORT_VERSIONS:
        raise ValueError("supported CycloneDX versions are 1.6 and 1.7")

    timestamp = collected_at or datetime.now(UTC)
    document_digest = canonical_digest(document)
    assets: list[CryptoAsset] = []
    for index, component in enumerate(document.get("components", []), start=1):
        if not isinstance(component, dict) or component.get("type") != "cryptographic-asset":
            continue
        crypto = component.get("cryptoProperties", {})
        if not isinstance(crypto, dict):
            crypto = {}
        properties = _properties(component)
        asset_kind = str(crypto.get("assetType", "algorithm"))
        asset_type_map: dict[str, CryptoAssetType] = {
            "algorithm": "algorithm",
            "certificate": "certificate",
            "protocol": "protocol",
            "related-crypto-material": "key",
        }
        mapped_kind = asset_type_map.get(asset_kind, "algorithm")
        name = str(component.get("name") or f"CBOM asset {index}")
        parameter = crypto.get("algorithmProperties", {})
        key_size: int | None = None
        if isinstance(parameter, dict):
            raw_size = parameter.get("parameterSetIdentifier")
            if isinstance(raw_size, str) and raw_size.isdigit():
                key_size = int(raw_size)
        record_id = str(
            component.get("bom-ref") or f"cbom:{index}:{canonical_digest(component)[7:19]}"
        )
        assets.append(
            CryptoAsset(
                record_id=record_id,
                schema_version=SCHEMA_VERSION,
                provenance=Provenance(
                    source_type="cyclonedx_cbom",
                    source_uri=source_uri,
                    collected_at=timestamp,
                    collector="forge_qsparx.cyclonedx.import_cbom",
                ),
                source_confidence=0.9,
                valid_from=timestamp,
                valid_until=timestamp + timedelta(days=365),
                artifact_digest=document_digest,
                data_label="synthetic",
                authority_label="non_authoritative",
                name=name,
                asset_type=mapped_kind,
                mission_service_id=properties.get("forge:qsparx:mission-service", "unassigned"),
                platform=properties.get("forge:qsparx:platform", "unknown"),
                implementation=properties.get("forge:qsparx:implementation", "CycloneDX import"),
                algorithm=name
                if mapped_kind == "algorithm"
                else properties.get("forge:qsparx:algorithm"),
                key_size=key_size,
                protocol_version=properties.get("forge:qsparx:protocol-version"),
                data_lifetime_years=int(properties.get("forge:qsparx:data-lifetime-years", "0")),
                internet_exposed=properties.get("forge:qsparx:internet-exposed", "false") == "true",
                vendor=(
                    str(component.get("manufacturer", {}).get("name"))
                    if isinstance(component.get("manufacturer"), dict)
                    else None
                ),
                discovery_modality="sbom_cbom",
                tags=["cyclonedx", f"cyclonedx-{version}"],
            )
        )
    return assets


def _asset_type(asset: CryptoAsset) -> str:
    if asset.asset_type == "protocol":
        return "protocol"
    if asset.asset_type == "certificate":
        return "certificate"
    if asset.asset_type in {"key", "keystore", "kms_reference"}:
        return "related-crypto-material"
    return "algorithm"


def _primitive(algorithm: str | None) -> str:
    normalized = (algorithm or "").upper()
    if "ML-KEM" in normalized:
        return "kem"
    if any(name in normalized for name in ("RSA", "ECDSA", "ML-DSA", "SLH-DSA")):
        return "signature"
    if any(name in normalized for name in ("SHA", "BLAKE")):
        return "hash"
    if "GCM" in normalized:
        return "ae"
    if "AES" in normalized:
        return "block-cipher"
    if any(name in normalized for name in ("ECDH", "ECDHE", "DH")):
        return "key-agree"
    return "unknown"


def _crypto_properties(asset: CryptoAsset) -> dict[str, Any]:
    asset_type = _asset_type(asset)
    properties: dict[str, Any] = {"assetType": asset_type}
    if asset_type == "algorithm":
        algorithm_properties: dict[str, Any] = {
            "primitive": _primitive(asset.algorithm),
            "executionEnvironment": "unknown",
            "implementationPlatform": "other",
            "certificationLevel": ["none"],
        }
        if asset.key_size is not None:
            algorithm_properties["parameterSetIdentifier"] = str(asset.key_size)
        properties["algorithmProperties"] = algorithm_properties
    elif asset_type == "protocol":
        protocol = (
            "tls"
            if "TLS" in asset.name.upper()
            else "ssh"
            if "SSH" in asset.name.upper()
            else "unknown"
        )
        properties["protocolProperties"] = {
            "type": protocol,
            "version": asset.protocol_version or "unknown",
        }
    elif asset_type == "certificate":
        properties["certificateProperties"] = {"certificateFormat": "X.509"}
    return properties


def export_cbom(
    assets: list[CryptoAsset] | tuple[CryptoAsset, ...],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    ordered = sorted(assets, key=lambda item: item.record_id)
    identity_digest = canonical_digest([asset.model_dump(mode="json") for asset in ordered])
    serial = UUID(hex=identity_digest[7:39])
    components: list[dict[str, Any]] = []
    for asset in ordered:
        properties = {
            "forge:qsparx:algorithm": asset.algorithm or "unknown",
            "forge:qsparx:artifact-digest": asset.artifact_digest,
            "forge:qsparx:authority-label": asset.authority_label,
            "forge:qsparx:data-label": asset.data_label,
            "forge:qsparx:data-lifetime-years": str(asset.data_lifetime_years),
            "forge:qsparx:discovery-modality": asset.discovery_modality,
            "forge:qsparx:implementation": asset.implementation,
            "forge:qsparx:internet-exposed": str(asset.internet_exposed).lower(),
            "forge:qsparx:mission-service": asset.mission_service_id,
            "forge:qsparx:original-asset-type": asset.asset_type,
            "forge:qsparx:platform": asset.platform,
            "forge:qsparx:schema-version": asset.schema_version,
        }
        component: dict[str, Any] = {
            "type": "cryptographic-asset",
            "bom-ref": asset.record_id,
            "name": asset.algorithm or asset.name,
            "description": asset.name,
            "cryptoProperties": _crypto_properties(asset),
            "properties": [
                {"name": name, "value": value} for name, value in sorted(properties.items())
            ],
        }
        if asset.vendor:
            component["manufacturer"] = {"name": asset.vendor}
        components.append(component)

    return {
        "$schema": "https://cyclonedx.org/schema/bom-1.7.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "lifecycles": [{"phase": "discovery"}],
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "forge-qbit-qsparx",
                        "version": "0.1.1",
                    }
                ]
            },
            "distributionConstraints": {"tlp": "CLEAR"},
            "properties": [
                {
                    "name": "forge:qsparx:data-classification",
                    "value": "synthetic-unclassified-non-cui",
                },
                {"name": "forge:qsparx:authority", "value": "non-authoritative"},
            ],
        },
        "components": components,
    }
