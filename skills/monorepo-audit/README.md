# `monorepo-audit` skill

Audit a Python monorepo for schema drift, coverage-floor drift, and orphan
modules. Skill procedure: [`SKILL.md`](SKILL.md). The script is fast (no
network, stdlib + optional `tomli`, walks the repo and finishes in seconds)
and read-only — produces a markdown or JSON report with no mutations.

## Quick links

| Document | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Skill procedure — what the audit does and how Claude runs it |
| [`scripts/audit.py`](scripts/audit.py) | The audit script itself (`python scripts/audit.py --help`) |
| [`references/`](references/) | Layout conventions and configuration notes |

## Real-world case studies

External and internal audits that have used this skill, with severity
summaries.

| Target | Audit date | Severity summary | Case-study |
|---|---|---|---|
| `yakuphanycl/WinstonRedGuard` (18 active apps + 62 archived) | 2026-04-26 | 0 C / 0 H / 0 M / 1 L / 1 I (42 raw → 6 real after pickaxe) | [`wrg-monorepo-2026-04-26.md`](../../docs/case-studies/wrg-monorepo-2026-04-26.md) |

When an audit lands, the case-study links to a document under
[`docs/case-studies/`](../../docs/case-studies/). The format mirrors
[`mcp-audit`](../mcp-audit/README.md)'s case-study convention so cross-skill
audits read consistently.

## How to use

### Audit your own monorepo

Read [`SKILL.md`](SKILL.md). Quickstart from the repo root:

```bash
python <path-to>/skills/monorepo-audit/scripts/audit.py            # markdown
python <path-to>/skills/monorepo-audit/scripts/audit.py --json     # JSON
python <path-to>/skills/monorepo-audit/scripts/audit.py --apps-dir packages
```

Exit code is `0` (no findings) or `1` (at least one finding) — useful in
CI.

### Apply pickaxe before claiming "real"

The first WRG case-study showed an **86% false-positive rate** on the raw
audit output. Most false positives map to known patterns:

- Dynamic-dispatch directories (`pkgutil.iter_modules` +
  `importlib.import_module`) — every module looks orphan to the static
  graph.
- ASGI / plugin / worker entrypoints not in `[project.scripts]`.
- SQLite DB exists but contains zero tables (DORMANT app).

Verify each finding via `grep`, source inspection, or DB introspection
before treating it as actionable. The case-study's §6 documents proposed
skill enhancements that would reduce the noise floor.

## What this skill is NOT

- Not a security scanner — `bandit` / `gitleaks` / `mcp-audit` cover that.
- Not a lint / type-check — `ruff` / `mypy` cover that.
- Not a fix-applier — pure read-and-report; the maintainer ships the fixes.
- Not a multi-language tool — Python monorepos with `pyproject.toml`
  per-app only.
