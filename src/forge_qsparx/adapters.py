"""Passive, file-only cryptographic discovery adapters."""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from pathlib import Path
from typing import Any

from forge_qsparx.cyclonedx import import_cbom


class PassiveAdapter(str, Enum):
    auto = "auto"
    source = "source"
    dependency = "dependency"
    binary = "binary"
    container = "container"
    tls = "tls"
    ssh = "ssh"
    pki = "pki"
    keystore = "keystore"
    aws_kms = "aws-kms"
    azure_pki = "azure-pki"
    cyclonedx = "cyclonedx"


ALGORITHM = re.compile(
    rb"\b(?:AES(?:-\d{3})?|ECDSA(?:-P\d+)?|ECDHE(?:-P\d+)?|ML-DSA-\d+|ML-KEM-\d+|"
    rb"RSA(?:-\d+)?|SHA-?(?:1|2|256|384|512)|SLH-DSA(?:-[A-Za-z0-9-]+)?|TLS|SSH)\b",
    re.IGNORECASE,
)


def _select_adapter(requested: PassiveAdapter, document: Any, source: Path) -> PassiveAdapter:
    if requested is not PassiveAdapter.auto:
        return requested
    if isinstance(document, dict) and document.get("bomFormat") == "CycloneDX":
        return PassiveAdapter.cyclonedx
    name = source.name.casefold()
    if "aws" in name and "kms" in name:
        return PassiveAdapter.aws_kms
    if "azure" in name and ("pki" in name or "key" in name):
        return PassiveAdapter.azure_pki
    if source.suffix.casefold() in {".py", ".ts", ".js", ".java", ".cs", ".go", ".rs"}:
        return PassiveAdapter.source
    return PassiveAdapter.binary


def _discovery_records(
    content: bytes, selected: PassiveAdapter, source_digest: str
) -> list[dict[str, Any]]:
    algorithms = sorted(
        {
            match.group(0).decode("ascii", errors="replace").upper()
            for match in ALGORITHM.finditer(content)
        }
    )
    if not algorithms:
        algorithms = ["UNKNOWN"]
    return [
        {
            "record_id": f"passive:{selected.value}:{source_digest[7:19]}:{index}",
            "adapter": selected.value,
            "algorithm": algorithm,
            "source_digest": source_digest,
            "data_label": "synthetic_or_caller_supplied",
            "authority_label": "non_authoritative",
        }
        for index, algorithm in enumerate(algorithms, start=1)
    ]


def passive_import(source: Path, requested: PassiveAdapter) -> dict[str, Any]:
    """Read one local file and normalize observations without network or effects."""

    content = source.read_bytes()
    source_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
    try:
        document: Any = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        document = None
    selected = _select_adapter(requested, document, source)
    if selected is PassiveAdapter.cyclonedx:
        if not isinstance(document, dict):
            raise ValueError("CycloneDX adapter requires a JSON object")
        assets = import_cbom(document, source_uri=source.resolve().as_uri())
        records = [asset.model_dump(mode="json") for asset in assets]
    else:
        records = _discovery_records(content, selected, source_digest)
    return {
        "requested_adapter": requested.value,
        "selected_adapter": selected.value,
        "source": str(source),
        "source_digest": source_digest,
        "passive": True,
        "real_connector_calls": 0,
        "effects_applied": False,
        "count": len(records),
        "records": records,
        "assets": records if selected is PassiveAdapter.cyclonedx else [],
    }
