#!/usr/bin/env python3
"""Quick-check CLI for wrg-devguard policy lint and secret scan.

Reads text from stdin or a file, runs the requested scan, and emits
structured JSON to stdout.

Exit codes:
    0 — passed (no findings)
    1 — findings present
    2 — usage error

Requires: wrg-devguard (pip install wrg-devguard)
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from wrg_devguard.policy import default_policy, lint_policy
from wrg_devguard.secrets import scan_secrets


def _run_scan(text: str, mode: str) -> list[dict]:
    """Write *text* to a tempfile and run the appropriate scan."""
    suffix = ".prompt" if mode == "policy" else ".env"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / f"paste{suffix}"
        target.write_text(text, encoding="utf-8")
        if mode == "policy":
            findings = lint_policy(
                Path(tmp), default_policy(), allowed_files={target.name}
            )
        else:
            findings = scan_secrets(Path(tmp), allowed_files={target.name})
    results = []
    for f in findings:
        entry = f.to_dict()
        # Secret mode: strip snippet to prevent echoing matched bytes.
        # The library already redacts, but belt-and-braces.
        if mode == "secret":
            entry.pop("snippet", None)
        results.append(entry)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run wrg-devguard policy lint or secret scan on text."
    )
    parser.add_argument(
        "--mode",
        choices=("policy", "secret"),
        required=True,
        help="Scan mode: 'policy' for prompt-injection lint, 'secret' for credential scan.",
    )
    parser.add_argument(
        "--input",
        metavar="PATH",
        help="File to scan. Reads from stdin if omitted.",
    )
    args = parser.parse_args(argv)

    if args.input:
        path = Path(args.input)
        if not path.is_file():
            print(f"error: file not found: {args.input}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("error: empty input", file=sys.stderr)
        return 2

    findings = _run_scan(text, args.mode)
    passed = len(findings) == 0

    report = {
        "mode": args.mode,
        "passed": passed,
        "count": len(findings),
        "findings": findings,
        "verdict": "PASS" if passed else "FAIL",
    }
    json.dump(report, sys.stdout, indent=2)
    print()  # trailing newline
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
