---
target_repo: modelcontextprotocol/servers
target_commit: HEAD@2026-04-26
target_package: "@modelcontextprotocol/server-filesystem@0.6.3"
audit_date: 2026-04-26
auditor: yakuphanycl (automation, Agent A)
skill_version: skills/mcp-audit @ 2026-04-25
severity_rubric: skills/mcp-audit/SEVERITY.md @ 2026-04-26
mcp_servers_audited:
  - src/filesystem
severity_summary:
  critical: 0
  high: 0
  medium: 0
  low: 6
  info: 2
disclosure_status: public
---

# `modelcontextprotocol/servers` MCP audit — `2026-04-26`

> Audited `@modelcontextprotocol/server-filesystem@0.6.3` (14 tools, 1483 LOC TS in `src/filesystem/`). **Zero Critical / High / Medium findings.** Six **Low** (test-coverage extension across 12 tools + one return-shape envelope deviation) and two **Info** (one decay candidate + one missing-when-to-use). All findings batched into a single public upstream PR; no private disclosure required. Internal evidence record: [WRG#307](https://github.com/yakuphanycl/WinstonRedGuard/pull/307).

---

## 1. Scope

**In scope**
- Server: `src/filesystem/index.ts` — 14 tools registered via `server.registerTool()` (TypeScript MCP SDK 1.26 + Zod input/output schemas)
- Commit / version audited: `modelcontextprotocol/servers@HEAD` on 2026-04-26 (`@modelcontextprotocol/server-filesystem` published as `v0.6.3`)
- Adjacent surfaces examined for context: `README.md`, `lib.ts`, `path-utils.ts`, `path-validation.ts`, `roots-utils.ts`, `__tests__/` (7 test files)

**Out of scope**
- Performance benchmarks
- Code-quality lint (`eslint`, `tsc --strict` beyond what the project already runs)
- Static security scans (the project has its own CI for these)
- Behavioural correctness of individual tool implementations beyond the audit's five axes
- The other six reference servers (`everything`, `fetch`, `git`, `memory`, `sequentialthinking`, `time`) — single-target audit by design

**Constraints**
- Read-only audit. No code executed against a live filesystem.
- No mutation tools invoked. No credentials used.
- All findings derived from source inspection + grep + docstring review.

---

## 2. Methodology

The audit applies the [`mcp-audit` skill](../../skills/mcp-audit/SKILL.md): five axes scored per tool (discoverability, return-shape, naming, error handling, test coverage), plus decay-candidate detection across four signals (CHANGELOG / README / consumer-import / test).

Severity bucketing uses the default rubric in [`skills/mcp-audit/SEVERITY.md`](../../skills/mcp-audit/SEVERITY.md). Overrides are called out per finding under "Why this bucket".

Disclosure handling follows [`docs/disclosure-sop.md`](../disclosure-sop.md). All findings here resolve to **public PR / batched issue** under the SOP's Low/Info routing.

**Honest-scoring discipline**: the average discoverability of 4.50/5 is high. The maintainers wrote thoughtful descriptions; the gaps are narrow. No findings are manufactured to inflate the report.

**Framework adaptation**: this is the first run of the skill against a TypeScript MCP server. The skill was developed against Python FastMCP. Substitutions made:
- Tool inventory grep: `server\.registerTool\(` instead of `@mcp.tool()`. Inputs are Zod (`inputSchema: { ... }`), not Python annotations.
- Return-shape canonical form: TS SDK convention is `{content: [{type, text}], structuredContent: {...}}` — different from FastMCP's `{ok, ...}` Python idiom. The axis still applies; the canonical shape is just different per ecosystem.
- Error handling: TS surface uses `throw` + SDK error channel, not in-band `{ok: false}` envelope. Consistent within the surface; would be force-fitting to flag as deviation.
- MCP-layer test coverage: integration tests use `@modelcontextprotocol/sdk/client` + `StdioClientTransport`. Higher-fidelity coverage signal than Python's typical "did you call the function" tests, since round-trips through the SDK serializer (which is where #3110-class bugs live).

These adaptations are surfaced in §6 as a reusable pattern.

---

## 3. Findings

### 3.0 Findings matrix

| finding_id | section | severity | status | upstream_link |
|---|---|---|---|---|
| F-001 | TEST-001 — read tools (8) without MCP-layer test, batched | Low | reported | _pending public PR_ |
| F-002 | TEST-003 (de-escalated) — `write_file` no MCP-layer test | Low | reported | _pending_ |
| F-003 | TEST-003 (de-escalated) — `edit_file` no MCP-layer test | Low | reported | _pending_ |
| F-004 | TEST-003 (de-escalated) — `move_file` no MCP-layer test | Low | reported | _pending_ |
| F-005 | TEST-003 (de-escalated) — `create_directory` no MCP-layer test | Low | reported | _pending_ |
| F-006 | SHAPE-001 — `read_media_file` envelope deviates from 13/14 sibling tools | Low | reported | _pending_ |
| F-007 | DECAY-002 — `read_file` partial decay (deprecated, README-omitted, still registered) | Info | reported | _pending batched PR_ |
| F-008 | DISC-003 — `read_media_file` missing when-to-use guidance | Info | reported | _pending batched PR_ |

`status` values: `draft` | `reported` | `acknowledged` | `patched` | `declined` | `wontfix`

### 3.1 Critical

_No findings._

### 3.2 High

_No findings._

### 3.3 Medium

_No findings._ (Four TEST-003 mutation findings de-escalated to Low; rationale per finding below.)

### 3.4 Low

#### F-001 — `TEST-001` read tools (8) batched: no MCP-layer test
- **Where**: `src/filesystem/index.ts` lines 213, 225, 248, 300, 420, 626, 655, 683 — tools `read_file`, `read_text_file`, `read_media_file`, `read_multiple_files`, `list_directory`, `search_files`, `get_file_info`, `list_allowed_directories`
- **What**: Of 14 tools, only `directory_tree` and `list_directory_with_sizes` are exercised end-to-end via MCP client→server round-trip in `__tests__/structured-content.test.ts`. The other 12 tools have only lib-level unit tests (path validation, lib functions) — no integration coverage. This finding covers the 8 read-side tools; the 4 mutation tools are filed separately as F-002 through F-005.
- **Past regression context**: `__tests__/structured-content.test.ts:9-16` cites issues [#3110](https://github.com/modelcontextprotocol/servers/issues/3110), [#3106](https://github.com/modelcontextprotocol/servers/issues/3106), [#3093](https://github.com/modelcontextprotocol/servers/issues/3093) — production bugs from incorrect `structuredContent` shapes. The fix was integration tests; the fix's coverage stopped at 2 tools.
- **Suggested fix**: extend the existing `structured-content.test.ts` fixture to cover all 8 read tools. Same `beforeEach` setup, same MCP client, same shape assertions. Estimated +120 LOC, mechanical.

#### F-002 — `TEST-003` (de-escalated) `write_file` no MCP-layer test
- **Where**: `src/filesystem/index.ts:339`
- **What**: `write_file` is a destructive mutation tool (`destructiveHint: true`). No MCP-layer integration test exists. Lib-level coverage exists for `writeFileContent` in `lib.test.ts`, but the SDK round-trip (which is where #3110-class bugs live) is uncovered.
- **Why this bucket**: `OVERRIDE: de-escalated` from Medium (TEST-003 default) to Low. Rationale: (a) integration test infrastructure already exists in `structured-content.test.ts`, so the fix is an extension not a from-scratch fixture; (b) `validatePath` (the security-critical layer) IS tested at function level (136 test descriptors in `path-validation.test.ts`); (c) no observed corruption — this is a coverage gap, not a known-bug condition.
- **Suggested fix**: bundle into the same fixture extension as F-001. Add a write-then-read assertion per file.

#### F-003 — `TEST-003` (de-escalated) `edit_file` no MCP-layer test
- **Where**: `src/filesystem/index.ts:365`
- **What**: `edit_file` is destructive (`destructiveHint: true`) and non-idempotent (`idempotentHint: false`) — re-applying edits can fail or double-apply. No MCP-layer test.
- **Why this bucket**: same override rationale as F-002. Additional note: `applyFileEdits` has unit coverage in `lib.test.ts`; the `dryRun` path specifically warrants an integration test since it returns a git-style diff that the MCP client must parse.
- **Suggested fix**: same fixture extension. Cover both `dryRun: true` (diff format assertion) and `dryRun: false` (file-mutation assertion) paths.

#### F-004 — `TEST-003` (de-escalated) `move_file` no MCP-layer test
- **Where**: `src/filesystem/index.ts:597`
- **What**: `move_file` is destructive (deletes source). No MCP-layer test.
- **Why this bucket**: same override rationale as F-002. Additional risk: `move_file` validates BOTH source and destination paths via `validatePath` — a refactor that detaches one of the two validations would be silent without integration coverage.
- **Suggested fix**: same fixture extension. Assert (a) source no longer exists, (b) destination has expected content, (c) move across allowed-directory boundary fails.

#### F-005 — `TEST-003` (de-escalated) `create_directory` no MCP-layer test
- **Where**: `src/filesystem/index.ts:394`
- **What**: `create_directory` is non-destructive (`destructiveHint: false`) but mutating (`readOnlyHint: false`). No MCP-layer test.
- **Why this bucket**: `OVERRIDE: de-escalated` from Medium to Low — strongest case of the four override findings. Rationale: tool is `idempotentHint: true` and `destructiveHint: false`; re-applying does no harm; failure is observable to the caller. The integration coverage gap is real but the blast radius is the lowest among the four mutations.
- **Suggested fix**: same fixture extension. Assert directory creation + idempotent re-call.

#### F-006 — `SHAPE-001` `read_media_file` envelope deviates from 13/14 sibling tools
- **Where**: `src/filesystem/index.ts:267-297`
- **What**: 13 of 14 tools return the canonical TS SDK envelope `{content: [{type:"text", text}], structuredContent: {content: <string>}}`. `read_media_file` deviates: it returns `{content: [contentItem], structuredContent: {content: [contentItem]}}` cast as `unknown as CallToolResult`. The unsafe cast is the smoking gun — TypeScript flags the shape mismatch and the handler bypasses type-checking. The declared `outputSchema` (lines 258-264) is `{content: z.array(z.object({type, data, mimeType}))}` while every other tool's outputSchema is `{content: z.string()}`.
- **Why this bucket**: Low per SHAPE-001 default ("Mixed envelope vs raw dict across surface"). No security impact; a strict MCP client could fail to parse the array form if it relies on the documented `structuredContent.content: string` convention.
- **Suggested fix**: two routes:
  1. **Align** `read_media_file` outputSchema to declare `content: z.array(...)` and document the per-media envelope clearly. Drop the `as unknown as CallToolResult` cast (the type system would then accept the return shape).
  2. **Normalize** to the canonical string envelope: serialize the media object to JSON and return it as text. Lower-effort, preserves homogeneity.
   Maintainer choice. The cast-bypass is what flagged this; either resolution removes the cast.

### 3.5 Info

> Discoverability / consistency / decay observations. Batched into a single upstream PR per SOP §2 (Info routing).

#### F-007 — `DECAY-002` `read_file` partial decay (3-of-4 signals)
- **Where**: `src/filesystem/index.ts:213`
- **What**: `read_file` is registered with description starting `"DEPRECATED: Use read_text_file instead."`. Four-signal check:
  - CHANGELOG mention: n/a (no per-tool CHANGELOG in `src/filesystem/`)
  - README mention: ❌ (omitted from README's tool table — `read_text_file` is documented in its place)
  - Internal consumer: n/a (external repo)
  - Test: ❌ (no MCP-layer test; no lib-level test specific to the deprecation contract)
   3-of-4 signals fail (excluding the n/a). Tool is functional and indistinguishable from `read_text_file` at discovery time — a fresh agent reading the registered description sees "DEPRECATED" but can call it normally. No structured deprecation flag (e.g., SDK `_meta.deprecated`) is set.
- **Why this bucket**: Info per DECAY-002 default. Maintainer kept the tool intentionally for back-compat — this is documented intent, not abandonment.
- **Suggested fix**: if MCP SDK 1.26 supports tool-level `_meta.deprecated` (or equivalent), set it on `read_file` so MCP clients can surface the deprecation programmatically. Otherwise, a stderr deprecation warning on first call is the next-best signal. Long-term: remove in next major (`v1.0.0`?) per the deprecation policy.

#### F-008 — `DISC-003` `read_media_file` missing when-to-use
- **Where**: `src/filesystem/index.ts:251-254`
- **What**: Description is two lines: "Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories." Covers what + scope. Missing: when an agent should prefer this over `read_text_file` (e.g., binary detection? extension allowlist? size limits?), and the MIME fallback behavior (currently silent `application/octet-stream` for unknown extensions, undocumented).
- **Why this bucket**: Info per DISC-003 default. No security or correctness impact; pure discoverability.
- **Suggested fix**: extend description to ~4 lines: add when-to-use ("Use for binary files including images and audio; for text files use `read_text_file` instead — this tool returns base64 which is wasteful for plain text") + MIME fallback note + size-limit warning if any.

---

## 4. Disclosure timeline

| date | actor | event |
|---|---|---|
| 2026-04-26 | auditor | Audit completed against `modelcontextprotocol/servers@HEAD` |
| 2026-04-26 | auditor | Internal evidence record landed in [yakuphanycl/WinstonRedGuard#307](https://github.com/yakuphanycl/WinstonRedGuard/pull/307) |
| 2026-04-26 | auditor | This case-study published with `disclosure_status: public` (no embargo per SOP §2 Low/Info routing) |
| _pending_ | auditor | Public upstream PR opened against `modelcontextprotocol/servers` extending `__tests__/structured-content.test.ts` to all 14 tools (covers F-001 through F-005) |
| _pending_ | auditor | Public upstream PR opened batching F-006 (envelope reconciliation) |
| _pending_ | auditor | Public upstream PR or issue batching F-007 + F-008 (Info findings) per SOP §2 Info routing |

No private disclosure was performed. No GHSA was filed. No deadlines apply.

---

## 5. Upstream response

_Pending._ This document is published before any upstream PR has been opened, per SOP §2 Low/Info routing (which permits public-first, no-embargo). Upstream PRs will be opened in the order listed in §4. This section will be updated when responses land.

**Acknowledgement**: pending
**Patches landed**: pending
**Patches declined / wontfix**: pending
**Outstanding**: F-001 through F-008 (all eight pending upstream contact)

---

## 6. Reusable patterns

Two patterns surfaced from this audit that should feed back into the audit infrastructure:

- **Pattern**: TypeScript MCP server adaptation
  - **Observed in**: methodology §2, applies to all 8 findings indirectly
  - **Generalises because**: the official `modelcontextprotocol/servers` reference servers are TypeScript, and so are most third-party servers built on the TS SDK. Future external audits will keep encountering TS surfaces. The skill currently documents `@mcp.tool()` (Python FastMCP) as the canonical decorator.
  - **Proposed action**: extend [`SKILL.md`](../../skills/mcp-audit/SKILL.md) with a "TypeScript adaptation" subsection covering: (a) `server.registerTool()` grep pattern, (b) Zod-schema input/output inspection, (c) canonical envelope shape `{content: [...], structuredContent: {...}}`, (d) MCP-layer test recognition via `@modelcontextprotocol/sdk/client` imports, (e) error channel = throw vs in-band `{ok: false}` distinction.
  - **Tracked as**: _pending — to open follow-up PR against `wrg-skills/skills/mcp-audit/SKILL.md`_

- **Pattern**: type-system bypass cast as inconsistency marker
  - **Observed in**: F-006 (`as unknown as CallToolResult`)
  - **Generalises because**: in TypeScript MCP servers, an unsafe cast inside a tool handler return statement is a strong signal that the handler's actual return shape doesn't match the declared `outputSchema`. This is more reliable than reading the schema in isolation — the cast is the type system's own complaint, captured in source.
  - **Proposed action**: add a new SEVERITY row `SHAPE-005` "Tool handler return cast (`as unknown as CallToolResult` or equivalent) bypassing outputSchema typecheck" with default severity Low. Audit step §3 should grep for `as unknown as` and `as any` inside `registerTool` handler bodies as a discoverability signal for SHAPE-001 findings.
  - **Tracked as**: _pending — to propose row addition in follow-up PR_

---

## Appendix A — tool inventory snapshot

Format: `name | line | category | first sentence | annotations | outputSchema | mcp-layer test? | disc.`

| # | Tool | Line | Category | First sentence | Annotations | outputSchema | MCP test | Disc. |
|---|------|------|----------|----------------|-------------|--------------|----------|-------|
| 1 | `read_file` | 213 | read (deprecated) | "Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead." | `readOnlyHint:true` | `{content: string}` | none | **2** |
| 2 | `read_text_file` | 225 | read | "Read the complete contents of a file from the file system as text..." | `readOnlyHint:true` | `{content: string}` | none | **5** |
| 3 | `read_media_file` | 248 | read (media) | "Read an image or audio file. Returns the base64 encoded data and MIME type." | `readOnlyHint:true` | `{content: array<{type,data,mimeType}>}` ⚠️ | none | **3** |
| 4 | `read_multiple_files` | 300 | read (batch) | "Read the contents of multiple files simultaneously..." | `readOnlyHint:true` | `{content: string}` | none | **5** |
| 5 | `write_file` | 339 | mutation | "Create a new file or completely overwrite an existing file with new content..." | `readOnlyHint:false, idempotentHint:true, destructiveHint:true` | `{content: string}` | none | **4** |
| 6 | `edit_file` | 365 | mutation | "Make line-based edits to a text file. Each edit replaces exact line sequences..." | `readOnlyHint:false, idempotentHint:false, destructiveHint:true` | `{content: string}` | none | **4** |
| 7 | `create_directory` | 394 | mutation | "Create a new directory or ensure a directory exists..." | `readOnlyHint:false, idempotentHint:true, destructiveHint:false` | `{content: string}` | none | **5** |
| 8 | `list_directory` | 420 | read | "Get a detailed listing of all files and directories in a specified path..." | `readOnlyHint:true` | `{content: string}` | none | **5** |
| 9 | `list_directory_with_sizes` | 448 | read | "Get a detailed listing of all files and directories in a specified path, including sizes..." | `readOnlyHint:true` | `{content: string}` | **dedicated ×1** | **5** |
| 10 | `directory_tree` | 527 | read | "Get a recursive tree view of files and directories as a JSON structure..." | `readOnlyHint:true` | `{content: string}` | **dedicated ×1** | **5** |
| 11 | `move_file` | 597 | mutation | "Move or rename files and directories..." | `readOnlyHint:false, idempotentHint:false, destructiveHint:true` | `{content: string}` | none | **5** |
| 12 | `search_files` | 626 | read | "Recursively search for files and directories matching a pattern..." | `readOnlyHint:true` | `{content: string}` | none | **5** |
| 13 | `get_file_info` | 655 | read | "Retrieve detailed metadata about a file or directory..." | `readOnlyHint:true` | `{content: string}` | none | **5** |
| 14 | `list_allowed_directories` | 683 | read (introspection) | "Returns the list of directories that this server is allowed to access..." | `readOnlyHint:true` | `{content: string}` | none | **5** |

⚠️ = `read_media_file` has type-system bypass at handler return: `as unknown as CallToolResult` (index.ts:296).

**Aggregates**:
- Tools registered: 14
- Average discoverability: 4.50 / 5 (without deprecated outlier `read_file`: 4.69 / 5)
- Return-shape consistency: 93% (13/14)
- MCP-layer integration coverage: 14% (2/14)
- Naming consistency: 100% snake_case, action-prefix verbs

## Appendix B — methodology drift

The skill was developed against Python FastMCP. This audit applied it to a TypeScript MCP server. Three substitutions were made (recorded in §6 as a reusable pattern):

1. **Inventory grep**: `server\.registerTool\(` instead of `@mcp.tool()`. Inputs are Zod schemas, not Python annotations.
2. **Canonical envelope**: TS SDK convention `{content: [...], structuredContent: {...}}` substituted for FastMCP `{ok, ...}`. The five-axis rubric still applies; the canonical shape per ecosystem differs.
3. **Error-handling axis**: TS surface uses `throw` + SDK error channel, not `{ok: false}` envelope. Consistent within surface; flagging as deviation would force-fit Python idiom.

These substitutions did not require deviating from the skill's procedure, scoring rubric, or honest-scoring discipline. Recommendation: codify them as a TS-adaptation subsection in `SKILL.md` so the next external TS audit does not re-derive them.

---

## Appendix C — companion artifacts

- **Internal evidence record** (the working file the auditor produced before refiling to this case-study format): [yakuphanycl/WinstonRedGuard#307](https://github.com/yakuphanycl/WinstonRedGuard/pull/307)
- **Audit infrastructure that landed alongside this case-study**: [yakuphanycl/wrg-skills#7](https://github.com/yakuphanycl/wrg-skills/pull/7) (`_TEMPLATE.md`, `disclosure-sop.md`, `SEVERITY.md`)
- **Skill applied**: [`skills/mcp-audit/SKILL.md`](../../skills/mcp-audit/SKILL.md)
