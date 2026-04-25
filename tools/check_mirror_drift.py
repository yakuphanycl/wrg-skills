"""Detect upstream drift on mirrored skills in this repo.

Reads `skills.json`, finds every skill with a `mirror` block, fetches the
upstream raw URL, computes its sha256, and compares to the recorded
`upstream_content_sha256` in the mirror metadata. Reports drift, no drift,
or first-run-baseline-missing.

Usage:
    python tools/check_mirror_drift.py             # check mode (CI-friendly)
    python tools/check_mirror_drift.py --update    # write current upstream hashes to skills.json

Exit codes:
    0 — no drift (or --update succeeded)
    1 — drift detected
    2 — usage error or unreachable upstream
    3 — baseline missing on a mirror (first run; rerun with --update)

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_JSON = REPO_ROOT / "skills.json"


def _github_blob_to_raw(blob_url: str) -> str:
    """Convert a github.com/<o>/<r>/blob/<branch>/<path> URL to raw.githubusercontent.com."""
    if "raw.githubusercontent.com" in blob_url:
        return blob_url
    if "github.com" not in blob_url or "/blob/" not in blob_url:
        raise ValueError(f"Unrecognized URL shape (need github.com .../blob/...): {blob_url}")
    return blob_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")


def _fetch_sha256(raw_url: str) -> tuple[str, bytes]:
    """Fetch the URL and return (sha256_hex, raw_bytes)."""
    req = urllib.request.Request(
        raw_url,
        headers={"User-Agent": "wrg-skills-mirror-drift-checker/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Fetch failed for {raw_url}: {exc}") from exc
    return hashlib.sha256(body).hexdigest(), body


def _check_one(skill: dict[str, Any]) -> tuple[str, str | None]:
    """Check one mirrored skill. Returns (status, recorded_or_actual_hash).

    Status values: "ok" | "drift" | "baseline_missing" | "fetch_error"
    """
    mirror = skill.get("mirror") or {}
    source = mirror.get("source")
    if not source:
        return ("fetch_error", None)
    try:
        raw_url = _github_blob_to_raw(source)
        actual_sha, _ = _fetch_sha256(raw_url)
    except (ValueError, RuntimeError) as exc:
        print(f"  fetch error: {exc}", file=sys.stderr)
        return ("fetch_error", None)
    recorded = mirror.get("upstream_content_sha256")
    if not recorded:
        print(
            f"  baseline missing — actual upstream sha256: {actual_sha}",
            file=sys.stderr,
        )
        return ("baseline_missing", actual_sha)
    if recorded == actual_sha:
        return ("ok", recorded)
    print(
        f"  DRIFT — recorded: {recorded[:12]}...  actual: {actual_sha[:12]}...",
        file=sys.stderr,
    )
    return ("drift", actual_sha)


def _load_skills_json() -> dict[str, Any]:
    if not SKILLS_JSON.exists():
        raise SystemExit(f"skills.json not found at {SKILLS_JSON}")
    with SKILLS_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_skills_json(data: dict[str, Any]) -> None:
    with SKILLS_JSON.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cmd_check() -> int:
    data = _load_skills_json()
    mirrors = [s for s in data.get("skills", []) if s.get("mirror")]
    if not mirrors:
        print("no mirrored skills found in skills.json — nothing to check.")
        return 0
    print(f"checking {len(mirrors)} mirrored skill(s)...")
    drift = 0
    missing = 0
    errors = 0
    for skill in mirrors:
        name = skill.get("name", "<unknown>")
        print(f"  - {name}: ", end="")
        status, _ = _check_one(skill)
        print(status)
        if status == "drift":
            drift += 1
        elif status == "baseline_missing":
            missing += 1
        elif status == "fetch_error":
            errors += 1
    print()
    if errors:
        print(f"FAIL: {errors} mirror(s) had upstream fetch errors.", file=sys.stderr)
        return 2
    if missing:
        print(
            f"FAIL: {missing} mirror(s) missing baseline hash. Rerun with --update to record.",
            file=sys.stderr,
        )
        return 3
    if drift:
        print(
            f"FAIL: {drift} mirror(s) drifted from upstream. Re-sync content + bump last_sync + rerun --update.",
            file=sys.stderr,
        )
        return 1
    print("OK: all mirrors in sync with upstream.")
    return 0


def cmd_update() -> int:
    data = _load_skills_json()
    mirrors = [s for s in data.get("skills", []) if s.get("mirror")]
    if not mirrors:
        print("no mirrored skills to update.")
        return 0
    print(f"updating baseline hashes for {len(mirrors)} mirror(s)...")
    errors = 0
    for skill in mirrors:
        name = skill.get("name", "<unknown>")
        print(f"  - {name}: ", end="")
        try:
            raw_url = _github_blob_to_raw(skill["mirror"]["source"])
            actual_sha, _ = _fetch_sha256(raw_url)
        except (ValueError, RuntimeError) as exc:
            print(f"fetch error: {exc}")
            errors += 1
            continue
        skill["mirror"]["upstream_content_sha256"] = actual_sha
        print(f"{actual_sha[:12]}...")
    if errors:
        print(f"FAIL: {errors} mirror(s) failed to fetch.", file=sys.stderr)
        return 2
    _save_skills_json(data)
    print("OK: skills.json updated with current upstream hashes.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch current upstream hashes and write them to skills.json (baseline mode).",
    )
    args = parser.parse_args(argv)
    if args.update:
        return cmd_update()
    return cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
