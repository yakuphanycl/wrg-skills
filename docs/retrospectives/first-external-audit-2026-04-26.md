---
audit_target: modelcontextprotocol/servers/src/filesystem (@modelcontextprotocol/server-filesystem@0.6.3)
audit_date: 2026-04-26
case_study: docs/case-studies/filesystem-mcp-2026-04-26.md
retro_date: 2026-04-26
author: A (orchestrator, Opus 4.7 1M)
agents_involved: A, B, C
---

# Retrospective — first external MCP audit (2026-04-26)

> The `mcp-audit` skill shipped its first end-to-end external audit on 2026-04-26: 7 PRs across 3 repos in a single wave, coordinated across 3 Claude agents (A/B/C), targeting `@modelcontextprotocol/server-filesystem@0.6.3` in TypeScript. This retrospective captures what worked, what almost didn't, and what should land in the skill / SOP / template before the next external audit (B's `src/git` + C's `src/fetch` are running now).

## 1. Outcomes — what shipped

| Repo | PR | Author | Scope | Status |
|---|---|---|---|---|
| `WinstonRedGuard` | [#307](https://github.com/yakuphanycl/WinstonRedGuard/pull/307) | A | Internal evidence record (186 LOC) | Merged |
| `wrg-skills` | [#7](https://github.com/yakuphanycl/wrg-skills/pull/7) | B | Audit infra: `_TEMPLATE.md` + `disclosure-sop.md` + `SEVERITY.md` 32 rows | Merged |
| `wrg-skills` | [#8](https://github.com/yakuphanycl/wrg-skills/pull/8) | B | SHAPE-005 row + TS-adaptation subsection | Open (solo-gate) |
| `wrg-skills` | [#9](https://github.com/yakuphanycl/wrg-skills/pull/9) | A | Public case-study refile + README live link | Open (solo-gate) |
| `modelcontextprotocol/servers` | [#4045](https://github.com/modelcontextprotocol/servers/pull/4045) | A | F-006 — `read_media_file` cast scope-isolation | Open, CI green |
| `modelcontextprotocol/servers` | [#4046](https://github.com/modelcontextprotocol/servers/pull/4046) | C | F-001..F-005 — `structured-content.test.ts` 2/14 → 14/14 | Open, CI green |
| `modelcontextprotocol/servers` | [#4047](https://github.com/modelcontextprotocol/servers/pull/4047) | B | F-007 + F-008 — `_meta.deprecated` + `read_media_file` docstring | Open, CI in progress |

Headline numbers from the audit itself: 14 tools, avg discoverability **4.50/5**, return-shape consistency **93%**, MCP-layer integration coverage **14% pre-fix → 100% post-#4046**, 0 Critical / 0 High / 0 Medium / 6 Low / 2 Info, all public-batched per disclosure SOP §2 routing. No GHSA filed.

## 2. What worked

### 2.1 Pivot discipline at setup

Original target was the github MCP server. Five minutes in: discovered it had been moved to `modelcontextprotocol/servers-archived` — low disclosure value (audited package effectively dead). Pivoted to `filesystem` immediately based on three criteria captured in the case-study §1: (a) active reference server, (b) high blast radius (file mutation), (c) TypeScript surface (validates the skill's adaptation from FastMCP-Python).

The pivot took less than five minutes from discovery to confirmation. **Lesson**: an "expected target moved/archived" check belongs at audit step 0, not step 3 — current `SKILL.md` doesn't mention this. Proposed addition: see §6.

### 2.2 Severity OVERRIDE convention paid off immediately

Four `TEST-003` findings (untested mutation tools) defaulted to Medium per `SEVERITY.md` row 19. Mechanically routed to Medium → coordinated 90-day private disclosure, which would have been wildly disproportionate for "your test suite doesn't exercise `write_file` end-to-end." Applied `OVERRIDE: de-escalated → Low` per the override convention with explicit per-finding rationale (test infrastructure exists, fix is extension not creation, security-critical layer IS tested). Disclosure routed as public-batched. **The override mechanism worked exactly as designed.**

The case-study finding blocks document the override transparently — the maintainer reading the case-study sees both the default rubric assignment AND the deviation rationale, can disagree, and the audit's severity numbers stay honest.

### 2.3 Dual-output flow (internal evidence + public case-study)

The two-PR-per-finding-set pattern (WRG `docs/decisions/EXTERNAL_MCP_AUDIT_*` for internal record, `wrg-skills/docs/case-studies/*` for public) gave us a stable internal URL while the public case-study was being prepared on B's infrastructure (#7), and let us start writing the public document while waiting for #7 to merge. Without the internal staging file, A would either have had to wait idle for B, or risked drafting in B's worktree (shared-worktree wipe risk per existing memory).

### 2.4 Non-repo staging path during cross-agent waits

Key trick: A drafted the public case-study at `D:\dev\_external\case-study-draft.md` while waiting for B's #7 to merge. This solved two problems at once:
- B's worktree had `session/mcp-audit-infra` checked out — A couldn't safely create files in `wrg-skills/` without risking branch-pointer stomp.
- A had no idle time — drafting started while B was building infrastructure.

When #7 merged, refile took ~2 minutes (open A's own worktree off updated main, copy draft, adjust frontmatter dates, push).

### 2.5 Shared-fork pattern for upstream PRs

Three agents (A/B/C) all needed to push branches to a fork of `modelcontextprotocol/servers`. Instead of three forks (race condition on first push, redundant disk usage), A forked once, cloned once to `D:\dev\_external\mcp-servers-fork`, ran `safe.directory` config once, added `upstream` remote. B and C branched off `origin/main` in the same clone (B used a separate clone for one PR; both work). Three branches, file-disjoint by prompt scoping (A: `index.ts` handler block, B: `index.ts` description block + new `_meta` field, C: `__tests__/structured-content.test.ts` only). Zero file conflicts in the wave.

### 2.6 3-agent role crystallization

Roles fell out cleanly within one wave:
- **A** = orchestrator + judgment work + cross-cutting (this retro is A's natural deliverable).
- **B** = depth + decision briefs + documentation (audit infrastructure, skill extensions, batched Info finding writeup).
- **C** = mechanical / scaffold-heavy / fast-mode parallelism (test extensions: 2/14 → 14/14 in 7m12s).

C's fast-mode (Opus 4.6) was a perfect fit for the test extension work — fixture pattern was established, the work was 12 mostly-identical test blocks following the same template. This is exactly where fast-mode wins; the 7m12s cycle time validates it.

## 3. What almost didn't work

### 3.1 Windows symlink install block

`@modelcontextprotocol/servers` is an npm workspaces monorepo. On Windows without Developer Mode, BOTH `npm install` and `pnpm install` fail with `EISDIR symlink ... -> .../node_modules/@modelcontextprotocol/server-*`. Workspace packages get symlinked into `node_modules`; Windows requires admin/Dev-Mode for symlinks.

Workarounds tried during A's F-006 PR:
1. `npm install --workspaces=false` — fails (root deps reference workspace packages by name).
2. `pnpm install` — uses junctions, still fails on a separate rename step.

**Resolution**: skip local install, trust upstream CI. This worked — both A's #4045 and C's #4046 shipped this way and CI passed all platforms (build + test for filesystem, fetch, memory, git, time, everything, sequentialthinking).

**Lesson for `SKILL.md`**: when targeting an npm workspaces project on Windows, document the ship-and-iterate flow as the default, not the fallback. The audit framework doesn't need local test execution — it needs the diff to be small/surgical/reviewable. CI handles the validation. See §6.

### 3.2 Worktree-checkout collision risk

When A wanted to peek B's branch content (template + SEVERITY + SOP) before refile, the natural move would have been `git checkout origin/session/mcp-audit-infra` in `wrg-skills/`. But B's worktree was actively pointing at `session/mcp-audit-infra` — checkout in another worktree would have triggered "branch already checked out" error (best case) or a branch-pointer stomp (worst case, on legacy git versions).

**Resolution**: used `git show origin/session/mcp-audit-infra:path/to/file` to read content without checkout. No worktree mutation, no branch-pointer movement. This is the documented Multi-session pattern from existing memory but applied here for the first time mid-wave.

**Lesson**: `git show <ref>:<path>` is the safe primitive when peeking another agent's in-flight branch. Worth a brief note in the skill's "Workflow for Claude when this skill triggers" section.

### 3.3 SOP "Medium" routing edge case

The SOP says Medium → coordinated 90-day private disclosure. For an OSS project where the maintainer is highly reachable (active repo, accepting PRs, no `SECURITY.md` complications), the 90-day private window for "your write_file tool doesn't have an integration test" felt disproportionate. The override convention saved the day, but the SOP's edge-case section ("Maintainer is unreachable", "Maintainer asks for a different channel") doesn't directly address "Medium severity, but disclosure is just 'extend your test suite' — public PR is the right channel."

**Lesson for `disclosure-sop.md`**: add an edge case for "Medium severity where the disclosure IS the patch." Not all Medium severities require private notification — some (TEST-003 untested mutation, ERR-002 mixed `raise` vs envelope) are best resolved by an upstream PR that the maintainer can review on its own. See §6.

### 3.4 Audit framework adaptation cost (Python → TypeScript)

The skill was developed against Python FastMCP. Adapting it for the TS surface required four substitutions documented in the case-study §6 and being added to `SKILL.md` by B's #8:
- Inventory grep pattern (`server\.registerTool\(` vs `@mcp.tool()`).
- Input/output schema reading (Zod vs Python annotations).
- Canonical envelope shape (`{content, structuredContent}` vs `{ok, ...}`).
- Error channel (throw + SDK vs in-band envelope).

The adaptation cost was real but bounded — A re-derived all four during the audit, then captured them in case-study §6. B's #8 codifies them. Before the next TS audit, this adaptation should be **read once from the skill, not re-derived**.

**Lesson**: case-study §6 ("Reusable patterns") is the right capture point during the audit, but the patterns must actually feed back into `SKILL.md` quickly. B's #8 doing this in the same wave is the model — don't let pattern capture decay into "we'll add it next time."

## 4. Numbers worth remembering

- **Wave size**: 7 PRs across 3 repos (4 from A, 2 from B, 1 from C).
- **Audit-to-shipping latency**: < 24 hours from "what should we audit?" to all 7 PRs filed.
- **C fast-mode cycle time**: 7m12s for 12-tool test extension PR. The fixture pattern from existing 2 tools was the multiplier.
- **Scope violations across the wave**: 0. File-disjoint enforcement at branch level held.
- **Worktree collisions**: 0. The `git show <ref>:<path>` pattern + non-repo staging path eliminated the risk vectors.
- **Severity inflation observed**: 0. Honest scoring discipline held — case-study reports avg 4.50/5 (high), 0 Critical/High/Medium (after override), all Low/Info.

## 5. What's next (concurrent with this retro)

Wave 2 is running in parallel:

- **B**: auditing `src/git` (Python FastMCP, mutation surface — mirror of filesystem's profile).
- **C**: auditing `src/fetch` (Python FastMCP, smaller surface — fast-mode validation at smaller scale).
- **A**: this retro + upstream PR monitoring + supervision (passive / exception-based).

The wave-2 audits will validate the skill in its native FastMCP-Python ecosystem. If both surface clean (or near-clean), the skill graduates from "validated on the surface it was built for" to "validated across two ecosystems and three external surfaces" — strong basis for inviting external auditors to use it.

## 6. Proposed follow-ups (concrete actions)

Each item below is a discrete follow-up PR. None is urgent — the skill works as-is. These are quality-of-life improvements informed by the first audit.

### 6.1 `SKILL.md` — add "Step 0: target health check"

**Where**: `skills/mcp-audit/SKILL.md`, "How to run" section, before step 1.

**Content** (proposed):

```markdown
0. **Target health check** — before scoping the audit:
   - Confirm the target package is on the active reference list (not in
     `*-archived` repos, not deprecated by the maintainer).
   - Note the latest published version and the commit SHA being audited.
   - If the target was moved/archived, surface this immediately and ask
     the maintainer (or yourself, if self-directing) whether to (a) audit
     the archived version anyway (low disclosure value but skill-validation
     value), or (b) pivot to an active sibling.
```

This codifies the github → filesystem pivot pattern from this audit.

### 6.2 `SKILL.md` — add "Workflow note: peeking in-flight branches"

**Where**: `skills/mcp-audit/SKILL.md`, "Workflow for Claude when this skill triggers" section.

**Content** (proposed addition):

```markdown
9. **Cross-agent coordination** — if multiple Claude agents are running
   parallel branches in the same repo (case-study refile by one agent,
   skill-extension by another, etc.), use `git show <ref>:<path>` to read
   another agent's in-flight content rather than `git checkout <ref>`.
   Checkout in a shared repo can stomp the other agent's worktree branch
   pointer; `git show` is read-only and safe. The `<ref>` can be
   `origin/<branch>` even before the branch is merged.
```

### 6.3 `disclosure-sop.md` — add Medium edge case

**Where**: `docs/disclosure-sop.md`, §2 "Decision tree" → "Edge cases" subsection.

**Content** (proposed addition):

```markdown
- **Medium severity where the disclosure IS the patch**: some Medium-bucket
  findings (TEST-003 untested mutation, ERR-002 mixed `raise` vs envelope,
  certain SHAPE-* drifts) are best resolved by an upstream PR that the
  maintainer can review on its own — there is nothing to disclose privately
  beyond the diff itself, and the 90-day window adds friction without
  protecting users. In these cases, route as Low (public PR with the fix)
  and record the routing decision in the case-study finding's "Why this
  bucket" line: `OVERRIDE: de-escalated to Low — disclosure IS the patch`.
  This is distinct from a generic Medium → Low de-escalation; the
  patch-as-disclosure rationale should be explicit.
```

### 6.4 `_TEMPLATE.md` — add Windows-CI-only note for npm workspaces targets

**Where**: `docs/case-studies/_TEMPLATE.md`, Appendix B "Methodology drift" section.

**Content** (proposed addition):

```markdown
- **Local test execution blocked**: if the target is an npm workspaces
  project and you're auditing on Windows without Developer Mode, document
  that local install/test was blocked by symlink permissions and that
  upstream CI was relied on for validation. This is not a methodology
  failure; it's a known Windows-tooling constraint. Reproducing on macOS or
  Linux removes this entirely.
```

### 6.5 `SKILL.md` — define a "lite scan" variant for `<10-tool` surfaces

**Where**: `skills/mcp-audit/SKILL.md`, "When to invoke" → "Don't trigger when" subsection.

**Background**: the current `SKILL.md` says "Don't trigger when: Server has <10 tools — too small for the rubric to add value over reading the source." Wave-2 evidence (C's `mcp-server-fetch` audit, 1-tool surface) confirms this is the right default for the **5-axis** scan: 3 of 5 axes (return-shape, naming, decay) are trivially satisfied with 1 tool. But C's audit also surfaced a security-relevant finding (SSRF posture, missing allowlist) through git-history analysis at the inventory step — work that happened **outside** the 5-axis scoring loop.

**Content** (proposed):

```markdown
For `<10-tool` surfaces, run a **"lite scan" variant** instead of skipping
entirely:

1. Inventory + git-history scan (especially: any feature branches that
   added security/test/docs but never merged? `git branch -a --contains
   <commit>` to verify merge status; `git log -S "<symbol>"` to confirm
   add/remove claims).
2. Security axis only (SEC-001 through SEC-009 from `SEVERITY.md`) —
   discoverability and decay axes are noise at this scale.
3. Test coverage axis (TEST-001 through TEST-004) — small surfaces still
   benefit from MCP-layer integration tests.
4. Skip discoverability + return-shape + naming scoring.

The lite scan still produces a case-study using the same `_TEMPLATE.md`,
just with a shorter §3 (Findings) and a note in §2 (Methodology) that the
lite variant was applied.

Threshold: 1-9 tools = lite scan. 10+ tools = full 5-axis scan.
```

**Attribution**: surfaced by C's `mcp-server-fetch` audit (wave 2). The 1-tool surface validated both that the threshold is right for the full scan AND that a security-only variant catches what the full scan would have skipped.

**Cross-reference**: this proposal is independent of §6.1–§6.4. Can land in any order. It's the highest-leverage of the five proposals because the next external audit may target a small surface, and "skip entirely" loses real findings.

### 6.6 Attribution discipline — pickaxe-required for "silently removed" claims

**Where**: `skills/mcp-audit/SKILL.md`, "Honest scoring discipline" section, fourth rule (after the existing three).

**Background**: wave 2's C audit produced a false-positive `silently removed` claim — narrative attribution chained two unrelated commits (one feature-branch add, one main null-fix). The disclosure SOP's GHSA gate caught it (C correctly STOPPED before public filing), but the claim made it as far as the case-study draft and WRG evidence record.

**Content** (proposed):

```markdown
4. **Verify "silently removed" / "regression in commit X" claims with pickaxe**.
   Any audit narrative that says "the security feature was added in commit A and
   removed/disabled in commit B" must be backed by:
   - `git log -S "<symbol>" -- <path>` showing the symbol added in A
     and removed (or modified) in B. If the symbol appears in **only**
     A's commit and never in B's diff, the "silently removed" claim is
     false — A was likely on an unmerged feature branch.
   - `git branch -a --contains <commit>` to verify the commit's merge
     status. A commit reachable only from a `claude/issue-*` or other
     ad-hoc feature branch was never on `main` to be removed from.
   - Math sanity check: if commit A was `+143/-3` and commit B is
     `+12/-10`, B did not "remove the security feature" — it modified
     ~22 lines of unrelated code.

   This rule prevents false-positive escalations from chained-narrative
   misreads and protects the disclosure SOP's GHSA gate from churn.
```

**Attribution**: surfaced by C's `mcp-server-fetch` audit (wave 2). The disclosure SOP gate worked exactly as designed — the claim was caught at A's pre-disclosure review. Codifying the verification step into the skill prevents the same shape of error in future audits.

### 6.7 No skill-source PRs from A this wave

`SKILL.md` and `SEVERITY.md` are currently being modified by B's #8 (TS-adaptation subsection + SHAPE-005 row). To avoid file-conflict with B's open PR, A's retro lands as a standalone document under `docs/retrospectives/` and the actions above are filed as **proposals**, not source edits. Once #8 merges, any of §6.1–§6.4 can be opened as one or more follow-up PRs. The order doesn't matter — these are independent.

## 7. The bottom line

The skill works. The infrastructure (template + SOP + SEVERITY) works. The 3-agent topology works. The shared-fork pattern works. The override convention works. The dual-output flow works. The non-repo staging path works.

The lessons in §3 are real but small — none of them blocked the wave, and all four have proposed fixes in §6. The next external audit (B's git + C's fetch, in flight as of this retro) is the validation of all of the above in a different ecosystem.

If wave 2 ships at the same shape (≤24h, ≥6 PRs, 0 scope violations), the framework graduates from "first time worked" to "the way we do this now."
