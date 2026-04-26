---
target_repo: <owner/repo>
target_commit: <sha-or-tag>
target_package: <pypi-or-npm-name@version>     # if applicable
audit_date: <YYYY-MM-DD>
auditor: <name or handle>
skill_version: skills/mcp-audit @ <commit-or-date>
severity_rubric: skills/mcp-audit/SEVERITY.md @ <commit-or-date>
mcp_servers_audited:
  - <server-name-or-path>
severity_summary:
  critical: 0
  high: 0
  medium: 0
  low: 0
  info: 0
disclosure_status: draft       # draft | private | coordinated | public
---

# `<target_repo>` MCP audit — `<YYYY-MM-DD>`

> One-paragraph TL;DR. State (a) what was audited, (b) what was found at the
> highest severity level, and (c) what the maintainer is asked to do next.
> Example: "Audited `<repo>` MCP surface (N tools across M files). One **High**
> finding (unauthenticated mutation tool); 3 **Low** (return-shape drift); 8
> **Info** (docstring tautology). High already disclosed via GHSA on YYYY-MM-DD;
> Low/Info batched into a public PR."

---

## 1. Scope

**In scope**
- Server(s): `<path/to/server.py>` — N tools (`@mcp.tool()` decorators)
- Commit / version audited: `<sha>` (tag `<vX.Y.Z>` if tagged)
- Adjacent surfaces examined for context: `<README.md, docs/, CHANGELOG.md>`

**Out of scope**
- Performance benchmarks
- Code-quality lint (ruff, mypy)
- Static security scans already covered by upstream CI (gitleaks, bandit)
- Behavioural correctness of individual tool implementations beyond the
  audit's five axes

**Constraints**
- Read-only audit. No code executed against live infrastructure.
- No mutation tools invoked. No credentials used.
- All findings derived from source inspection + grep + docstring review.

---

## 2. Methodology

The audit applies the [`mcp-audit` skill](../../skills/mcp-audit/SKILL.md):
five axes scored per tool (discoverability, return-shape, naming, error
handling, test coverage), plus decay-candidate detection across four signals
(CHANGELOG / README / consumer-import / test).

Severity bucketing uses the default rubric in
[`skills/mcp-audit/SEVERITY.md`](../../skills/mcp-audit/SEVERITY.md). Any
deviation from the default is called out in the relevant finding.

Disclosure handling follows [`docs/disclosure-sop.md`](../disclosure-sop.md).

**Honest-scoring discipline**: scores are not graded on a curve. A surface
with no problems is reported as "no findings" — it is not padded with
manufactured Info-level items.

---

## 3. Findings

All findings are listed in the matrix below. Detail blocks for each finding
follow, grouped by severity (Critical → Info).

### 3.0 Findings matrix

| finding_id | section | severity | status | upstream_link |
|---|---|---|---|---|
| F-001 | <e.g. SEC-006 unauthenticated mutation> | High | reported | <GHSA URL or `private`> |
| F-002 | <e.g. SHAPE-001 mixed envelope> | Low | reported | <issue/PR URL> |
| F-003 | <e.g. DISC-001 tautological docstring> | Info | reported | <issue/PR URL> |
| ... | ... | ... | ... | ... |

`status` values: `draft` | `reported` | `acknowledged` | `patched` | `declined` | `wontfix`

### 3.1 Critical

> Findings warranting immediate private disclosure. See SOP.

#### F-XXX — `<short title>`
- **Where**: `<path/to/file.py:LINE>` (function `<tool_name>`)
- **What**: <observation in one or two sentences>
- **Why severe**: <which SEVERITY.md row applies + reasoning>
- **Reproduction**: <minimal steps; redact if private disclosure>
- **Suggested fix**: <one-paragraph remediation>
- **Disclosure**: GHSA `<id-or-pending>` filed `<YYYY-MM-DD>`

### 3.2 High

#### F-XXX — `<short title>`
- **Where**: `...`
- **What**: ...
- **Why severe**: ...
- **Reproduction**: ...
- **Suggested fix**: ...
- **Disclosure**: ...

### 3.3 Medium

#### F-XXX — `<short title>`
- **Where**: `...`
- **What**: ...
- **Why this bucket**: ...
- **Suggested fix**: ...

### 3.4 Low

#### F-XXX — `<short title>`
- **Where**: `...`
- **What**: ...
- **Suggested fix**: ...

