"""Typer command-line interface for the public QSPARX pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from forge_qsparx.canonical import canonical_json
from forge_qsparx.cyclonedx import import_cbom
from forge_qsparx.repository import MissionRepository
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

app = typer.Typer(
    name="forge-qsparx",
    help="Synthetic, evidence-first cryptographic mission twin.",
    no_args_is_help=True,
)


def _emit(value: Any) -> None:
    typer.echo(canonical_json(value).decode("utf-8"))


@app.command()
def seed(
    world: Annotated[str, typer.Option(help="Synthetic world identifier.")] = "world-reviewer",
    database: Annotated[Path, typer.Option(help="SQLite evidence database.")] = Path(
        ".forge-qsparx/qsparx.sqlite3"
    ),
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Seed a deterministic synthetic mission world."""

    mission = generate_mission(seed=seed)
    records = MissionRepository(database).save_mission(world, mission)
    _emit(
        {
            "world_id": world,
            "seed": seed,
            "records": records,
            "data_label": "synthetic",
            "authority_label": "non_authoritative",
        }
    )


@app.command()
def ingest(
    source: Annotated[Path, typer.Argument(help="CycloneDX 1.6/1.7 JSON CBOM.")],
) -> None:
    """Passively import a CycloneDX CBOM without contacting its source systems."""

    document = json.loads(source.read_text(encoding="utf-8"))
    assets = import_cbom(document, source_uri=source.resolve().as_uri())
    _emit({"source": str(source), "count": len(assets), "assets": assets})


@app.command()
def inventory(
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Return the canonical cryptographic inventory."""

    _emit(inventory_result(seed))


@app.command()
def assess(
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Run the decomposable deterministic risk policy."""

    _emit(assessment_result(seed))


@app.command()
def detect(
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Run evidence-grounded deterministic detections."""

    _emit(detection_result(seed))


@app.command()
def plan(
    world: Annotated[str, typer.Option(help="World binding for the migration plan.")],
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Generate reversible migration waves."""

    _emit(plan_result(seed, world))


@app.command()
def simulate(
    world: Annotated[str, typer.Option(help="World binding for the simulation.")],
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Simulate a migration with no real-world effects."""

    _emit(simulation_result(seed, world))


@app.command()
def benchmark(
    repetitions: Annotated[int, typer.Option(min=1, help="Smoke repetitions.")] = 3,
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Run a labeled synthetic smoke benchmark (not an acceptance gate)."""

    _emit(benchmark_result(seed, repetitions))


@app.command()
def verify(
    runs: Annotated[int, typer.Option(min=2, help="Clean deterministic runs.")] = 3,
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Verify reproducible digests and the public no-effects invariant."""

    _emit(verification_result(seed, runs))


if __name__ == "__main__":
    app()
