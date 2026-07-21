"""Typer command-line interface for the public QSPARX pipeline."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer

from forge_qsparx.adapters import PassiveAdapter, passive_import
from forge_qsparx.canonical import canonical_digest, canonical_json
from forge_qsparx.models import EvaluationManifest
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
from forge_qsparx.synthetic import generate_mission, generate_scale_corpus

app = typer.Typer(
    name="forge-qsparx",
    help="Synthetic, evidence-first cryptographic mission twin.",
    no_args_is_help=True,
)


class BenchmarkSuite(str, Enum):
    smoke = "smoke"
    scale = "scale"
    interop = "interop"


class SeedProfile(str, Enum):
    reviewer = "reviewer"
    scale_v1 = "scale-v1"


def _emit(value: Any) -> None:
    typer.echo(canonical_json(value).decode("utf-8"))


@app.command()
def seed(
    profile: Annotated[SeedProfile, typer.Option(help="Synthetic corpus profile.")] = (
        SeedProfile.reviewer
    ),
    world: Annotated[str, typer.Option(help="Synthetic world identifier.")] = "world-reviewer",
    database: Annotated[Path, typer.Option(help="SQLite evidence database.")] = Path(
        ".forge-qsparx/qsparx.sqlite3"
    ),
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
    assets: Annotated[int, typer.Option(min=1, help="Scale-profile asset count.")] = 10_000,
    observations: Annotated[
        int, typer.Option(min=1, help="Scale-profile observation count.")
    ] = 1_000_000,
    output: Annotated[Path, typer.Option(help="Scale-profile output directory.")] = Path(
        ".forge-qsparx/scale-v1"
    ),
) -> None:
    """Seed a deterministic synthetic mission world."""

    if profile is SeedProfile.scale_v1:
        _emit(generate_scale_corpus(output, seed=seed, assets=assets, observations=observations))
        return
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
    source: Annotated[Path, typer.Argument(help="Local passive-import file.")],
    adapter: Annotated[PassiveAdapter, typer.Option(help="Passive adapter type.")] = (
        PassiveAdapter.auto
    ),
) -> None:
    """Passively import local evidence without contacting source systems."""

    _emit(passive_import(source, adapter))


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
    suite: Annotated[BenchmarkSuite, typer.Option(help="Benchmark suite.")] = BenchmarkSuite.smoke,
    repetitions: Annotated[int, typer.Option(min=1, help="Smoke repetitions.")] = 3,
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path.")] = None,
) -> None:
    """Run a named benchmark or return a fail-closed not-run report."""

    report = benchmark_result(seed, repetitions, suite.value)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json(report))
    _emit(report)


@app.command()
def verify(
    manifest: Annotated[Path | None, typer.Option(help="Evaluation manifest JSON.")] = None,
    runs: Annotated[int, typer.Option(min=2, help="Clean deterministic runs.")] = 3,
    seed: Annotated[int, typer.Option(help="Deterministic fixture seed.")] = 577,
) -> None:
    """Verify reproducible digests and the public no-effects invariant."""

    report = verification_result(seed, runs)
    if manifest is not None:
        evaluation_manifest = EvaluationManifest.model_validate_json(manifest.read_text())
        report.update(
            {
                "manifest_valid": True,
                "manifest_release_tag": evaluation_manifest.release_tag,
                "manifest_digest": canonical_digest(evaluation_manifest),
            }
        )
    _emit(report)


if __name__ == "__main__":
    app()
