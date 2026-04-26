---
name: mcp-audit
description: Audit a FastMCP server for tool discoverability, return-shape consistency, test coverage, and decay candidates. Produces a structured evidence-only report with a "this-week pick" of named ≤1hr fixes plus a deferred next-session backlog. Use this skill when the user asks to "audit my MCP server", "score my MCP tools", "check tool discoverability", "MCP tool inventory", "are my MCP descriptions any good", or invokes `/mcp-audit`. Also use proactively when reviewing a FastMCP project that has grown past ~10 tools and the maintainer is unsure which deserve attention. Output is a Markdown report (single file under `docs/audit/` or `docs/decisions/`) with 6 sections: inventory, discoverability scoring (1-5 per tool), consistency audit (return shape + naming + error handling), decay candidates, top 5 priorities, decision gate. Read-only — proposes fixes, does not apply them. Battle-tested across two MCP servers (yakuphanycl/WinstonRedGuard PR #295, yakuphanycl/instinct PR #26).
---

# mcp-audit

Apply a repeatable audit to a [FastMCP](https://github.com/jlowin/fastmcp)
server (or any MCP server with `@mcp.tool()` decorators) and produce a
single-file evidence report that the maintainer can act on inside a 1-hour
session.

## What this skill does

Scores every registered MCP tool on five axes, surfaces inconsistencies
across the surface, and ranks fixes by leverage. The audit is **read-only**:
it produces a Markdown report, not code changes. Fix-application happens in
follow-up PRs, optionally reusing the same maintainer.

The five axes (per tool):

1. **Discoverability (1-5)** — would a fresh agent call this tool from its
   description alone? 5 = trigger phrases + when-to-use + return shape; 1 =
   docstring just restates the function name.
2. **Return-shape consistency** — does the tool return a uniform `{ok, ...}`
   envelope, or its own idiom? Count idiom families across the surface.
3. **Naming consistency** — snake_case? prefixed by domain (e.g.,
   `memory_*`, `pipeline_*`)? consistent action verbs?
4. **Test coverage** — dedicated unit test? smoke-only? none? At which layer
   (CLI / store / server / MCP wrapper)?
5. **Decay signal** — is the tool documented in CHANGELOG, exercised in
   examples, imported by any consumer, mentioned in README? Tools that fail
   all four are decay candidates.

## When to invoke

Strongly trigger on:

- User asks "audit my MCP server", "score my MCP tools"
- User asks "are my tool descriptions any good", "is anyone using this tool"
- User says "my MCP server has grown, where should I focus"
- Explicit invocation: `/mcp-audit`
- A FastMCP project with 10+ tools where the maintainer hasn't done a
  systematic review

Don't trigger when:

- Server has <10 tools — too small for the rubric to add value over
  reading the source
- User wants behavioural testing of tools — that's `pytest` territory, not
  this audit
- User wants performance benchmarks — out of scope; this is a static review
- Project doesn't use FastMCP / `@mcp.tool()` shape — adapt manually,
  don't force-fit

## How to run

The skill produces a single Markdown file. The doing-it-yourself version:

0. **Target health check** — before scoping the audit:
   - Confirm the target package is on the active reference list (not in
     `*-archived` repos, not deprecated by the maintainer).
   - Note the latest published version and the commit SHA being audited.
   - If the target was moved/archived, surface this immediately and ask
     the maintainer (or yourself, if self-directing) whether to (a) audit
     the archived version anyway (low disclosure value but skill-validation
     value), or (b) pivot to an active sibling.

   First applied: planned target was `modelcontextprotocol/servers/src/github`,
   discovered moved to `modelcontextprotocol/servers-archived` at step 0,
   pivoted to `src/filesystem` (active, comparable blast radius). Pivot
   took <5 minutes; without step 0 the discovery would have surfaced
   mid-audit and wasted scoring work.

1. **Inventory** — grep for `@mcp.tool()` (or equivalent decorator) across
   `src/`. List every match: tool name, module path, line number.

   ```bash
   grep -rn "@mcp.tool\(\)" src/ | wc -l   # total count
   grep -rn "@mcp.tool\(\)" src/ -A 2      # peek at each
   ```

   For TypeScript surfaces, see "TypeScript adaptation" section below
   (substitute `server\.registerTool\(` for `@mcp.tool()`).

   For Python low-level SDK surfaces (`@server.list_tools()` +
   `@server.call_tool()` instead of FastMCP `@mcp.tool()`), grep for
   the dispatch handler and extract tool names from the returned list.

1.5. **Novelty verification (prerequisite for any "novel finding" claim)** —
     before recording a finding as not-previously-discussed by the
     maintainer, run **at least three** of the following queries:

     ```bash
     gh issue list --repo <upstream> --state all --search "<keyword>"
     gh pr list    --repo <upstream> --state all --search "<keyword>"
     gh search code --repo <upstream> "<symbol>"
     git log -S "<symbol>" -- <path>           # pickaxe
     git log --all --grep="<keyword>"
     ```

     Document the queries run + result counts in the case-study §7
     disclosure timeline. If a relevant existing issue/PR is found, the
     finding routes via the SOP "maintainer-tracked, documented limitation"
     edge case (de-escalate to Low + comment on existing issue), not as
     a novel finding. If all queries return 0 relevant results, the
     "novel" claim is verified and the finding routes per its severity
     bucket.

     First applied proactively: `mcp-server-memory` audit (2026-04-26),
     5 queries (race / atomic / lock / concurrent / mutex) all returned
     0 results before claiming F-002 (non-atomic write) was novel.

2. **Discoverability scoring** — for each tool, read its docstring + args.
   Score 1-5 against the rubric. Justify scores below 5 with one sentence.

3. **Consistency audit** — across all tools:
   - Return shape: count `{ok, ...}`, raw dict, raw list, raise-on-error,
     error-by-key-presence patterns. Report distribution.
   - Naming: any tools with inconsistent verbs (`get_x` vs `fetch_y`),
     missing domain prefix?
   - Error handling: raise vs structured envelope vs silent? Per tool.

4. **Decay candidate detection** — for each tool, check four signals:
   - Mentioned in CHANGELOG.md?
   - Mentioned in README.md or docs/?
   - Imported by any consumer in this repo (grep)?
   - Exercised in any test?

   Tools failing **all four** are decay candidates. Rank by how recently
   they last appeared in any signal.

5. **State handling (stateful surfaces only)** — applies when the server
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
   `SEVERITY.md`.

   First applied: `mcp-server-memory` audit (2026-04-26) — surfaced F-002
   (non-atomic `saveGraph` + missing in-process serialiser) which scored
   trivially-OK on all five other axes.

6. **Top 5 priorities** — ranked, name-specific, with effort estimate.
   Each priority must be ≤1hr to fix. Bigger fixes are next-session
   backlog.

7. **Decision gate** — at the bottom of the report:
   - Total tools, average discoverability, % consistency
   - **This-week pick**: 1-2 fixes (≤1hr each), name specific tools
   - **Next-session backlog**: 3-5 deeper items
   - **Decay candidate fates**: KEEP / SOFT-DEPRECATE / REMOVE per tool

See `references/audit_template.md` for the full Markdown template, with
section headers and example rows already filled in for adaptation.

## Lite-scan variant for `<10`-tool surfaces

For surfaces with fewer than 10 tools, run a **lite scan** instead of
skipping the audit entirely. The full 5-axis scan adds noise at small
scale (3 of 5 axes are trivially satisfied with 1-2 tools), but security
posture and test coverage gaps still warrant attention.

**Lite scan procedure**:

1. Step 0 (target health check) — same as full scan.
2. Step 1 (inventory) — same as full scan.
3. Step 1.5 (novelty verification) — same as full scan.
4. **Skip steps 2 (discoverability scoring), 3 (consistency audit),
   4 (decay candidate detection)** — these axes are trivially-pass at
   small scale and produce no actionable findings.
5. **Run security axis only** (`SEC-001` through `SEC-009` from
   `SEVERITY.md`).
6. **Run test coverage axis** — small surfaces still benefit from
   MCP-layer integration tests.
7. Step 5 (state handling) — only if the surface is stateful.
8. Steps 6 (top 5 priorities) and 7 (decision gate) — adjusted to "top
   1-3 priorities" given the smaller finding pool.

The lite scan produces a case-study using the same `_TEMPLATE.md`, just
with a shorter §3 (Findings) and a note in §2 (Methodology) that the
lite variant was applied.

**Threshold**: 1-9 tools = lite scan. 10+ tools = full 5-axis scan.

**First applied**: `mcp-server-time` audit (2026-04-26, 2 tools) — full
scan would have added 3 trivially-passing sections; lite scan saved 60%
of analysis time with zero loss of actionable findings (see case-study
§6 dogfood validation feedback). Confirmed signal: `SEC N/A ratio >50%`
identifies pure-computation servers (no network / no filesystem / no
database = no attack surface) where the lite scan completes faster.

## Output location

Write the report to one of:

- `docs/decisions/MCP_TOOL_AUDIT_<YYYY-MM-DD>.md` — for monorepos using a
  decisions/ADR layout
- `docs/audit/MCP_AUDIT_<YYYY-MM-DD>.md` — for repos with a dedicated audit
  folder

Both have been used in practice; either is fine. Be consistent with the
rest of the repo's docs structure.

## TypeScript adaptation

The skill was developed against Python FastMCP (`@mcp.tool()`). When auditing
a TypeScript MCP server (e.g., `modelcontextprotocol/servers/src/*`), apply
the following substitutions:

- **Inventory grep**: `server\.registerTool\(` instead of `@mcp.tool()`.
  Tool names are the first string arg to `registerTool`, not the function
  name.
- **Inputs / outputs**: Zod schemas (`inputSchema: { ... }`,
  `outputSchema: { ... }`), not Python annotations. Read the schema
  definition, not just the function signature.
- **Canonical envelope**: TS SDK convention is
  `{content: [{type, text}], structuredContent: {...}}` — different from
  FastMCP's `{ok, ...}` Python idiom. The five-axis rubric still applies;
  the canonical shape per ecosystem differs. Don't force-fit `{ok}` onto
  a TS surface.
- **Error handling axis**: TS surface uses `throw` + SDK error channel,
  not in-band `{ok: false}` envelope. Consistent within surface; flagging
  as deviation force-fits Python idiom.
- **MCP-layer test recognition**: integration tests use
  `@modelcontextprotocol/sdk/client` + `StdioClientTransport` to round-trip
  through the SDK serializer. This is a higher-fidelity coverage signal
  than Python's typical "did you call the function" tests. Grep for
  `@modelcontextprotocol/sdk/client` to identify MCP-layer coverage.
- **Type-system bypass as inconsistency marker**: grep
  `as unknown as CallToolResult` and `as any` inside `registerTool` handler
  bodies — these are the type system's own complaints, captured in source.
  Map to `SHAPE-005`.

First applied: `modelcontextprotocol/servers@HEAD` filesystem audit
([case-study](../../docs/case-studies/filesystem-mcp-2026-04-26.md)).

## Workflow for Claude when this skill triggers

1. Confirm the project uses `@mcp.tool()` (or compatible decorator).
   If not, abort and explain.
2. Run the inventory grep. Total count + first-pass list.
3. Open `references/audit_template.md` and adapt section by section.
4. For discoverability scoring, use Claude's own judgment of what would
   trigger a tool call — **honest scoring**: if half the tools are 1/5,
   say so. Don't grade-inflate to make the project look healthier.
5. For decay candidates, run the four-signal check mechanically. Don't
   skip a signal because "I'm pretty sure it's used".
6. Top 5 priorities must name SPECIFIC tools with SPECIFIC fix shapes.
   "Improve descriptions" is not a priority; "rewrite `tool_x` docstring
   to add when-to-use + return shape" is.
7. The "this-week pick" must be SHIPPABLE. 1-2 named fixes that the
   maintainer can do in a single PR within an hour.
8. Open the report as a draft PR with the file as the only deliverable.
   Use the maintainer's evidence-brief format if known.
9. **Cross-agent coordination** — if multiple Claude agents are running
   parallel branches in the same repo (case-study refile by one agent,
   skill-extension by another, etc.), use `git show <ref>:<path>` to
   read another agent's in-flight content rather than `git checkout
   <ref>`. Checkout in a shared repo can stomp the other agent's
   worktree branch pointer; `git show` is read-only and safe. The
   `<ref>` can be `origin/<branch>` even before the branch is merged.

## Honest scoring discipline

The audit is most useful when the maintainer **trusts the numbers**.
Four discipline rules:

1. **Don't deflate to manufacture problems.** If the surface is genuinely
   well-described (4.91/5 happens — see instinct's PR #26), say so.
   "No discoverability problem" is a finding too.

2. **Don't grade-inflate to be polite.** If a tool returns raw JSON and
   raises bare `RuntimeError`, that's 1/5 even if the maintainer wrote
   the docstring with care.

3. **Decision gate must point to specific tools.** Not "consider improving
   X". Tools have names; use them. The maintainer should be able to
   `grep` the exact strings the audit names.

4. **Verify "silently removed" / "regression in commit X" claims with
   pickaxe.** Any audit narrative that says "the security feature was
   added in commit A and removed/disabled in commit B" must be backed by:
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

   First applied: caught a false-positive `silently removed` claim
   in `mcp-server-fetch` audit (2026-04-26) at A's pre-disclosure review,
   before public filing. The disclosure SOP gate worked exactly as
   designed; this rule codifies the verification step into the skill so
   the same shape of error is caught at audit time.

## Examples in the wild

Two real audits using this skill (or its precursor):

- [`yakuphanycl/WinstonRedGuard#295`](https://github.com/yakuphanycl/WinstonRedGuard/pull/295) — wrg_mcp_server audit (32 tools, avg 2.81/5, 88% return-shape consistency, 4 decay candidates flagged for soft-deprecate)
- [`yakuphanycl/instinct#26`](https://github.com/yakuphanycl/instinct/pull/26) — instinct audit (22 tools + 2 prompts, avg 4.91/5, 0/22 `ok` envelope, 0/22 MCP-layer test coverage, NONE decay)

Both audits produced ≤1hr "this-week pick" PRs that landed within hours.
First audit's quick wins: [WRG#296](https://github.com/yakuphanycl/WinstonRedGuard/pull/296). Second audit's quick wins: [instinct#27](https://github.com/yakuphanycl/instinct/pull/27).

## What this skill is NOT

- Not a code-quality linter — `ruff` / `mypy` already do that
- Not a security scanner — `gitleaks` / `bandit` cover that
- Not a performance profile — different tooling
- Not an LLM-judgment review of "is this tool useful" — frequency / coverage / consistency are the measurable axes; usefulness is a maintainer call
- Not a fix-applier — pure read-and-report; the maintainer ships the fixes
