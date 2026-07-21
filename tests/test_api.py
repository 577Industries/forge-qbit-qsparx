from fastapi.testclient import TestClient

from forge_qsparx.api import create_app


def test_versioned_api_exposes_the_complete_side_effect_free_pipeline() -> None:
    client = TestClient(create_app())

    calls = [
        ("post", "/v1/seed", {"seed": 577, "world_id": "world-reviewer"}),
        (
            "post",
            "/v1/ingest",
            {
                "document": {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.7",
                    "components": [
                        {
                            "type": "cryptographic-asset",
                            "bom-ref": "crypto:rsa",
                            "name": "RSA-2048",
                            "cryptoProperties": {"assetType": "algorithm"},
                        }
                    ],
                }
            },
        ),
        ("get", "/v1/inventory?seed=577", None),
        ("get", "/v1/assessments?seed=577", None),
        ("get", "/v1/detections?seed=577", None),
        ("post", "/v1/migration-plans", {"seed": 577, "world_id": "world-reviewer"}),
        ("post", "/v1/simulations", {"seed": 577, "world_id": "world-reviewer"}),
        ("post", "/v1/benchmarks", {"seed": 577, "repetitions": 2}),
        ("get", "/v1/verification?seed=577&runs=3", None),
    ]

    responses = []
    for method, path, body in calls:
        response = client.request(method, path, json=body)
        assert response.status_code == 200, f"{method} {path}: {response.text}"
        responses.append(response.json())

    (
        seed_result,
        ingest_result,
        inventory,
        assessments,
        detections,
        plan,
        simulation,
        benchmark,
        verification,
    ) = responses
    assert seed_result["data_label"] == "synthetic"
    assert ingest_result["assets"][0]["authority_label"] == "non_authoritative"
    assert inventory["assets"]
    assert assessments["assessments"][0]["factors"]
    assert detections["detections"]
    assert plan["approval_required"] is True
    assert simulation["effects_applied"] is False
    assert benchmark["claim_state"] == "measured_synthetic"
    assert set(benchmark["models"]) == {
        "deterministic_rules",
        "gradient_boosted",
        "graph_features",
        "isolation_forest",
    }
    assert verification["canonical_digests_match"] is True


def test_api_rejects_unsafe_world_identifiers() -> None:
    client = TestClient(create_app())

    response = client.post("/v1/simulations", json={"seed": 577, "world_id": "../escape"})

    assert response.status_code == 422


def test_api_attests_the_deployment_digest_when_configured(monkeypatch: object) -> None:
    digest = "sha256:" + "b" * 64
    monkeypatch.setenv("FORGE_QSPARX_CORE_DIGEST", digest)  # type: ignore[attr-defined]
    client = TestClient(create_app())

    response = client.get("/v1/inventory?seed=577")

    assert response.headers["x-forge-qsparx-core-digest"] == digest


def test_api_accepts_all_named_benchmark_suites() -> None:
    client = TestClient(create_app())

    reports = [
        client.post("/v1/benchmarks", json={"seed": 577, "repetitions": 1, "suite": suite})
        for suite in ["smoke", "scale", "interop"]
    ]

    assert all(response.status_code == 200 for response in reports)
    assert [response.json()["suite"] for response in reports] == ["smoke", "scale", "interop"]
    assert reports[1].json()["execution_state"] == "not_run"
    assert reports[2].json()["execution_state"] == "not_run"
