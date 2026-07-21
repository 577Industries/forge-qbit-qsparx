from forge_qsparx.canonical import canonical_digest
from forge_qsparx.evaluation import evaluate_detectors


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
