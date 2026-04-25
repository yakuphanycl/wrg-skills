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

1. **Inventory** — grep for `@mcp.tool()` (or equivalent decorator) across
   `src/`. List every match: tool name, module path, line number.

   ```bash
   grep -rn "@mcp.tool\(\)" src/ | wc -l   # total count
   grep -rn "@mcp.tool\(\)" src/ -A 2      # peek at each
   ```

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

5. **Top 5 priorities** — ranked, name-specific, with effort estimate.
   Each priority must be ≤1hr to fix. Bigger fixes are next-session
   backlog.

6. **Decision gate** — at the bottom of the report:
   - Total tools, average discoverability, % consistency
   - **This-week pick**: 1-2 fixes (≤1hr each), name specific tools
   - **Next-session backlog**: 3-5 deeper items
   - **Decay candidate fates**: KEEP / SOFT-DEPRECATE / REMOVE per tool

See `references/audit_template.md` for the full Markdown template, with
section headers and example rows already filled in for adaptation.

## Output location

Write the report to one of:

- `docs/decisions/MCP_TOOL_AUDIT_<YYYY-MM-DD>.md` — for monorepos using a
  decisions/ADR layout
- `docs/audit/MCP_AUDIT_<YYYY-MM-DD>.md` — for repos with a dedicated audit
  folder

Both have been used in practice; either is fine. Be consistent with the
rest of the repo's docs structure.

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

## Honest scoring discipline

The audit is most useful when the maintainer **trusts the numbers**.
Three discipline rules:

1. **Don't deflate to manufacture problems.** If the surface is genuinely
   well-described (4.91/5 happens — see instinct's PR #26), say so.
   "No discoverability problem" is a finding too.

2. **Don't grade-inflate to be polite.** If a tool returns raw JSON and
   raises bare `RuntimeError`, that's 1/5 even if the maintainer wrote
   the docstring with care.

3. **Decision gate must point to specific tools.** Not "consider improving
   X". Tools have names; use them. The maintainer should be able to
   `grep` the exact strings the audit names.

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
