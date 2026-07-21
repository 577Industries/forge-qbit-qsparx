"""SQLite persistence with explicit synthetic-world isolation."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from forge_qsparx.canonical import canonical_json
from forge_qsparx.models import CryptoAsset, EvidenceRecord, Observation
from forge_qsparx.synthetic import SyntheticMission

WORLD_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class MissionRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
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
                CREATE TABLE IF NOT EXISTS observations (
                    world_id TEXT NOT NULL REFERENCES worlds(world_id) ON DELETE CASCADE,
                    observation_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    modality TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    artifact_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (world_id, observation_id)
                );
                CREATE INDEX IF NOT EXISTS observations_world
                    ON observations(world_id, observation_id);
                CREATE INDEX IF NOT EXISTS observations_asset
                    ON observations(asset_id, world_id);
                CREATE INDEX IF NOT EXISTS observations_modality
                    ON observations(modality, world_id);
                CREATE INDEX IF NOT EXISTS observations_service
                    ON observations(service_id, world_id);
                CREATE INDEX IF NOT EXISTS observations_severity
                    ON observations(severity, world_id);
                CREATE INDEX IF NOT EXISTS observations_provenance
                    ON observations(provenance, world_id);
                CREATE INDEX IF NOT EXISTS observations_time
                    ON observations(observed_at, world_id);
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
        service_by_asset = {asset.record_id: asset.mission_service_id for asset in mission.assets}
        self.save_observations(world_id, mission.observations, service_by_asset=service_by_asset)
        return count

    def save_observations(
        self,
        world_id: str,
        observations: Iterable[Observation],
        *,
        service_by_asset: dict[str, str],
        transaction_size: int = 10_000,
    ) -> int:
        """Persist normalized observations in bounded bulk transactions."""

        self._validate_world(world_id)
        if transaction_size < 1:
            raise ValueError("transaction_size must be positive")
        saved = 0
        batch: list[tuple[str, ...]] = []
        for observation in observations:
            severity_value = observation.attributes.get("severity", "info")
            severity = str(severity_value)
            batch.append(
                (
                    world_id,
                    observation.record_id,
                    observation.asset_id,
                    observation.modality,
                    service_by_asset.get(observation.asset_id, "unknown"),
                    severity,
                    observation.provenance.source_type,
                    observation.valid_from.isoformat(),
                    observation.artifact_digest,
                    canonical_json(observation).decode("utf-8"),
                )
            )
            if len(batch) == transaction_size:
                self._save_observation_batch(batch)
                saved += len(batch)
                batch = []
        if batch:
            self._save_observation_batch(batch)
            saved += len(batch)
        return saved

    def _save_observation_batch(self, rows: list[tuple[str, ...]]) -> None:
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO observations(
                    world_id, observation_id, asset_id, modality, service_id, severity,
                    provenance, observed_at, artifact_digest, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(world_id, observation_id) DO UPDATE SET
                    asset_id = excluded.asset_id,
                    modality = excluded.modality,
                    service_id = excluded.service_id,
                    severity = excluded.severity,
                    provenance = excluded.provenance,
                    observed_at = excluded.observed_at,
                    artifact_digest = excluded.artifact_digest,
                    payload_json = excluded.payload_json
                """,
                rows,
            )

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
