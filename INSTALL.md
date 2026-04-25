# Install guide

Quick reference for installing skills from this repo across the various
agent CLIs that consume the [skills format](https://skills.sh).

---

## TL;DR

```bash
npx skills install github.com/yakuphanycl/wrg-skills
```

The installer asks two questions that materially change behaviour:

1. **Which skills to install** — pick what you actually want
2. **Installation scope** — `Project` or `Global` (see below)
3. **Which agents** — multi-select; Claude Code is **NOT** in the list

If you're using **Claude Code**, the npx installer doesn't help directly. See
the [Claude Code](#claude-code) section below.

---

## Installation scope — `Project` vs `Global`

The installer's scope choice determines where skill files land.

### `Project` scope

Drops skills into `./.agents/skills/<skill-name>/` of the **current working
directory**. Plus a `skills-lock.json` at the cwd root.

When to use:
- You want this skill ONLY for agents working in this specific repo
- The skill is project-specific (e.g. encodes layout assumptions of one
  monorepo)
- You don't want to pollute home directory with global skills

**Caveat for git-tracked repos**: the installer creates files inside your
working tree. Add `/.agents/skills/` and `/skills-lock.json` to `.gitignore`
unless you intentionally want to commit those copies.

### `Global` scope

Drops skills into `~/.agents/skills/<skill-name>/` (user home).

When to use:
- You want the skill available everywhere on this machine
- The skill is general-purpose (memory-check, monorepo-audit fit here)
- One install, many projects

---

## Agent compatibility

The npx installer offers ~12 agents in the multi-select. As of 2026-04-25 the
list includes (alphabetical): **Amp, Antigravity, Cline, Codex, Cursor, Deep
Agents, Firebender, Gemini CLI, GitHub Copilot, Kimi Code CLI, OpenCode,
Warp**.

For each selected agent, the installer copies the skill to that agent's
expected directory layout. The same `SKILL.md` file is the source — only the
destination path differs.

**Claude Code is not in this list.** See below.

---

## Claude Code

Claude Code reads skills from `~/.claude/skills/<skill-name>/`. The npx
installer doesn't currently target this path.

### Option 1 — manual copy

```bash
git clone https://github.com/yakuphanycl/wrg-skills.git /tmp/wrg-skills
cp -r /tmp/wrg-skills/skills/<name> ~/.claude/skills/<name>
```

Refresh Claude Code; the skill will appear in `/<name>` slash command and
trigger phrase matches.

### Option 2 — symlink (if you want updates to track the repo)

```bash
git clone https://github.com/yakuphanycl/wrg-skills.git ~/code/wrg-skills
ln -s ~/code/wrg-skills/skills/<name> ~/.claude/skills/<name>
# Pull in ~/code/wrg-skills updates the live skill
```

### Option 3 — npx install with Global scope, then symlink (Linux/macOS)

If your other agents and Claude Code agree on the skill name:

```bash
npx skills install github.com/yakuphanycl/wrg-skills    # pick Global
ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>
```

This does NOT work cleanly on Windows (symlinks need elevated permissions);
use Option 1 there.

---

## Verifying an install

After install, check the skill file landed:

```bash
# Project scope
ls .agents/skills/<name>/SKILL.md

# Global scope
ls ~/.agents/skills/<name>/SKILL.md

# Claude Code
ls ~/.claude/skills/<name>/SKILL.md
```

For Claude Code specifically, restart your session and try a trigger phrase
from the skill's `description` frontmatter. The skill should activate.

---

## Uninstalling

```bash
# Project scope
rm -rf .agents/skills/<name>
rm skills-lock.json   # if you only had one skill installed

# Global scope
rm -rf ~/.agents/skills/<name>

# Claude Code
rm -rf ~/.claude/skills/<name>
```

No registry entry to clean up — the skills format is purely file-based.

---

## Updating

`npx skills install` against the same repo will offer to overwrite existing
copies. For Claude Code (manual install), re-pull the repo and re-copy.

For long-term tracking, prefer Option 2 (symlink) over re-copy. Skill files
are small and rarely change incompatibly, but you'll get fixes for free.

---

## Troubleshooting

**"Found 3 skills" but I only see 1 installed.** The selector is
multi-select — press space to toggle each, then enter to confirm. Default is
nothing selected.

**Installed but Claude Code doesn't trigger it.** Skills must be at
`~/.claude/skills/<name>/`, not `~/.agents/skills/<name>/`. The npx
installer's "Global" scope writes to `~/.agents/`, not `~/.claude/`. Manual
copy or symlink (Option 1/2 above) bridges the gap.

**`.agents/skills/` showing up in `git status` after install.** Expected —
add to `.gitignore`. The installer doesn't manage your repo's hygiene.

**`npx skills` itself fails.** Make sure Node 18+ and a working network.
First-time runs install `skills@<version>` to your npm cache.
