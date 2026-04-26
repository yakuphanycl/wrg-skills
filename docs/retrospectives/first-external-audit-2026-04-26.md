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

### 6.7 `SKILL.md` — add 6th axis: stateful surface adaptation

**Where**: `skills/mcp-audit/SKILL.md`, "What this skill does" section, after the existing 5 axes.

**Background**: wave 3's B audit of `@modelcontextprotocol/server-memory` (file-backed JSONL storage) was the skill's first audit against a **stateful** surface. The existing 5 axes (discoverability, return-shape, naming, test coverage, decay) all pass cleanly without inspecting the state-handling layer. B's audit surfaced finding F-002 (saveGraph non-atomic + missing in-process serialiser) — which scores trivially-OK on all 5 axes but is genuinely a coverage gap. The proposed 6th axis fills this.

**Content** (proposed):

```markdown
6. **State handling (stateful surfaces only)** — applies when the server
   maintains state across tool calls (file-backed store, SQLite, in-memory
   dict, external service connection):
   - **Atomicity**: do mutating writes use atomic primitives (write-temp +
     `fs.rename`, transactions) or naked `write` calls that can leave
     half-written state on crash?
   - **Concurrency**: is there an in-process serialiser (mutex, async-lock)
     for `load → mutate → save` patterns? Two concurrent calls to a
     mutation tool — does one win cleanly or do they interleave?
   - **Persistence verification**: do tests verify state survives a process
     restart, or only that mutations are visible within the same fixture?
   - **State leakage**: can tool A's mutations be observed by tool B in
     ways the surface doesn't document? Especially relevant for
     multi-tenant or multi-context deployments.

   For pure-functional surfaces (no state — `time`, `fetch`, etc.) skip
   this axis entirely. For stateful surfaces, the four sub-checks above
   are the discovery questions; map findings to `STATE-*` rows in
   `SEVERITY.md` (see §6.8).
```

**Attribution**: surfaced by B's `mcp-server-memory` audit (wave 3, [yakuphanycl/wrg-skills#15](https://github.com/yakuphanycl/wrg-skills/pull/15)). The audit was the first to formally exercise this dimension; B's case-study §6 documents the four sub-checks as candidate skill additions.

### 6.8 `SEVERITY.md` — add 4 new `STATE-*` rows

**Where**: `skills/mcp-audit/SEVERITY.md`, matrix block, after the existing 32 rows (numbered 33–36, contiguous within the new `STATE-*` prefix).

**Background**: §6.7's 6th axis produces findings that don't map cleanly to existing rows. B's F-002 (non-atomic write) was forced into `SHAPE-004` (silent empty return) by analogy — close but not exact. Native rows give the audit honest, attributable severity assignments.

**Content** (proposed, four rows):

```markdown
| 33 | `STATE-001` | State handling | Mutating tool writes state without atomic primitives (no write-temp + rename, no transaction) | Medium | Crash mid-write leaves half-written state on disk; torn reads possible | `saveGraph` in `mcp-server-memory@0.6.x` writes JSONL via direct `fs.writeFile`, not `fs.rename`-from-temp |
| 34 | `STATE-002` | State handling | Missing in-process serialiser for `load → mutate → save` pattern across concurrent tool calls | Medium | Two parallel mutation calls can interleave; second's load races first's save = lost write | Two concurrent `create_entities` calls on `mcp-server-memory` can lose one write under load |
| 35 | `STATE-003` | State handling | State persistence not exercised by tests (mutations visible in fixture, but no restart verification) | Low | Refactor to a different storage backend may silently break persistence; failure surfaces only in production | All `mcp-server-memory` tests are within-fixture; no test re-instantiates the server and checks state |
| 36 | `STATE-004` | State handling | Tool A's mutations observable by tool B in ways the surface doesn't document (state leakage) | Medium | Multi-tenant deployments leak data across contexts; not directly exploitable but trust-degrading | Hypothetical; not yet observed in audited surfaces — placeholder for future findings |
```

