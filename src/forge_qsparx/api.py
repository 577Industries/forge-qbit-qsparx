"""FastAPI v1 resources for the public QSPARX engine."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import FastAPI, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from forge_qsparx.cyclonedx import import_cbom
from forge_qsparx.services import (
    assessment_result,
    benchmark_result,
    detection_result,
    inventory_result,
    plan_result,
    simulation_result,
    verification_result,
)
from forge_qsparx.synthetic import generate_mission

WORLD_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldRequest(RequestModel):
    seed: int = 577
    world_id: str = Field(default="world-reviewer", pattern=WORLD_PATTERN)


class IngestRequest(RequestModel):
    document: dict[str, Any]
    source_uri: str = "api://v1/ingest"


class BenchmarkRequest(RequestModel):
    seed: int = 577
    repetitions: int = Field(default=3, ge=1, le=1000)
    suite: Literal["smoke", "scale", "interop"] = "smoke"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forge Qbit QSPARX",
        version="0.1.1",
        description="Synthetic, non-authoritative, side-effect-free cryptographic mission twin.",
    )
    deployment_digest = os.getenv("FORGE_QSPARX_CORE_DIGEST")

    @app.middleware("http")
    async def attest_core_digest(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if deployment_digest:
            response.headers["X-Forge-Qsparx-Core-Digest"] = deployment_digest
        return response

    @app.post("/v1/seed")
    def seed_mission(request: WorldRequest) -> dict[str, Any]:
        mission = generate_mission(seed=request.seed)
        return {
            "world_id": request.world_id,
            "seed": request.seed,
            "records": 1
            + len(mission.assets)
            + len(mission.relationships)
            + len(mission.observations),
            "data_label": "synthetic",
            "authority_label": "non_authoritative",
        }

    @app.post("/v1/ingest")
    def ingest_cyclonedx(request: IngestRequest) -> dict[str, Any]:
        assets = import_cbom(
            request.document,
            source_uri=request.source_uri,
            collected_at=datetime(2026, 7, 21, tzinfo=UTC),
        )
        return {
            "count": len(assets),
            "assets": [asset.model_dump(mode="json") for asset in assets],
        }

    @app.get("/v1/inventory")
    def inventory(seed: int = 577) -> dict[str, Any]:
        return inventory_result(seed)

    @app.get("/v1/assessments")
    def assessments(seed: int = 577) -> dict[str, Any]:
        return assessment_result(seed)

    @app.get("/v1/detections")
    def detections(seed: int = 577) -> dict[str, Any]:
        return detection_result(seed)

    @app.post("/v1/migration-plans")
    def migration_plan(request: WorldRequest) -> dict[str, Any]:
        return plan_result(request.seed, request.world_id)

    @app.post("/v1/simulations")
    def simulation(request: WorldRequest) -> dict[str, Any]:
        return simulation_result(request.seed, request.world_id)

    @app.post("/v1/benchmarks")
    def benchmark(request: BenchmarkRequest) -> dict[str, Any]:
        return benchmark_result(request.seed, request.repetitions, request.suite)

    @app.get("/v1/verification")
    def verification(seed: int = 577, runs: int = Query(default=3, ge=2, le=100)) -> dict[str, Any]:
        return verification_result(seed, runs)

    return app


app = create_app()
