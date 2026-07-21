"""Shared orchestration used by both CLI and REST adapters."""

from __future__ import annotations

import platform
from statistics import fmean
from time import perf_counter
from typing import Any, Literal

from forge_qsparx.canonical import canonical_digest
from forge_qsparx.engine import QsparxEngine
from forge_qsparx.evaluation import evaluate_detectors
from forge_qsparx.synthetic import generate_mission


def model_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list | tuple):
        return [model_json(item) for item in value]
    return value


def inventory_result(seed: int) -> dict[str, Any]:
    assets = QsparxEngine(generate_mission(seed=seed)).inventory()
    return {"seed": seed, "count": len(assets), "assets": model_json(assets)}


def assessment_result(seed: int) -> dict[str, Any]:
    assessments = QsparxEngine(generate_mission(seed=seed)).assess()
    return {"seed": seed, "count": len(assessments), "assessments": model_json(assessments)}


def detection_result(seed: int) -> dict[str, Any]:
    detections = QsparxEngine(generate_mission(seed=seed)).detect()
    return {"seed": seed, "count": len(detections), "detections": model_json(detections)}


def plan_result(seed: int, world_id: str) -> dict[str, Any]:
    plan = QsparxEngine(generate_mission(seed=seed)).plan(world_id=world_id)
    return plan.model_dump(mode="json")


def simulation_result(seed: int, world_id: str) -> dict[str, Any]:
    engine = QsparxEngine(generate_mission(seed=seed))
    return engine.simulate(engine.plan(world_id=world_id)).model_dump(mode="json")


def benchmark_result(
    seed: int, repetitions: int, suite: Literal["smoke", "scale", "interop"] = "smoke"
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    if suite != "smoke":
        return {
            "benchmark_id": f"synthetic-{suite}-suite-1.0.0",
            "suite": suite,
            "execution_state": "not_run",
            "claim_state": "planned_phase_i",
            "acceptance_gate": False,
            "seed": seed,
            "repetitions": repetitions,
            "metrics": {},
            "limitation": (
                f"The {suite} suite interface is frozen, but no result is emitted until its "
                "preregistered corpus or interoperability matrix is executed."
            ),
        }
    durations_ms: list[float] = []
    result_digest = ""
    for _ in range(repetitions):
        started = perf_counter()
        engine = QsparxEngine(generate_mission(seed=seed))
        payload = {
            "inventory": model_json(engine.inventory()),
            "assessments": model_json(engine.assess()),
            "detections": model_json(engine.detect()),
        }
        durations_ms.append((perf_counter() - started) * 1000)
        result_digest = canonical_digest(payload)
    evaluation = evaluate_detectors(seed=seed, samples=160)
    return {
        "benchmark_id": "synthetic-pipeline-smoke-1.0.0",
        "suite": suite,
        "execution_state": "completed",
        "claim_state": "measured_synthetic",
        "acceptance_gate": False,
        "limitation": (
            "Smoke timing only; not the sealed 30-repetition interoperability or scale benchmark."
        ),
        "seed": seed,
        "repetitions": repetitions,
        "mean_latency_ms": round(fmean(durations_ms), 3),
        "min_latency_ms": round(min(durations_ms), 3),
        "max_latency_ms": round(max(durations_ms), 3),
        "result_digest": result_digest,
        "corpus_state": evaluation["corpus_state"],
        "split": evaluation["split"],
        "models": evaluation["models"],
        "reference_machine": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
    }


def verification_result(seed: int, runs: int) -> dict[str, Any]:
    if runs < 2:
        raise ValueError("runs must be at least 2")
    digests: list[str] = []
    effects_applied = False
    rollback_verified = True
    for _ in range(runs):
        mission = generate_mission(seed=seed)
        digests.append(canonical_digest(mission))
        engine = QsparxEngine(mission)
        simulation = engine.simulate(engine.plan(world_id="world-verification"))
        effects_applied = effects_applied or simulation.effects_applied
        rollback_verified = rollback_verified and simulation.rollback_verified
    return {
        "seed": seed,
        "runs": runs,
        "canonical_digests_match": len(set(digests)) == 1,
        "canonical_digest": digests[0],
        "effects_applied": effects_applied,
        "rollback_verified": rollback_verified,
        "real_connector_calls": 0,
        "data_label": "synthetic",
        "authority_label": "non_authoritative",
    }