### 3.5 Info

> Discoverability / consistency / decay observations. Batched into a single
> upstream PR or issue where possible.

#### F-XXX — `<short title>`
- **Where**: `...`
- **What**: ...
- **Suggested fix**: ...

---

## 4. Disclosure timeline

| date | actor | event |
|---|---|---|
| `<YYYY-MM-DD>` | auditor | Audit completed against commit `<sha>` |
| `<YYYY-MM-DD>` | auditor | Critical/High findings disclosed privately via GHSA `<id>` |
| `<YYYY-MM-DD>` | maintainer | Acknowledgement received |
| `<YYYY-MM-DD>` | maintainer | Patch released as `<vX.Y.Z>` |
| `<YYYY-MM-DD>` | auditor | Public disclosure (this document) published |
| `<YYYY-MM-DD>` | auditor | Low/Info batched PR opened: `<URL>` |

If any deadline lapses without response, document the missed checkpoint here
and link the SOP escalation step that triggered.

---

## 5. Upstream response

**Acknowledgement**: <yes/no, channel, date>

**Patches landed**
- F-XXX → <commit/PR URL>, released in `<vX.Y.Z>` on `<YYYY-MM-DD>`
- F-YYY → ...

**Patches declined / wontfix**
- F-ZZZ → maintainer rationale: "<paraphrase or quote>" (link)

**Outstanding** (open as of this document's `audit_date`)
- F-AAA → status, last contact `<YYYY-MM-DD>`, next checkpoint `<YYYY-MM-DD>`

---

## 6. Reusable patterns

Findings that generalise beyond this single repo and should feed back into
the audit infrastructure:

- **Pattern**: <name>
  - **Observed in**: F-XXX
  - **Generalises because**: <why it'll likely show up in the next audit too>
  - **Proposed action**: add row to [`SEVERITY.md`](../../skills/mcp-audit/SEVERITY.md) / extend [`SKILL.md`](../../skills/mcp-audit/SKILL.md) check / new heuristic in `references/audit_template.md`
  - **Tracked as**: <issue/PR URL in this repo>

If no new patterns surfaced, state that explicitly: "No new reusable patterns;
all findings fit existing SEVERITY rows."

---

## Appendix A — tool inventory snapshot

Optional. Include the raw inventory table from §1 of the standard audit
template if it adds context the maintainer will want to verify against.

## Appendix B — methodology drift

Optional. Note any deviation from the standard skill procedure (e.g.,
"server uses a custom `@register_tool` decorator instead of `@mcp.tool()`;
inventory grep adapted accordingly").

Common drift categories worth recording when applicable:

- **Decorator / framework substitution** — server uses a custom decorator,
  the low-level Python SDK (`@server.list_tools()` + `@server.call_tool()`),
  or the TS SDK (`server.registerTool()`) instead of canonical FastMCP
  `@mcp.tool()`. Note the substitution + the canonical envelope shape for
  the substituted ecosystem (TS: `{content, structuredContent}`; low-level
  Python: `[TextContent(...)]`; FastMCP: `{ok, ...}`).
- **Local test execution blocked** — if the target is an npm workspaces
  project and the audit ran on Windows without Developer Mode, document
  that local install/test was blocked by symlink permissions and that
  upstream CI was relied on for validation. This is not a methodology
  failure; it is a known Windows-tooling constraint. Reproducing on macOS
  or Linux removes this entirely. First documented in the
  `@modelcontextprotocol/server-filesystem` audit (2026-04-26).
- **Lite-scan variant applied** — if the target has fewer than 10 tools
  and the auditor ran the lite-scan variant (security axis + test-coverage
  axis only; discoverability + return-shape + naming skipped as
  trivial-pass at small scale), note this here and link the SKILL.md
  section that defines the lite scan.
- **Pickaxe verification used for "removed" claims** — if the audit's
  inventory step surfaced a "feature added then removed" narrative across
  commits, note that pickaxe (`git log -S "<symbol>"`) and branch-membership
  (`git branch -a --contains <commit>`) checks were used to verify the
  claim, and record the result. False-positive `silently removed` claims
  have happened (mcp-server-fetch audit, 2026-04-26) when an unmerged
  feature branch was diffed against a mainline commit; the verification
  is now mandatory per `SKILL.md` honest-scoring rule 4.
