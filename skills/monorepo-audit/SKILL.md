---
name: monorepo-audit
description: Audit a Python monorepo for schema drift between SQLite code/DBs, coverage-floor drift between pyproject fail_under and recorded coverage, orphan Python modules never imported anywhere, declared-adapter contracts that drifted from the actual module set, Protocol type-contracts where the claimed implementer is missing methods, plugin-loader entry-point drift, and public-API re-export drift between README docs and __init__.py. Use this skill whenever the user mentions governance checks, schema drift, coverage floor, orphan modules, dead code detection in a monorepo, adapter contracts / `REQUIRED_ADAPTERS`, Protocol contract drift, plugin loaders, entry points, public API, re-export, doc drift, app/package audit, "is this module used?", fail_under vs actual coverage mismatch, or any phrase like "audit my repo", "check my monorepo", or "/monorepo-audit". Also use when you see a user working in a repo with multiple `apps/<name>/` or `packages/<name>/` subprojects and they're thinking about hygiene, dead code, or consistency across apps — even if they don't specifically ask for an "audit". The output is a human-readable markdown report plus structured JSON, and the skill is fast (no network, stdlib + optional tomli fallback, walks the repo and finishes in seconds).
---

# monorepo-audit

## What this skill does

Runs seven static checks across a Python monorepo and reports findings in a
single report. Works on any repo where subprojects live under `apps/<name>/`,
`packages/<name>/`, or a configurable layout. No network calls, no mutation —
pure read-and-report.

The seven checks:

1. **Schema drift** — parses `CREATE TABLE` statements out of app source code,
   builds the expected column set, compares against live on-disk SQLite DBs
   under `~/.<something>/<app>.db` (or configurable). Flags extra columns on
   either side and missing tables.
2. **Coverage floor** — reads each app's `pyproject.toml`
   `[tool.coverage.report].fail_under` value, compares against recorded
   coverage (reads `artifacts/health/release_check_<app>.json` or
   `coverage.xml` when present). Flags apps whose actual coverage is below
   their declared floor.
3. **Orphan modules** — walks each app's `src/` tree (or flat layout),
   builds an AST-based import graph, flags `.py` files that no sibling
   imports. Entrypoints (`__init__.py`, `__main__.py`, `main.py`, and
   targets of `[project.scripts]`) are exempt.
4. **Required adapters** — for any app with an `adapters/` subpackage,
   parses `adapters/__init__.py` for a `REQUIRED_ADAPTERS = [...]` list (or
   a module-name-style `__all__`). Flags any name in the list that has no
   matching `adapters/<name>.py` or `adapters/<name>/__init__.py`. Plain
   `__all__` is treated leniently: it only counts as a module-name list
   when at least one of its entries resolves to a real module — otherwise
   the audit assumes `__all__` is a re-export symbol list and skips the
   app with a note.
5. **Type contract drift** — for Protocol classes defined in
   `<pkg>/**/protocols.py` or `<pkg>/**/*_proto.py`, finds classes that
   claim to implement them via two AST patterns:
   - typed assignment: `var: ProtoName = SomeClass(...)`
   - factory return:   `def f(...) -> ProtoName: return SomeClass(...)`
   Flags any implementer that is missing one or more of the Protocol's
   declared methods. AST-only — no runtime import. Skips a Protocol when
   it's `@runtime_checkable` AND at least one `tests/test_*.py` calls
   `isinstance(_, ProtoName)` — in that case the runtime check is treated
   as the contract.
6. **Plugin-loader drift** — AST-scans for `importlib.metadata.entry_points()`
   or `pkg_resources.iter_entry_points()` calls. For each app that uses a
   plugin loader, parses `pyproject.toml` `[project.entry-points.*]` groups
   and verifies every `module:attr` target resolves to an importable symbol
   in the app's source tree. No runtime import — pure AST resolution.
7. **Public-API re-export drift** — for each app's top-level `__init__.py`,
   builds the set of names in `__all__` (or all non-`_` public names if
   `__all__` is absent). Scans `README.md` for backticked `pkg.module.Symbol`
   references and flags any documented symbol not in the exported set.
   Rationale: README promises != import surface = doc drift.

## When to use

Strongly trigger on any of:
- "audit my monorepo" / "audit this repo" / "governance check"
- "schema drift" / "coverage floor" / "fail_under" / "orphan modules"
- "required adapters" / "REQUIRED_ADAPTERS drift" / "adapter contract"
- "type contract drift" / "Protocol drift" / "missing protocol methods"
- "plugin loader" / "entry points" / "entry-point drift"
- "public API" / "re-export" / "__all__" / "doc drift" / "README vs __init__"
- "is this module used?" / "dead code in my repo"
- "/monorepo-audit" (explicit slash)
- User in a repo with `apps/*/pyproject.toml` asking about hygiene/cleanup

Don't trigger if:
- Single-package repo (no `apps/` or `packages/` layout) — skill expects multi-app
- User wants test coverage metrics, not the floor discipline — different tool
- User wants linting / type checking — that's ruff/mypy, not this

## How to run

From the repo root:

```bash
python <skill-path>/scripts/audit.py            # human-readable markdown
python <skill-path>/scripts/audit.py --json     # JSON report
python <skill-path>/scripts/audit.py --only coverage_floor  # single check
python <skill-path>/scripts/audit.py --only plugin_loader_drift   # entry-point resolution
python <skill-path>/scripts/audit.py --only public_api_not_reexported  # README vs __init__
python <skill-path>/scripts/audit.py --apps-dir packages    # custom layout
python <skill-path>/scripts/audit.py --skip schema_drift    # opt out of a check
```

Exit code:
- `0` — no findings
- `1` — at least one finding

