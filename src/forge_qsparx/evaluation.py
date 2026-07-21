"""Preregistered development-corpus detector comparison.

These results are explicitly not acceptance evidence.  The sealed corpus and
independent validation remain future gates.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import shap
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.metrics import average_precision_score, brier_score_loss, recall_score
from sklearn.model_selection import train_test_split

FEATURES = [
    "weak_primitive",
    "quantum_vulnerable",
    "data_lifetime",
    "internet_exposed",
    "graph_outage_impact",
    "graph_centrality",
]


def _metrics(labels: np.ndarray[Any, Any], scores: np.ndarray[Any, Any]) -> dict[str, float]:
    predictions = scores >= 0.5
    negatives = labels == 0
    false_positives = int(np.sum(predictions & negatives))
    negative_count = max(1, int(np.sum(negatives)))
    return {
        "aucpr": round(float(average_precision_score(labels, scores)), 6),
        "brier_score": round(float(brier_score_loss(labels, scores)), 6),
        "critical_recall": round(float(recall_score(labels, predictions, zero_division=0)), 6),
        "false_positive_rate": round(false_positives / negative_count, 6),
    }


def _development_corpus(
    seed: int, samples: int
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    if samples < 80:
        raise ValueError("development evaluation requires at least 80 samples")
    rng = np.random.default_rng(seed)
    weak = rng.binomial(1, 0.16, samples)
    quantum = rng.binomial(1, 0.58, samples)
    lifetime = rng.integers(0, 21, samples) / 20.0
    exposed = rng.binomial(1, 0.28, samples)
    impact = rng.binomial(1, 0.34, samples)
    centrality = rng.beta(2.0, 5.0, samples)
    features = np.column_stack([weak, quantum, lifetime, exposed, impact, centrality])
    labels = (
        ((weak == 1) & ((impact == 1) | (exposed == 1)))
        | ((quantum == 1) & (lifetime >= 0.5) & (exposed == 1))
        | ((quantum == 1) & (lifetime >= 0.75) & (impact == 1))
    ).astype(int)
    return features, labels


def _normalize(values: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    low = float(np.min(values))
    high = float(np.max(values))
    if high == low:
        return np.zeros_like(values, dtype=float)
    return (values - low) / (high - low)


def evaluate_detectors(seed: int = 577, samples: int = 160) -> dict[str, Any]:
    features, labels = _development_corpus(seed, samples)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.25,
        random_state=seed,
        stratify=labels,
    )

    rule_scores = np.clip(
        0.38 * x_test[:, 0]
        + 0.18 * x_test[:, 1]
        + 0.17 * x_test[:, 2]
        + 0.14 * x_test[:, 3]
        + 0.13 * x_test[:, 4],
        0.0,
        1.0,
    )
    graph_scores = np.clip(
        0.28 * x_test[:, 0]
        + 0.18 * x_test[:, 1]
        + 0.12 * x_test[:, 2]
        + 0.12 * x_test[:, 3]
        + 0.22 * x_test[:, 4]
        + 0.08 * x_test[:, 5],
        0.0,
        1.0,
    )

    isolation = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=seed,
    ).fit(x_train)
    isolation_scores = _normalize(-isolation.decision_function(x_test))

    gradient = GradientBoostingClassifier(
        n_estimators=60,
        learning_rate=0.05,
        max_depth=2,
        random_state=seed,
    ).fit(x_train, y_train)
    gradient_scores = gradient.predict_proba(x_test)[:, 1]
    shap_values = np.asarray(shap.TreeExplainer(gradient).shap_values(x_test))
    shap_mean_abs = {
        feature: round(float(value), 6)
        for feature, value in zip(FEATURES, np.mean(np.abs(shap_values), axis=0), strict=True)
    }

    return {
        "evaluation_id": "development-detector-ablation-1.0.0",
        "claim_state": "measured_synthetic",
        "acceptance_gate": False,
        "corpus_state": "development_unsealed",
        "limitation": (
            "Synthetic development corpus only; thresholds may be revised once before sealing. "
            "No operational, government, or independent validation claim."
        ),
        "features": FEATURES,
        "samples": samples,
        "split": {
            "random_seed": seed,
            "held_out_fraction": 0.25,
            "train_samples": int(len(x_train)),
            "held_out_samples": int(len(x_test)),
            "stratified": True,
        },
        "models": {
            "deterministic_rules": {
                "role": "explainable_policy_baseline",
                "metrics": _metrics(y_test, rule_scores),
            },
            "isolation_forest": {
                "role": "advisory_anomaly_ablation",
                "metrics": _metrics(y_test, isolation_scores),
            },
            "gradient_boosted": {
                "role": "advisory_supervised_ablation",
                "metrics": _metrics(y_test, gradient_scores),
                "shap_mean_abs": shap_mean_abs,
            },
            "graph_features": {
                "role": "advisory_graph_ablation",
                "metrics": _metrics(y_test, graph_scores),
            },
        },
    }
