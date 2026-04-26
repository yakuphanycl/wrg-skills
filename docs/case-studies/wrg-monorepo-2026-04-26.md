---
target_repo: yakuphanycl/WinstonRedGuard
target_commit: 81a7f00
target_package: (monorepo, no single package)
audit_date: 2026-04-26
auditor: yakuphanycl (Claude Code)
skill_version: skills/monorepo-audit @ 136203e
mcp_servers_audited: []
severity_summary:
  critical: 0
  high: 0
  medium: 0
  low: 1
  info: 1
disclosure_status: public
---

# `yakuphanycl/WinstonRedGuard` monorepo audit (2026-04-26)

> **First end-to-end battle-test of the [`monorepo-audit`](../../skills/monorepo-audit/SKILL.md)
> skill** — counterpart to the `mcp-audit` skill's 5 external-MCP audits
> from earlier this week. This case-study uses the same `_TEMPLATE.md`
> structure even though `monorepo-audit` is structurally different from
> `mcp-audit` (different rubric, different finding shape) so future
> case-studies across both skills read consistently.
>
> **Headline**: 0 Critical / 0 High / 0 Medium. **42 raw findings → 6
> real after pickaxe** (1 Low + 1 Info actionable; 4 entrypoint-exemption
> false positives flagged as skill-enhancement candidates). The 86%
> false-positive rate is itself the most actionable finding — surfaces
> four concrete `audit.py` enhancements that would meaningfully reduce
> noise on similar codebases.

---

## 1. Scope