**Override conventions**: `STATE-001` and `STATE-002` may de-escalate to Low under the §6.3 "Medium-as-patch" edge case (`disclosure-sop.md`) when the fix is a small public PR (e.g., B's #4049 atomic-write fix landed as Low routing). `STATE-004` is Medium by default but escalates to High if the leakage crosses authentication boundaries.

**Attribution**: surfaced by B's `mcp-server-memory` audit (wave 3). The four rows codify B's case-study §6 reusable-pattern proposals.

### 6.9 `SKILL.md` — add pickaxe-as-prerequisite for novel findings

**Where**: `skills/mcp-audit/SKILL.md`, "How to run" section, between current step 1 (Inventory) and step 2 (Discoverability scoring).

**Background**: §6.6 codifies pickaxe verification for "silently removed" claims (reactive, post-claim). §6.9 codifies pickaxe verification as a **prerequisite** for any finding that the audit calls "novel" or "not previously discussed by the maintainer" (proactive, pre-claim). B's wave-3 memory audit applied this proactively before claiming F-002 was novel: 5 `gh search` queries (race / atomic / lock / concurrent / mutex) all returned 0 results, documented in case-study §7 disclosure timeline. This turned the "novel" claim from an assertion into a verified observation.

**Content** (proposed):

```markdown
1.5. **Novelty verification (prerequisite for any "novel finding" claim)** —
     before recording a finding as not-previously-discussed by the
     maintainer, run **at least three** of the following queries:
     - `gh issue list --repo <upstream> --state all --search "<keyword>"`
       for the finding's primary keyword(s).
     - `gh pr list --repo <upstream> --state all --search "<keyword>"`
       same keywords across PRs.
     - `gh search code --repo <upstream> "<symbol>"` for a function or
       symbol the finding names.
     - `git log -S "<symbol>" -- <path>` (pickaxe) for symbol add/remove
       history in source.
     - `git log --all --grep="<keyword>"` for commit-message matches.

     Document the queries run + result counts in the case-study §7
     disclosure timeline. If a relevant existing issue/PR is found, the
     finding routes via the §2 SOP "maintainer-tracked, documented
     limitation" edge case (de-escalate to Low + comment on existing
     issue), not as a novel finding. If all queries return 0 relevant
     results, the "novel" claim is verified and the finding routes per
     its severity bucket.
```

**Attribution**: surfaced proactively by B's `mcp-server-memory` audit (wave 3) — B applied this pattern without prior codification, then flagged it in case-study §6 as a SKILL.md candidate. Wave 2's C false-positive (`mcp-server-fetch` SSRF, ec20ee7 misattribution) was the negative-example precedent that motivated the proactive form. Together §6.6 (reactive) + §6.9 (proactive) close the attribution-discipline class.

### 6.10 Status update — A's queue cleared post-#8

[`#8` merged 2026-04-26](https://github.com/yakuphanycl/wrg-skills/pull/8) (TS-adaptation subsection + `SHAPE-005` row). A's queue (§6.1, §6.2, §6.5, §6.6, §6.7, §6.8, §6.9) is now unblocked — these can land as a single batched skill PR or 7 separate PRs. §6.3 + §6.4 (file-disjoint from #8) already shipped via [#13](https://github.com/yakuphanycl/wrg-skills/pull/13).

## 7. The bottom line

After three waves (1 day each, 22 PRs total, 5 audit case studies, 3 ecosystems, 0 scope violations):

The skill works. The infrastructure (template + SOP + SEVERITY) works. The 3-agent topology works. The shared-fork pattern works. The override convention works (3 distinct override types live-applied). The dual-output flow works. The non-repo staging path works. The disclosure-SOP GHSA gate works (caught a false-positive pre-disclosure). The lite-scan variant works (validated by C's `mcp-server-time` audit at 60% time saving with zero loss of actionable findings). The pickaxe discipline works (applied reactively in wave 2, proactively in wave 3 — B's 5-query proactive scan before claiming novelty).

Wave 2 graduated the framework from "first time worked" to "the way we do this now." Wave 3 graduated it again from "validated on TS + Python FastMCP" to "validated across 3 ecosystems with one stateful surface and one lite-scan."

The next decision — whether to keep auditing or to consolidate momentum into framework refinement and onboarding artifacts — is a strategic call for the maintainer (yakuphanycl), not a methodological gap in the skill.

## 8. Five-audit cross-link table (for quick navigation)

| # | Target | Date | Variant | Severity (C/H/M/L/I) | WRG evidence | wrg-skills case-study | Upstream PR(s) | Comment |
|---|---|---|---|---|---|---|---|---|
| 1 | `@modelcontextprotocol/server-filesystem@0.6.3` (TS) | 2026-04-26 | full | 0/0/0/6/2 | [#307](https://github.com/yakuphanycl/WinstonRedGuard/pull/307) | [#9](https://github.com/yakuphanycl/wrg-skills/pull/9) | [#4045](https://github.com/modelcontextprotocol/servers/pull/4045) + [#4046](https://github.com/modelcontextprotocol/servers/pull/4046) + [#4047](https://github.com/modelcontextprotocol/servers/pull/4047) | – |
| 2 | `@modelcontextprotocol/server-fetch@0.6.3` (FastMCP-Py) | 2026-04-26 | lite (false-positive rescued) | 0/0/0/2/2 | [#308](https://github.com/yakuphanycl/WinstonRedGuard/pull/308) | [#11](https://github.com/yakuphanycl/wrg-skills/pull/11) | – | [issue #2317](https://github.com/modelcontextprotocol/servers/issues/2317#issuecomment-4320872444) |
| 3 | `@modelcontextprotocol/server-git@2025.x` (low-level Py) | 2026-04-26 | full | 0/0/0/2/1 | [#309](https://github.com/yakuphanycl/WinstonRedGuard/pull/309) | [#12](https://github.com/yakuphanycl/wrg-skills/pull/12) | [#4048](https://github.com/modelcontextprotocol/servers/pull/4048) | – |
| 4 | `@modelcontextprotocol/server-memory@0.6.x` (TS) | 2026-04-26 | full + stateful axis | 0/0/0/2/1 | [#311](https://github.com/yakuphanycl/WinstonRedGuard/pull/311) | [#15](https://github.com/yakuphanycl/wrg-skills/pull/15) | [#4049](https://github.com/modelcontextprotocol/servers/pull/4049) | – |
| 5 | `@modelcontextprotocol/server-time@0.6.2` (FastMCP-Py) | 2026-04-26 | **lite** (§6.5 dogfood) | 0/0/0/1/0 | [#310](https://github.com/yakuphanycl/WinstonRedGuard/pull/310) | [#14](https://github.com/yakuphanycl/wrg-skills/pull/14) | – (test gap too narrow) | – |

**Aggregates across 5 audits**: 0 Critical / 0 High / 0 Medium / **13 Low / 6 Info** (after overrides). 4 upstream fix PRs filed. 1 issue-comment routing. 0 GHSAs filed (and 1 false-positive rescue confirms the gate works).
