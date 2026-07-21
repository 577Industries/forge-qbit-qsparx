#!/usr/bin/env python3
"""Fail closed when the narrowly scoped container vulnerability waivers drift."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

EXPECTED_VULNERABILITIES = {
    "CVE-2026-7210",
    "CVE-2026-4224",
    "CVE-2026-15308",
    "CVE-2026-9669",
    "CVE-2026-3644",
    "CVE-2026-4786",
}
EXPECTED_PACKAGE = {
    "name": "python-3.12",
    "version": "3.12.13-r10",
    "type": "apk",
}
EXPIRY_PATTERN = re.compile(r"^expires=(\d{4}-\d{2}-\d{2}); ")


def main() -> None:
    policy_path = Path(".grype.yaml")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    rules = policy.get("ignore")
    if not isinstance(rules, list):
        raise SystemExit(".grype.yaml must contain an ignore list")

    vulnerabilities = [rule.get("vulnerability") for rule in rules]
    if len(vulnerabilities) != len(set(vulnerabilities)):
        raise SystemExit("container vulnerability waiver IDs must be unique")
    if set(vulnerabilities) != EXPECTED_VULNERABILITIES:
        raise SystemExit("container vulnerability waiver set changed without policy review")

    expiries = set()
    for rule in rules:
        vulnerability = rule["vulnerability"]
        if rule.get("package") != EXPECTED_PACKAGE:
            raise SystemExit(f"{vulnerability} is not constrained to the reviewed APK build")
        reason = rule.get("reason", "")
        match = EXPIRY_PATTERN.match(reason)
        if match is None or "vulnerable_code_not_in_execute_path" not in reason:
            raise SystemExit(f"{vulnerability} lacks an expiry or reachability rationale")
        expiries.add(datetime.strptime(match.group(1), "%Y-%m-%d").date())

    if len(expiries) != 1:
        raise SystemExit("all container vulnerability waivers must share one review date")
    expiry = expiries.pop()
    if datetime.now(UTC).date() > expiry:
        raise SystemExit(f"container vulnerability waivers expired on {expiry.isoformat()}")

    assessment = Path("docs/security/container-vulnerability-waivers.md").read_text(
        encoding="utf-8"
    )
    missing = sorted(
        vulnerability
        for vulnerability in EXPECTED_VULNERABILITIES
        if vulnerability not in assessment
    )
    if missing or expiry.isoformat() not in assessment:
        raise SystemExit("container waiver assessment is incomplete or out of sync")

    print(
        f"Validated {len(rules)} exact container vulnerability waivers; "
        f"review required by {expiry.isoformat()}."
    )


if __name__ == "__main__":
    main()
