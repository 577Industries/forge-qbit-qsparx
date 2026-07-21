import gzip

from forge_qsparx.canonical import ContentAddressedStore, canonical_digest, canonical_json
from forge_qsparx.synthetic import generate_mission, generate_scale_corpus


def test_synthetic_mission_is_deterministic_and_defense_balanced() -> None:
    first = generate_mission(seed=577)
    second = generate_mission(seed=577)

    assert canonical_json(first) == canonical_json(second)
    assert canonical_digest(first) == canonical_digest(second)
    assert first.context.data_label == "synthetic"
    assert first.context.authority_label == "non_authoritative"
    assert "fictional" in first.context.description.lower()

    platforms = {asset.platform for asset in first.assets}
    implementations = {asset.implementation for asset in first.assets}
    modalities = {asset.discovery_modality for asset in first.assets}
    asset_types = {asset.asset_type for asset in first.assets}

    assert {"Windows Server 2022", "RHEL 9"} <= platforms
    assert {".NET 8", "Java 21", "Python 3.12", "JavaScript/Node.js 22"} <= implementations
    assert {
        "source",
        "dependency",
        "binary",
        "container",
        "protocol",
        "pki",
        "sbom_cbom",
        "cloud_export",
    } <= modalities
    assert {
        "protocol",
        "certificate",
        "key",
        "keystore",
        "kms_reference",
        "data_store",
    } <= asset_types
    assert {relationship.source_asset_id for relationship in first.relationships} <= {
        asset.record_id for asset in first.assets
    }


def test_content_addressed_store_is_idempotent(tmp_path: object) -> None:
    store = ContentAddressedStore(tmp_path)  # type: ignore[arg-type]
    payload = {"z": 1, "a": ["synthetic", "evidence"]}

    first = store.put_json(payload)
    second = store.put_json({"a": ["synthetic", "evidence"], "z": 1})

    assert first.digest == second.digest
    assert first.path == second.path
    assert first.path.read_bytes() == canonical_json(payload)
    assert store.verify(first)


def test_scale_corpus_streams_exact_deterministic_counts(tmp_path: object) -> None:
    first_dir = tmp_path / "first"  # type: ignore[operator]
    second_dir = tmp_path / "second"  # type: ignore[operator]

    first = generate_scale_corpus(first_dir, seed=577, assets=10, observations=100)
    second = generate_scale_corpus(second_dir, seed=577, assets=10, observations=100)

    assert first["asset_count"] == 10
    assert first["observation_count"] == 100
    assert first["file_digests"] == second["file_digests"]
    with gzip.open(first_dir / "assets.ndjson.gz", "rt", encoding="utf-8") as stream:
        assert sum(1 for _ in stream) == 10
    with gzip.open(first_dir / "observations.ndjson.gz", "rt", encoding="utf-8") as stream:
        assert sum(1 for _ in stream) == 100