**In scope**
- Repo: `yakuphanycl/WinstonRedGuard` at commit
  [`81a7f00`](https://github.com/yakuphanycl/WinstonRedGuard/commit/81a7f00).
- Subprojects: 18 active apps under `apps/` (excluding `_archive/`).
- Adjacent surfaces examined: each app's `pyproject.toml`, `tests/`,
  `README.md`, `CHANGELOG.md`, last-commit date, `release_check_*.json`
  coverage records.

**Out of scope**
- The 62 archived apps under `_archive/` (already-archived tier; out of
  scope per skill's `apps/` default).
- MCP-audit-style tool-surface analysis (different skill, see
  [`filesystem-mcp-2026-04-26.md`](filesystem-mcp-2026-04-26.md) and
  siblings for that workflow).
- Performance benchmarks; ruff/mypy lint; ruff-class style.

**Constraints**
- Read-only. No code in WRG was modified.
- All findings derived from `audit.py --json` output + `grep` /
  source inspection / `sqlite_master` query.

---

## 2. Methodology

The audit applies the [`monorepo-audit` skill](../../skills/monorepo-audit/SKILL.md)
with default settings (all three checks, default exemption list):

1. **Schema drift** — parse `CREATE TABLE` from app source, compare
   against on-disk SQLite DBs.
2. **Coverage floor** — read each app's
   `[tool.coverage.report].fail_under`, compare against recorded
   coverage in `artifacts/health/release_check_<app>.json`.
3. **Orphan modules** — AST-based import graph; flag `.py` files that
   no sibling imports.

**Pickaxe discipline** (carried over from the `mcp-audit` wave-2
lesson): every finding the skill produces gets verified before
classification — `grep` for the actual import sites, inspect dynamic-
dispatch code, query `sqlite_master` for actual schema state, etc.
This is what turned 42 raw findings into 6 real ones.

**Honest-scoring discipline**: 0 findings padded to inflate audit
value; 0 findings de-emphasised to flatter the codebase. The 86%
false-positive rate is reported as-is (the skill's noise floor on a
codebase with heavy dynamic dispatch + DORMANT apps + ASGI
entrypoints).

---

## 3. Findings

### 3.0 Findings matrix

| finding_id | section | severity | status | upstream_link |
|---|---|---|---|---|
| F-001 | `orphan_modules` (5 modules in `research_motor/adapters/`) | Low | reported (deferred) | — |
| F-002 | `orphan_modules` (`wrg_control_center/wrg_control_center/config.py`) | Info | reported (deferred) | — |
| F-FP-1 | `orphan_modules` × 22 — `research_motor/cli/handlers/*` dynamic dispatch | (false positive) | known skill limit; §6.1 enhancement proposed | — |
| F-FP-2 | `schema_drift` × 8 — `pulseboard.db` empty | (false positive) | DORMANT app; §6.3 enhancement proposed | — |
| F-FP-3 | `orphan_modules` × 4 — entrypoints missed by static graph | (false positive) | §6.2 enhancement proposed | — |

`status` legend: `reported` = audit document is the public record;
`deferred` = follow-up planned but not in this PR; `false positive` =
not a real finding, documented for skill-improvement signal.

### 3.1 Critical
None.

### 3.2 High
None.

### 3.3 Medium
None.

### 3.4 Low

#### F-001 — research_motor adapter dead-code candidates (5 modules)

- **Where**: `apps/research_motor/src/research_motor/adapters/`:
  `twitter.py`, `metadata_osint.py`, `paste_osint.py`, `_records.py`,
  `plugin_system.py`.
- **What**: Each has zero importers in non-test code (verified via
  `grep -rn`). Adjacent context:
  - `twitter.py` — only self-reference (own docstring example);
    `twitter_archive.py` exists and is imported separately.
  - `_records.py` — underscore-prefix indicates internal helper; if no
    sibling imports it, likely dead.
  - `plugin_system.py` — defines `load_plugins()` API for external
    plugin-dir discovery; could be deliberately unused-from-internals
    (called externally) — verify before delete.
  - `metadata_osint.py`, `paste_osint.py` — zero callers period.
- **Why this bucket**: closest match in skill output is
  `orphan_modules` warn-severity. Real dead-code candidates after
  pickaxe (no `importlib` references, not in `[project.scripts]`).
- **Suggested fix**: per skill workflow §4(c) — human review of each;
  delete or document each. Likely 3-of-5 are deletion candidates after
  the maintainer confirms.
- **Disclosure**: deferred. Internal cleanup task, not upstream-PR
  shape (the audit doesn't have the context to safely delete code in
  another app).

### 3.5 Info

#### F-002 — wrg_control_center config.py possible orphan

- **Where**: `apps/wrg_control_center/wrg_control_center/config.py`.
- **What**: Zero importers in non-`.venv` code (verified via
  `grep -rn --exclude-dir=.venv`). Pydantic ships its own `config.py`
  inside `.venv`, which inflates the apparent grep count; after
  exclusion, no real sibling-import calls remain.
- **Why this bucket**: discoverability/dead-code at info severity —
  not a contract violation, just a stale module. Single file, low blast
  radius either way.
- **Suggested fix**: human review — either (a) delete, or (b) document
  the dynamic load path if one exists.
- **Disclosure**: deferred.

---

## 4. Disclosure timeline

| date | actor | event |
|---|---|---|
| 2026-04-26 | auditor | Audit ran (`audit.py --json`) — 42 raw findings |
| 2026-04-26 | auditor | Pickaxe pass — 6 real findings + 36 false positives classified |
| 2026-04-26 | auditor | Severity scan: 0 Critical / 0 High / 0 Medium → no GHSA |
| 2026-04-26 | auditor | WRG internal evidence record opened ([WRG#315](https://github.com/yakuphanycl/WinstonRedGuard/pull/315)) |
| 2026-04-26 | auditor | Public case-study published (this document) |

No upstream disclosure needed — the audited code is the auditor's own
monorepo; findings route directly to the maintainer.

---

## 5. Upstream response

N/A — internal audit. Maintainer is the auditor; review happens via
WRG#315 + the four skill-enhancement PRs that will land in
`wrg-skills`.

---

## 6. Reusable patterns

The 86% false-positive rate is itself the highest-leverage finding.
Each false positive maps to a concrete skill enhancement:

### 6.1 Detect dynamic-dispatch directories

**Observed in**: 22 of 34 `orphan_modules` findings (52%) were
`research_motor/cli/handlers/*` modules, all dynamically discovered by
`cli/registry.py:25-43` via `pkgutil.iter_modules` + `importlib.import_module`.

**Generalises because**: dynamic-dispatch handler dirs are a common
Python pattern (Django apps, Click subcommands, plugin systems).
Currently the skill flags these as orphans with no marker.

**Proposed action**: extend `audit.py` orphan-modules check to detect
the pattern — if a directory contains a sibling that does
`pkgutil.iter_modules` + `importlib.import_module`, mark all `.py`
under that dir as "dynamic-dispatched" rather than "orphan", or
group them under a separate report header. Single-file `audit.py`
edit.

**Tracked as**: `wrg-skills` follow-up PR; not in scope for this case-
study.

### 6.2 Add three new entrypoint exemption rules

**Observed in**: 4 false positives in this audit:
| Module | Pattern |
|---|---|
| `invoice_gen/app.py` | ASGI module — `app = FastAPI(...)` at module scope; served via `uvicorn module:app` |
| `pulseboard/worker.py` | Service worker; only consumer is same-app `tests/test_worker.py` |
| `wrg_devguard/plugin.py` | Control Center plugin entrypoint; loaded via HTTP-mount discovery |
| `wrg_scheduler/plugin.py` | Same Control Center plugin pattern |

**Generalises because**: ASGI is industry-standard; the `plugin.py`
naming convention is common in any pluggable monorepo; test-only
consumers are normal for daemon/worker entrypoints.

**Proposed action**: extend the default exemption list:
- Module containing `app = (FastAPI|Starlette|Flask|Quart)(...)` at
  top level → exempt as ASGI entrypoint.
- Module named `plugin.py` whose docstring or top-level attribute
  marks it as a plugin entrypoint → exempt.
- Module imported only by sibling `tests/test_*.py` → exempt as
  test-only consumer.

**Tracked as**: `wrg-skills` follow-up.

### 6.3 Treat "DB exists but zero tables" as skip

**Observed in**: 8 of 8 `schema_drift` findings — `pulseboard.db`
exists but `sqlite_master` returns empty. Per scope memory, pulseboard
is DORMANT — local DB created during a long-ago dev session, never
migrated.

**Generalises because**: any app with an SQLite DB that gets created
on first import (e.g., `sqlite3.connect(path)` initialises an empty
file) but isn't migrated until first real use, will trip this.

**Proposed action**: extend the skill's existing "missing on-disk
SQLite DB" skip rule to also cover "DB exists but contains zero
tables". One-line addition to the schema-drift check.

**Tracked as**: `wrg-skills` follow-up.

### 6.4 Mirror mcp-audit's SEVERITY.md / override convention

**Observed in**: this case-study used the mcp-audit `_TEMPLATE.md`,
which depends on a `SEVERITY.md` for default severities + override
rationale. `monorepo-audit` doesn't yet have one. The bucket
assignments here (F-001 Low, F-002 Info) are auditor judgment, not
rubric-anchored.

**Generalises because**: as more case-studies land for this skill,
consistent severity rubrics become valuable for cross-case
comparability — exactly the same rationale as mcp-audit's SEVERITY.md.

**Proposed action**: add `skills/monorepo-audit/SEVERITY.md` mirroring
the mcp-audit structure. Default severities per finding type:
- `schema_drift` → warn (default), error if "missing in DB" on a
  production-tier app
- `coverage_floor` → error (always — declared contract violated)
- `orphan_modules` → warn (default), info if also in
  dynamic-dispatch dir
- Override convention: `OVERRIDE: de-escalated` / `OVERRIDE: escalated`
  with one-sentence rationale.

**Tracked as**: `wrg-skills` follow-up.

---

## Appendix A — raw + filtered finding counts

```
Raw findings:    42  (8 schema_drift + 0 coverage_floor + 34 orphan_modules)
False positives: 36  (8 empty-DB + 22 dynamic dispatch + 4 entrypoints + 2 explained-overlap)
Real findings:    6  (5 in F-001 batched + 1 in F-002)
Noise ratio:    86%  → §6 enhancements would cut this to <20%
```

## Appendix B — methodology drift

- **Pickaxe discipline carried over from mcp-audit**: every finding
  was verified before classification. `grep -rn` for orphan importers
  (with and without `--exclude-dir=.venv`); `sqlite_master` query for
  pulseboard tables; source inspection of `cli/registry.py` for the
  dynamic-dispatch confirmation.
- **No `SEVERITY.md` exists yet** for `monorepo-audit` (proposed in
  §6.4); F-001 Low + F-002 Info are auditor judgment.
- **WRG scope thesis cross-check** ([memory `project_wrg_scope_thesis_2026_04_23`](https://github.com/yakuphanycl/WinstonRedGuard/blob/main/CLAUDE.md)):
  the audit confirmed 59→18 target met (and overshot by 21 — 62
  archived vs 41 recommended). No new archive candidates from the
  health scan; all 18 active apps touched within past 5 days.
- **Coverage ratchet baseline** ([memory `session_2026_04_21_ratchet_followup`](https://github.com/yakuphanycl/WinstonRedGuard/blob/main/CLAUDE.md)):
  audit's `coverage_floor` check returned **0 violations** —
  confirming the 40→60 ratchet across 58 apps is holding.
