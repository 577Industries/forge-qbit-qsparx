from forge_qsparx.canonical import canonical_digest
from forge_qsparx.evaluation import evaluate_detectors, inventory_metrics, prioritization_metrics


def test_detector_evaluation_is_preregistered_held_out_and_reproducible() -> None:
    first = evaluate_detectors(seed=577, samples=160)
    second = evaluate_detectors(seed=577, samples=160)

    assert canonical_digest(first) == canonical_digest(second)
    assert first["claim_state"] == "measured_synthetic"
    assert first["acceptance_gate"] is False
    assert first["corpus_state"] == "development_unsealed"
    assert first["split"]["random_seed"] == 577
    assert first["split"]["held_out_fraction"] == 0.25
    assert set(first["models"]) == {
        "deterministic_rules",
        "gradient_boosted",
        "graph_features",
        "isolation_forest",
    }
    for result in first["models"].values():
        assert set(result["metrics"]) == {
            "aucpr",
            "brier_score",
            "critical_recall",
            "false_positive_rate",
        }
        assert all(0.0 <= value <= 1.0 for value in result["metrics"].values())
    assert set(first["models"]["gradient_boosted"]["shap_mean_abs"]) == set(first["features"])


def test_inventory_metrics_use_stable_ids_and_report_each_modality() -> None:
    truth = {"asset:a": "source", "asset:b": "source", "asset:c": "binary"}
    detected = {"asset:a": "source", "asset:c": "binary", "asset:x": "container"}

    metrics = inventory_metrics(truth, detected)

    assert metrics["precision"] == 2 / 3
    assert metrics["recall"] == 2 / 3
    assert metrics["per_modality_recall"] == {"binary": 1.0, "source": 0.5}


def test_prioritization_metrics_measure_ndcg_and_critical_top_ten_recall() -> None:
    ranked = ["asset:critical", "asset:medium", "asset:low"]
    relevance = {"asset:critical": 3, "asset:medium": 2, "asset:low": 1}

    metrics = prioritization_metrics(ranked, relevance, critical_ids={"asset:critical"}, k=10)

    assert metrics == {"ndcg_at_10": 1.0, "critical_top_ten_recall": 1.0}
