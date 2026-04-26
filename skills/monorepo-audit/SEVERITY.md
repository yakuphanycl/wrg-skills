# SEVERITY.md — default severity weights for `monorepo-audit` findings

Reference table mapping every finding type the [`monorepo-audit` skill](SKILL.md)
can produce to its **default severity bucket**. Mirrors the structure of
[`skills/mcp-audit/SEVERITY.md`](../mcp-audit/SEVERITY.md) for cross-skill
consistency — the bucket names and override conventions are intentionally
shared.

When the audit produces a case-study under `docs/case-studies/`, every
finding row carries one `finding_id` from the table below. Auditors **may
deviate** from the default if context warrants — but deviations must be
called out in the case-study finding's "Why this bucket" line, not
silently applied.

---

## How to use this table

1. Audit produces a finding (e.g., "module `wrg_devguard/plugin.py` has zero importers").
2. Match the finding to the closest row by `category` + `description`.
3. Assign that row's `finding_id` and `default_severity` to the finding.
4. If you need to deviate (rare), record the override and the reason in
   the case-study finding block.

The 12 rows below cover the categories the audit's three checks
(`schema_drift`, `coverage_floor`, `orphan_modules`) naturally produce,
plus a small set of cross-cutting hygiene findings that surface during
audit synthesis.

