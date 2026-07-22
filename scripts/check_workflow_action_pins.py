#!/usr/bin/env python3
"""Verify that workflow action pins are commits in their declared repositories."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")


class Response(Protocol):
    def __enter__(self) -> Response: ...

    def __exit__(self, *args: object) -> None: ...

    def read(self) -> bytes: ...


CommitLookup = Callable[[str, str], str]


class OpenUrl(Protocol):
    def __call__(self, request: Request, *, timeout: int) -> Response: ...


@dataclass(frozen=True, order=True)
class ActionPin:
    action: str
    repository: str
    sha: str


def _parse_external_action(reference: str, location: str) -> ActionPin | None:
    if reference.startswith("./"):
        return None
    if reference.startswith("docker://"):
        raise ValueError(f"{location}: docker action references are outside this commit-pin policy")

    action, separator, sha = reference.rpartition("@")
    if not separator or not FULL_SHA.fullmatch(sha):
        raise ValueError(
            f"{location}: external action {reference!r} must use a 40-character commit SHA"
        )

    action_parts = action.split("/")
    if len(action_parts) < 2 or not all(action_parts[:2]):
        raise ValueError(f"{location}: malformed external action reference {reference!r}")
    repository = "/".join(action_parts[:2])
    return ActionPin(action=action, repository=repository, sha=sha)


def collect_action_pins(workflows: Path = Path(".github/workflows")) -> list[ActionPin]:
    pins: list[ActionPin] = []
    paths = sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml")))
    if not paths:
        raise ValueError(f"no GitHub Actions workflows found under {workflows}")

    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = USES.match(line)
            if match is None:
                continue
            pin = _parse_external_action(match.group(1), f"{path}:{line_number}")
            if pin is not None:
                pins.append(pin)

    if not pins:
        raise ValueError(f"no external GitHub Actions found under {workflows}")
    return pins


def github_commit_lookup(
    repository: str,
    sha: str,
    *,
    token: str,
    opener: OpenUrl = urlopen,
) -> str:
    request = Request(
        f"https://api.github.com/repos/{repository}/git/commits/{sha}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "forge-qbit-qsparx-action-pin-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with opener(request, timeout=20) as response:
        payload: Any = json.loads(response.read())
    resolved = payload.get("sha") if isinstance(payload, dict) else None
    if not isinstance(resolved, str):
        raise ValueError(f"GitHub returned no commit SHA for {repository}@{sha}")
    return resolved


def verify_action_pins(pins: Iterable[ActionPin], lookup: CommitLookup) -> None:
    for repository, sha in sorted({(pin.repository, pin.sha) for pin in pins}):
        resolved = lookup(repository, sha)
        if resolved != sha:
            raise ValueError(
                f"{repository}@{sha} resolved to unexpected Git commit {resolved!r}"
            )


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for the action-pin provenance audit")

    try:
        pins = collect_action_pins()
        verify_action_pins(
            pins,
            lambda repository, sha: github_commit_lookup(
                repository, sha, token=token
            ),
        )
    except (HTTPError, URLError, ValueError) as error:
        raise SystemExit(f"action-pin provenance audit failed: {error}") from error

    unique_commits = {(pin.repository, pin.sha) for pin in pins}
    print(
        f"Verified {len(pins)} external action references across "
        f"{len(unique_commits)} declared repository commits."
    )


if __name__ == "__main__":
    main()
