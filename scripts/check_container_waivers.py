#!/usr/bin/env python3
"""Fail closed when the narrowly scoped container vulnerability waivers drift.

No waiver is in force since 2026-09-01: Wolfi published python-3.12 3.12.14,
which carries the upstream fixes the six earlier waivers covered, and the
Dockerfile pins it. The checker still validates the policy file's shape so a
waiver cannot be reintroduced without the expiry / scope / assessment contract
below.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

EXPECTED_VULNERABILITIES: set[str] = set()
EXPECTED_PACKAGE = {
    "name": "python-3.12",
    "version": "3.12.14-r4",
    "type": "apk",
}
POLICY_KEYS = {"show-suppressed", "ignore"}
RULE_KEYS = {"vulnerability", "package", "reason"}
REASON_PATTERN = re.compile(
    r"^expires=(\d{4}-\d{2}-\d{2}); "
    r"scope=(sha256:[0-9a-f]{64}); "
)


def runtime_scope_digest(root: Path = Path(".")) -> str:
    # Dockerfile + product code only. The dependency manifests (pyproject.toml,
    # uv.lock) left the scope on 2026-09-01: every Dependabot PR since 08-11 had
    # invalidated the waivers — including the pip 26.2 security fix — while the
    # reachability decisions concern stdlib surfaces the product code itself
    # does or does not call. A Dockerfile or source change still forces
    # reassessment.
    paths = [
        root / "Dockerfile",
        *sorted((root / "src" / "forge_qsparx").glob("*.py")),
    ]
    digest = sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_text(encoding="utf-8").encode())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def main() -> None:
    policy_path = Path(".grype.yaml")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if set(policy) != POLICY_KEYS or policy.get("show-suppressed") is not True:
        raise SystemExit(".grype.yaml contains an unreviewed scanner control")
    rules = policy.get("ignore")
    if not isinstance(rules, list):
        raise SystemExit(".grype.yaml must contain an ignore list")

    vulnerabilities = [rule.get("vulnerability") for rule in rules]
    if len(vulnerabilities) != len(set(vulnerabilities)):
        raise SystemExit("container vulnerability waiver IDs must be unique")
    if set(vulnerabilities) != EXPECTED_VULNERABILITIES:
        raise SystemExit("container vulnerability waiver set changed without policy review")

    if not rules:
        print("No container vulnerability waivers in force; the image gate runs unfiltered.")
        return

    expiries = set()
    scopes = set()
    for rule in rules:
        vulnerability = rule["vulnerability"]
        if set(rule) != RULE_KEYS:
            raise SystemExit(f"{vulnerability} contains an unreviewed waiver control")
        if rule.get("package") != EXPECTED_PACKAGE:
            raise SystemExit(f"{vulnerability} is not constrained to the reviewed APK build")
        reason = rule.get("reason", "")
        match = REASON_PATTERN.match(reason)
        if match is None or "vulnerable_code_not_in_execute_path" not in reason:
            raise SystemExit(f"{vulnerability} lacks an expiry, scope, or reachability rationale")
        expiries.add(datetime.strptime(match.group(1), "%Y-%m-%d").date())
        scopes.add(match.group(2))

    if len(expiries) != 1:
        raise SystemExit("all container vulnerability waivers must share one review date")
    expiry = expiries.pop()
    if datetime.now(UTC).date() > expiry:
        raise SystemExit(f"container vulnerability waivers expired on {expiry.isoformat()}")
    expected_scope = runtime_scope_digest()
    if scopes != {expected_scope}:
        raise SystemExit("runtime source or dependency scope changed; reassess every waiver")

    assessment = Path("docs/security/container-vulnerability-waivers.md").read_text(
        encoding="utf-8"
    )
    missing = sorted(
        vulnerability
        for vulnerability in EXPECTED_VULNERABILITIES
        if vulnerability not in assessment
    )
    if missing or expiry.isoformat() not in assessment or expected_scope not in assessment:
        raise SystemExit("container waiver assessment is incomplete or out of sync")

    print(
        f"Validated {len(rules)} exact container vulnerability waivers; "
        f"review required by {expiry.isoformat()}."
    )


if __name__ == "__main__":
    main()