Severity bucket definitions are shared with mcp-audit's
[`docs/disclosure-sop.md` §1](../../docs/disclosure-sop.md#1-severity-rubric).
For internal-monorepo audits (the default use of this skill), the
disclosure SOP does not apply — all findings route to a public PR or
internal fix-wave per the maintainer's normal flow. The severity bucket
governs **prioritisation** (Critical = drop everything; Info = batch
into routine cleanup), not **disclosure routing**.

---

## Matrix

| # | finding_id | category | description | default_severity | rationale | concrete example |
|---|---|---|---|---|---|---|
| 1 | `SCHEMA-001` | Schema drift | Table declared in source CREATE TABLE statements is missing from the live SQLite DB | Medium | Code expects the table; runtime error on first query. Migration gap, recoverable but not silent | `wrg_memory` source defines `entries` table; live DB has no such table |
| 2 | `SCHEMA-002` | Schema drift | Table column declared in source is missing from the live DB | Medium | Same blast radius as SCHEMA-001 at the column level; runtime `OperationalError` on first SELECT/INSERT touching the column | `research_motor.runs` table has new `score` column in source, DB is one migration behind |
| 3 | `SCHEMA-003` | Schema drift | Table column exists in DB but not in source CREATE TABLE | Low | Code-truth-vs-DB-truth question; legacy column or external migration. Not actively harmful unless code starts asserting "no extra columns" | DB has a `legacy_id` column that source's CREATE TABLE no longer mentions |
| 4 | `SCHEMA-004` | Schema drift | Live DB read failed (corrupt file, locked, permissions) | High | Audit cannot complete; possible data loss / corruption signal that warrants immediate investigation | `sqlite3.DatabaseError: file is not a database` |
| 5 | `COVER-001` | Coverage floor | Recorded coverage < `pyproject.toml` `fail_under` for an app | High | The maintainer declared a contract (`fail_under=N`); the contract is silently violated | `wrg_devguard` declares `fail_under=60`, recorded coverage shows 47 |
| 6 | `COVER-002` | Coverage floor | Coverage record missing for an app with `fail_under` declared | Info | Cannot verify the contract; tests may not have been run, or the health-dir convention isn't followed by this app | App has `fail_under=60` in pyproject but no `artifacts/health/release_check_<app>.json` |
| 7 | `ORPHAN-001` | Orphan modules | Module has zero importers across the package + zero exemption matches (CLI script target, ASGI app, plugin.py marker, test consumer, dynamic-dispatch dir) | Low | Likely dead code; needs human verification (a single false positive would generate a destructive PR if auto-applied) | `apps/foo/src/foo/legacy_export_v1.py` last touched 14 months ago, no consumers, no tests |
| 8 | `ORPHAN-002` | Orphan modules | Module is exempt under §6.2 test-only-consumer rule but no production consumer | Info | Tests assert a contract no production code consumes; both module and tests may be candidates for removal in a future strict-mode audit | `apps/research_motor/src/research_motor/adapters/_records.py` only consumed by `tests/test_records_contract.py` |
| 9 | `ORPHAN-003` | Orphan modules | Module flagged as orphan but auditor verified it is dynamically loaded by an indirect dispatcher (e.g., entry-point group, host-app discovery) outside the directory's own siblings | Info | False-positive class beyond §6.1's same-directory dispatch detection; flag for skill enhancement candidate (e.g., entry-point-group exemption) | App registers itself via `entry_points = {"wrg.plugins": [...]}` in `setup.cfg`, loaded by host app outside this app tree |
| 10 | `LAYOUT-001` | Layout / convention | App has neither `src/<pkg>/` nor flat-layout package detectable by skill heuristics | Low | Audit skips the app silently; surfaces a layout convention drift worth standardising | App has only `scripts/` directory, no Python package — likely a misclassified ops folder under `apps/` |
| 11 | `LAYOUT-002` | Layout / convention | App has `pyproject.toml` but `[project.scripts]` references a module path that doesn't exist | Medium | Install would create a broken CLI entry; surfaces during smoke-install or first run | `[project.scripts] foo = "foo.cli:main"` but `src/foo/cli.py` doesn't exist |
| 12 | `META-001` | Meta / cross-app | Same finding type appears in ≥50% of audited apps | Info | Suggests a monorepo-level convention is misapplied or a tooling gap; raise as a single cross-cutting follow-up rather than per-app PRs | All 18 apps lack coverage records (COVER-002) — likely the health-dir convention changed |

---

## Override conventions

If you assign a non-default severity to a finding, prefix the
case-study's "Why this bucket" line with `OVERRIDE:` and one of:

- `OVERRIDE: escalated` — finding hits a higher bucket than default.
  Example: `ORPHAN-001` (Low) escalated to Medium because the orphan
  module is `auth_handler.py` and missing audit logs would mask
  unauthorised access attempts.
- `OVERRIDE: de-escalated` — finding hits a lower bucket than default.
  Example: `SCHEMA-002` (Medium) de-escalated to Low because the new
  column is nullable and existing code doesn't reference it yet.

`COVER-001` and `SCHEMA-004` are floor-severities — do not de-escalate.
`SCHEMA-004` is a corruption signal that warrants stopping and
investigating; `COVER-001` is a declared-contract violation and the
contract is the maintainer's word.

---

## Adding a new row

When an audit surfaces a finding type that does not match any existing
row, propose a new row in the case-study's §6 ("Reusable patterns") and
open a follow-up PR against this file. Keep `finding_id` zero-padded and
contiguous within its category prefix.

The 12-row count is not sacred — the table is expected to grow as more
case-studies land. The constraint is that every finding in every
case-study cites a row by `finding_id`, so coverage must precede usage.

## Cross-skill consistency notes

- Bucket names (Critical / High / Medium / Low / Info) are shared with
  mcp-audit per [`docs/disclosure-sop.md` §1](../../docs/disclosure-sop.md#1-severity-rubric).
  Auditors who have run mcp-audit before should find the rubric here
  immediately legible.
- Override convention syntax (`OVERRIDE: escalated` / `de-escalated`)
  is identical across skills, so case-studies can be cross-read.
- Floor-severity restriction (do not de-escalate certain rows) is the
  same shape as mcp-audit's `SEC-001`/`SEC-002`/`SEC-003` floor.
- For external-target audits (this skill applied against someone else's
  monorepo), `docs/disclosure-sop.md` routing applies. For internal
  monorepo audits (the default), the SOP does not apply — all findings
  go via the maintainer's normal PR / fix-wave flow.
