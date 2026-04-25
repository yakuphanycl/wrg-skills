# wrg-skills

## Quick install

```bash
npx skills install github.com/yakuphanycl/wrg-skills
claude
/skills
```

## Status

[![lint](https://github.com/yakuphanycl/wrg-skills/actions/workflows/lint.yml/badge.svg)](https://github.com/yakuphanycl/wrg-skills/actions/workflows/lint.yml)

Claude Code skills authored alongside the [WinstonRedGuard (WRG)](https://github.com/yakuphanycl/WinstonRedGuard) monorepo. Each skill is a self-contained `SKILL.md` (and optional accompanying scripts/references) that teaches Claude a specific capability.

## Install

```bash
npx skills install github.com/yakuphanycl/wrg-skills
```

This adds the skills under `~/.claude/skills/<skill-name>/`. Each skill loads on-demand when its trigger phrases match.

## Per-skill matrix

| Skill | Triggers | What it does |
|---|---|---|
| [`monorepo-audit`](skills/monorepo-audit/) | "audit my monorepo", "schema drift", "fail_under check", "orphan modules" | Three static checks across a Python monorepo: SQLite schema drift, coverage-floor drift, orphan modules. Markdown + JSON report, exit code 0/1. Read-only. |
| [`memory-check`](skills/memory-check/) | `/memory-check`, "what have I been correcting", "scan for friction patterns" | Pause-and-audit pass over the current conversation — surfaces correction patterns, repeated friction, real-time mismatches as candidate `feedback` memory entries with per-entry user approval. |
| [`wrg-devguard-paste-lint`](skills/wrg-devguard-paste-lint/) | "is this prompt safe?", "any secrets in this?", "lint this prompt" | Runs [`wrg-devguard`](https://pypi.org/project/wrg-devguard/) policy lint or secret scan against a pasted snippet. Returns structured findings (rule_id, severity, position). Useful for prompt-injection detection and credential leak review. |
| [`instinct`](skills/instinct/) — *mirror* | "remember this pattern", "log this fix", "what have we seen before", "/instinct" | Self-learning memory for AI coding agents (tool sequences, preferences, recurring fixes). Auto-promotes mature patterns into suggestions. **Mirrored from [yakuphanycl/instinct](https://github.com/yakuphanycl/instinct) v1.4.0**; runs on top of the [`instinct-mcp`](https://pypi.org/project/instinct-mcp/) PyPI server (~1,400 monthly downloads). |

## Why these skills

These are skills that surfaced naturally during day-to-day work on the WRG monorepo (4-agent orchestration, multi-app Python project, AI safety tooling). They graduated from `~/.claude/skills/` into a published repo when the patterns stopped being personal and started being reusable.

Adjacent ecosystem: [browserbase/skills](https://github.com/browserbase/skills) (browser automation), [google/skills](https://github.com/google/skills) (cloud-product domain experts), [anthropic-skills](https://github.com/anthropics/anthropic-skills) (canonical first-party set).

## Authoring conventions

Each skill follows the standard Claude Code skill format:

```
skills/<skill-name>/
├── SKILL.md                          # frontmatter + body (required)
├── scripts/                          # optional, executable helpers
│   └── ...
└── references/                       # optional, supporting docs
    └── ...
```

`SKILL.md` frontmatter:

```yaml
---
name: <skill-name>             # snake-case identifier
description: <when to invoke>  # the trigger description Claude reads
---
```

The `description` is the most important field — it's what Claude reads to decide whether the skill applies. Be specific: list trigger phrases, scope conditions, and explicit non-triggers.

## Contributing

This is a single-author repo (yakuphanycl) for now — the skills are byproducts of WRG work. If a skill seems generally useful and you want to extend it, open an issue first to discuss scope. PRs welcome but the bar is "Markdown-clean, deterministic, no surprise side effects."

Open an issue before larger changes. PRs must pass CI. `SKILL.md` frontmatter must include `name:` and `description:`, and `name:` must match the skill directory; the exact validation rules live in `.github/workflows/scripts/check_frontmatter.py`.

## License

[MIT](LICENSE) — same as WRG core.
