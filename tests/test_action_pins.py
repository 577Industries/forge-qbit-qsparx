from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
VALID_SHA = "a" * 40


def action_pin_module() -> ModuleType:
    path = ROOT / "scripts" / "check_workflow_action_pins.py"
    spec = importlib.util.spec_from_file_location("check_workflow_action_pins", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_action_pin_auditor_exists() -> None:
    assert (ROOT / "scripts" / "check_workflow_action_pins.py").is_file()


def test_parser_maps_action_subpaths_to_the_owning_repository(tmp_path: Path) -> None:
    audit = action_pin_module()
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "codeql.yml").write_text(
        "steps:\n"
        f"  - uses: github/codeql-action/init@{VALID_SHA} # v4\n"
        f"  - uses: github/codeql-action/analyze@{VALID_SHA} # v4\n"
        "  - uses: ./.github/actions/local\n",
        encoding="utf-8",
    )

    pins = audit.collect_action_pins(workflows)

    assert {pin.repository for pin in pins} == {"github/codeql-action"}
    assert {pin.action for pin in pins} == {
        "github/codeql-action/init",
        "github/codeql-action/analyze",
    }
    assert {pin.sha for pin in pins} == {VALID_SHA}


def test_parser_rejects_external_actions_that_are_not_full_sha_pinned(tmp_path: Path) -> None:
    audit = action_pin_module()
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "unsafe.yml").write_text(
        "steps:\n  - uses: actions/checkout@v6\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="40-character commit SHA"):
        audit.collect_action_pins(workflows)


def test_github_lookup_uses_git_commit_endpoint_and_token() -> None:
    audit = action_pin_module()
    captured: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"sha": VALID_SHA}).encode()

    def opener(request: Any, timeout: int) -> Response:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return Response()

    resolved = audit.github_commit_lookup(
        "github/codeql-action", VALID_SHA, token="test-token", opener=opener
    )

    assert resolved == VALID_SHA
    assert captured["url"].endswith(
        f"/repos/github/codeql-action/git/commits/{VALID_SHA}"
    )
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["timeout"] == 20


def test_verifier_deduplicates_repository_commit_pairs() -> None:
    audit = action_pin_module()
    pins = [
        audit.ActionPin("github/codeql-action/init", "github/codeql-action", VALID_SHA),
        audit.ActionPin("github/codeql-action/analyze", "github/codeql-action", VALID_SHA),
    ]
    calls: list[tuple[str, str]] = []

    def lookup(repository: str, sha: str) -> str:
        calls.append((repository, sha))
        return sha

    audit.verify_action_pins(pins, lookup)

    assert calls == [("github/codeql-action", VALID_SHA)]
