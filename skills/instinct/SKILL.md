---
name: instinct
description: Self-learning memory for AI coding agents. Record tool sequences, user preferences, and recurring fixes you observe; let mature patterns guide future behavior. Use when the user asks you to "remember this", establishes a preference, or when you notice you are repeating a fix or sequence you have seen before.
---

> **Mirrored skill** — canonical source: [yakuphanycl/instinct@v1.4.0](https://github.com/yakuphanycl/instinct/blob/master/.claude/skills/instinct/SKILL.md). This copy in `wrg-skills` exists for cross-discovery; for upstream changes, watch the [`instinct`](https://github.com/yakuphanycl/instinct) repo. Last sync: 2026-04-25.

# instinct skill

`instinct` is a self-learning memory layer. It observes patterns, tracks
their confidence over time, auto-promotes recurring patterns into
suggestions, and surfaces them back to you in the next session. This skill
runs on top of the `instinct-mcp` server.

## When to observe

Record a pattern whenever you notice one of these signals. Err on the side
of observing too much — low-confidence patterns decay if they do not
recur.

- **Tool sequences** the user follows deliberately (`seq:a->b->c`)
- **Preferences** the user states or corrects you on (`pref:key=value`)
- **Fixes** you apply that look like they will recur (`fix:description`)
- **Combinations** of things the user uses together (`combo:a+b`)

## Naming convention

Always prefix pattern names with their type:

| Prefix | Shape | Example |
|---|---|---|
| `seq:` | tool/action sequence | `seq:lint->format->test` |
| `pref:` | user preference | `pref:commit-style=conventional` |
| `fix:` | recurring fix | `fix:import-sort-on-save` |
| `combo:` | things used together | `combo:pytest+ruff` |

## Workflow

1. **Check for suggestions** at the start of substantial work:
   ```
   instinct__suggest project="<repo-name>"
   ```
   Apply any returned patterns with confidence ≥ 0.7 automatically.
   Mention patterns with confidence 0.4–0.7 as soft suggestions.

2. **Record observations** as you work:
   ```
   instinct__observe pattern="seq:ruff->pytest" project="<repo-name>"
   ```
   Confidence increments on every observation. A pattern seen 3+ times in
   a week auto-promotes to "suggest" status.

3. **Periodic consolidation** (once per long session or when the user
   says "tidy up memory"):
   ```
   instinct__consolidate
   ```

4. **End-of-session summary** (optional, for long sessions):
   ```
   instinct__session_summary project="<repo-name>"
   ```
   Emits a markdown digest of patterns observed this session.

## Do

- Prefix every pattern (`seq:`, `pref:`, `fix:`, `combo:`). Unprefixed
  patterns are harder to search and auto-promote.
- Include a short `metadata` object with file paths or tool versions when
  useful for disambiguation.
- Trust high-confidence suggestions — they survived repeated validation.
- Alias synonyms to keep the graph clean
  (`instinct__alias_pattern old new`).

## Do not

- Do not observe personal or sensitive info. The store is local but the
  export paths (`export-claude-md`, `export-rules`) round-trip to disk.
- Do not record one-off fixes. If it will not happen again, let it fade.
- Do not manually inflate confidence by re-observing the same pattern in
  a tight loop — consolidate does that legitimately.
- Do not fight low-confidence suggestions. Apply them once, then let the
  feedback loop strengthen or demote them.

## Install

```bash
pip install instinct-mcp
claude mcp add instinct -- instinct serve
```

Or in any MCP-compatible client's config:

```json
{
  "mcpServers": {
    "instinct": {
      "command": "instinct",
      "args": ["serve"]
    }
  }
}
```

---

**Sync note for `wrg-skills` maintainers**: this is a mirror, not a fork. To
pick up upstream improvements, re-copy from
`yakuphanycl/instinct/.claude/skills/instinct/SKILL.md` and bump the "Last
sync" date in the provenance line above. Drift detection should eventually
land as a CI step that hashes the upstream file and compares; until then,
manual sync on a quarterly cadence (or when upstream releases new minor) is
the convention.