Flags:
- `--json` — emit JSON instead of markdown
- `--apps-dir DIR` — which directory contains the subprojects (default: `apps`; common alternatives: `packages`, `projects`)
- `--only CHECK` — run only one check (schema_drift / coverage_floor / orphan_modules / required_adapters / type_contract_drift / plugin_loader_drift / public_api_not_reexported)
- `--skip CHECK` — skip one check (can be passed multiple times)
- `--health-dir DIR` — where release/coverage JSONs live (default: `artifacts/health`)

## Workflow for Claude when this skill triggers

1. **Verify layout.** Confirm the repo has `apps/*/pyproject.toml` (or the
   user's configured layout). If not, tell the user — skill doesn't fit.
2. **Run the audit script.** Start with the default (all five checks, markdown).
3. **Interpret the report.**
   - Severity: `warn` (default) is informational; `error` means the check
     asserts a contract was violated.
   - Findings are per-(check, app, detail). Group them by app if the user
     wants to know "what's wrong with app X".
4. **Propose action — don't apply.** For each finding:
   - Schema drift: explain whether the code or the DB is the source of truth.
     Usually code-is-source-of-truth → DB needs migration.
   - Coverage floor: either raise the floor (if actual is higher) or improve
     tests (if actual is lower). Don't silently lower the floor.
   - Orphan modules: may be (a) genuinely dead code → delete, (b) exempt
     entrypoint the graph missed → add to exemption list, or (c) imported
     dynamically → flag for human review.
   - Required adapters: contract list mentions a name with no module —
     either rename the contract entry, restore the missing module, or
     drop the name from `REQUIRED_ADAPTERS` / `__all__` if the adapter
     was intentionally retired.
   - Type contract drift: implementer is missing methods declared by the
     Protocol — either add the method to the class, change the type
     annotation to the narrower contract the class actually satisfies,
     or split the Protocol if multiple shapes are now needed.
   - Plugin-loader drift: the entry-point target is broken — either (a) the
     module was renamed/deleted → update pyproject.toml, or (b) the attr was
     refactored → fix the `module:attr` reference. If no `[project.entry-points]`
     is declared but the code calls `entry_points()`, it may be consuming
     plugins from *other* packages (note, not a finding).
   - Public-API re-export: README documents a symbol that `__init__.py` doesn't
     expose. Either (a) add the symbol to `__all__` / re-import it in
     `__init__.py`, or (b) update README to remove the stale reference.
5. **Ask before mutating.** The skill is read-only by design. If the user
   wants a fix applied, generate the edit and confirm before writing.

## Conventions the skill assumes

See `references/conventions.md` for layout expectations, default paths, and
how to configure non-standard monorepos.

## Edge cases / known limits

- **Missing on-disk SQLite DB:** Skipped with a note — the app may simply
  not have been run yet. Don't flag.
- **Dynamic imports** (`importlib.import_module(name)` with a runtime name):
  orphan-modules will false-positive on these. Check for plugin registries
  or entry-point manifests before deleting flagged modules.
- **Python 3.10:** `tomllib` isn't stdlib; skill falls back to `tomli` if
  installed, otherwise skips pyproject-based checks with a note.
- **Non-Python monorepos:** Unsupported. Skill requires `pyproject.toml`
  per-app to meaningfully check coverage.
- **`required_adapters` triggers only on `adapters/` subpackages** with a
  contract list. Apps that use a different convention (e.g.,
  `connectors/`, `plugins/`) won't be checked. The detector is
  intentionally narrow — adapter packages are where the re-export-vs-
  module-name drift surfaces in practice.
- **`type_contract_drift` resolves implementer classes by AST only.** It
  matches `var: ProtoName = SomeClass(...)` and `def f() -> ProtoName:
  return SomeClass(...)` patterns. Bare-name returns (`return
  some_instance`) and cross-package class references are conservatively
  skipped — rather than guessing, the audit produces no finding for
  those cases.
- **Plugin loaders consuming external packages:** If an app calls
  `entry_points()` to discover plugins from *other* installed packages
  (not its own `[project.entry-points]`), the check emits a note, not
  a finding.
- **README symbol references in code blocks:** The regex matches any
  backticked `pkg.module.Symbol` pattern. Symbols documented as examples
  or in code blocks may cause false positives — verify against the
  actual import surface before acting.

## Report format

Markdown output (default):

```markdown
# Monorepo audit — <repo-name>
_Generated <timestamp>_

## Summary
- 5 checks ran
- 9 findings (2 error, 7 warn)
- 18 apps scanned

## schema_drift
- **app_a** [warn]: table `users` on-disk has extra columns: email_verified
- **app_b** [error]: table `sessions` missing on-disk (expected by code)

## coverage_floor
- **app_c** [error]: fail_under=60, actual=42 (drift: -18)

## orphan_modules
- **app_d** [warn]: `helpers/legacy.py` — no importers found

## plugin_loader_drift
- **app_e** [warn]: entry-point 'my_plugins.bar' target 'app_e.plugins.bar:BarPlugin' does not resolve to an importable symbol in src/

## public_api_not_reexported
- **app_f** [warn]: README documents `app_f.core.Engine` but 'Engine' is not re-exported from app_f/__init__.py
```

JSON output (`--json`):

```json
{
  "repo_root": "/path/to/repo",
  "generated_at": "2026-04-23T19:30:00Z",
  "apps_scanned": 18,
  "checks": ["schema_drift", "coverage_floor", "orphan_modules",
             "plugin_loader_drift", "public_api_not_reexported"],
  "findings": [
    {"check": "coverage_floor", "app": "app_c",
     "detail": "fail_under=60, actual=42 (drift: -18)",
     "severity": "error"}
  ],
  "skipped": ["schema_drift:app_e (no SQLite DB on disk)"]
}
```
