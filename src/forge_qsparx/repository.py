"""SQLite persistence with explicit synthetic-world isolation."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from forge_qsparx.canonical import canonical_json
from forge_qsparx.models import CryptoAsset, EvidenceRecord
from forge_qsparx.synthetic import SyntheticMission

WORLD_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class MissionRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS worlds (
                    world_id TEXT PRIMARY KEY,
                    data_label TEXT NOT NULL CHECK (data_label = 'synthetic'),
                    authority_label TEXT NOT NULL CHECK (authority_label = 'non_authoritative')
                );
                CREATE TABLE IF NOT EXISTS records (
                    world_id TEXT NOT NULL REFERENCES worlds(world_id) ON DELETE CASCADE,
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    artifact_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (world_id, record_type, record_id)
                );
                CREATE INDEX IF NOT EXISTS records_world_type
                    ON records(world_id, record_type, record_id);
                """
            )

    @staticmethod
    def _validate_world(world_id: str) -> None:
        if WORLD_ID.fullmatch(world_id) is None:
            raise ValueError("world_id must match ^[a-z0-9][a-z0-9-]{0,63}$")

    def _save_records(
        self,
        connection: sqlite3.Connection,
        world_id: str,
        record_type: str,
        records: Iterable[EvidenceRecord],
    ) -> int:
        rows = [
            (
                world_id,
                record_type,
                record.record_id,
                record.artifact_digest,
                canonical_json(record).decode("utf-8"),
            )
            for record in records
        ]
        connection.executemany(
            """
            INSERT INTO records(world_id, record_type, record_id, artifact_digest, payload_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(world_id, record_type, record_id) DO UPDATE SET
                artifact_digest = excluded.artifact_digest,
                payload_json = excluded.payload_json
            """,
            rows,
        )
        return len(rows)

    def save_mission(self, world_id: str, mission: SyntheticMission) -> int:
        self._validate_world(world_id)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO worlds(world_id, data_label, authority_label)
                VALUES (?, 'synthetic', 'non_authoritative')
                ON CONFLICT(world_id) DO NOTHING
                """,
                (world_id,),
            )
            count = self._save_records(connection, world_id, "mission_context", [mission.context])
            count += self._save_records(connection, world_id, "crypto_asset", mission.assets)
            count += self._save_records(
                connection, world_id, "crypto_relationship", mission.relationships
            )
            count += self._save_records(connection, world_id, "observation", mission.observations)
            return count

    def list_worlds(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT world_id FROM worlds ORDER BY world_id").fetchall()
        return [str(row[0]) for row in rows]

    def load_assets(self, world_id: str) -> list[CryptoAsset]:
        self._validate_world(world_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM records
                WHERE world_id = ? AND record_type = 'crypto_asset'
                ORDER BY record_id
                """,
                (world_id,),
            ).fetchall()
        return [CryptoAsset.model_validate(json.loads(str(row[0]))) for row in rows]
