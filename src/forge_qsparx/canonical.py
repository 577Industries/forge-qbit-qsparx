"""Canonical serialization and content-addressed artifact storage."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=False)
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Path):
        return str(value)
    return value


def canonical_json(value: Any) -> bytes:
    """Serialize JSON with stable ordering and no insignificant whitespace."""

    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value)).hexdigest()}"


@dataclass(frozen=True)
class ArtifactReference:
    digest: str
    path: Path
    size_bytes: int
    media_type: str


class ContentAddressedStore:
    """Local immutable artifact store keyed by canonical SHA-256 digest."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)

    def put_json(self, value: Any, media_type: str = "application/json") -> ArtifactReference:
        payload = canonical_json(value)
        return self.put_bytes(payload, media_type=media_type)

    def put_bytes(
        self, payload: bytes, media_type: str = "application/octet-stream"
    ) -> ArtifactReference:
        hex_digest = hashlib.sha256(payload).hexdigest()
        path = self.root / "sha256" / hex_digest[:2] / hex_digest[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise RuntimeError("content-address collision")
        else:
            temporary = path.with_suffix(f".tmp-{os.getpid()}")
            temporary.write_bytes(payload)
            temporary.replace(path)
        return ArtifactReference(
            digest=f"sha256:{hex_digest}",
            path=path,
            size_bytes=len(payload),
            media_type=media_type,
        )

    def verify(self, reference: ArtifactReference) -> bool:
        if not reference.path.is_file():
            return False
        observed = hashlib.sha256(reference.path.read_bytes()).hexdigest()
        return reference.digest == f"sha256:{observed}"
