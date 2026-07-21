from pathlib import Path

import pytest

from forge_qsparx.repository import MissionRepository
from forge_qsparx.synthetic import generate_mission


def test_repository_keeps_synthetic_worlds_isolated(tmp_path: Path) -> None:
    repository = MissionRepository(tmp_path / "qsparx.sqlite3")
    first = generate_mission(seed=577)
    second = generate_mission(seed=578)

    first_count = repository.save_mission("world-alpha", first)
    second_count = repository.save_mission("world-bravo", second)

    assert first_count == second_count
    assert first_count == 1 + len(first.assets) + len(first.relationships) + len(first.observations)
    assert repository.list_worlds() == ["world-alpha", "world-bravo"]
    assert (
        repository.load_assets("world-alpha")[0].artifact_digest
        != repository.load_assets("world-bravo")[0].artifact_digest
    )
    assert {item.record_id for item in repository.load_assets("world-alpha")} == {
        item.record_id for item in first.assets
    }


@pytest.mark.parametrize("world_id", ["", "../escape", "with space", "a" * 65])
def test_repository_rejects_unsafe_world_identifiers(tmp_path: Path, world_id: str) -> None:
    repository = MissionRepository(tmp_path / "qsparx.sqlite3")

    with pytest.raises(ValueError, match="world_id"):
        repository.save_mission(world_id, generate_mission(seed=577))
