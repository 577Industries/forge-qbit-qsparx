from datetime import UTC, datetime

import pytest

from forge_qsparx.canonical import canonical_json
from forge_qsparx.cyclonedx import export_cbom, import_cbom
from forge_qsparx.synthetic import generate_mission


def cbom_fixture(version: str) -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": version,
        "version": 1,
        "components": [
            {
                "type": "cryptographic-asset",
                "bom-ref": "crypto:rsa-2048",
                "name": "RSA-2048",
                "cryptoProperties": {
                    "assetType": "algorithm",
                    "algorithmProperties": {
                        "primitive": "signature",
                        "parameterSetIdentifier": "2048",
                    },
                },
                "properties": [
                    {"name": "forge:qsparx:mission-service", "value": "svc-messaging"},
                    {"name": "forge:qsparx:platform", "value": "Windows Server 2022"},
                ],
            }
        ],
    }


@pytest.mark.parametrize("version", ["1.6", "1.7"])
def test_imports_supported_cyclonedx_cbom_versions(version: str) -> None:
    assets = import_cbom(
        cbom_fixture(version),
        source_uri=f"file://fixture-{version}.cbom.json",
        collected_at=datetime(2026, 7, 21, tzinfo=UTC),
    )

    assert len(assets) == 1
    assert assets[0].algorithm == "RSA-2048"
    assert assets[0].mission_service_id == "svc-messaging"
    assert assets[0].discovery_modality == "sbom_cbom"
    assert assets[0].data_label == "synthetic"


def test_rejects_unknown_or_non_cyclonedx_documents() -> None:
    with pytest.raises(ValueError, match="CycloneDX"):
        import_cbom({"bomFormat": "SPDX", "specVersion": "1.7"})
    with pytest.raises(ValueError, match="1.6 and 1.7"):
        import_cbom({"bomFormat": "CycloneDX", "specVersion": "1.5"})


def test_exports_canonical_cyclonedx_17_cbom() -> None:
    mission = generate_mission(seed=577)
    exported = export_cbom(mission.assets, generated_at=datetime(2026, 7, 21, tzinfo=UTC))

    assert exported["bomFormat"] == "CycloneDX"
    assert exported["specVersion"] == "1.7"
    assert exported["metadata"]["lifecycles"] == [{"phase": "discovery"}]
    assert exported["metadata"]["distributionConstraints"] == {"tlp": "CLEAR"}
    assert all(component["type"] == "cryptographic-asset" for component in exported["components"])
    assert all("cryptoProperties" in component for component in exported["components"])
    assert canonical_json(exported) == canonical_json(
        export_cbom(mission.assets, generated_at=datetime(2026, 7, 21, tzinfo=UTC))
    )
