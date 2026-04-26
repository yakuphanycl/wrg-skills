# Disclosure SOP — external MCP audits

Standard operating procedure for handling findings produced by the
[`mcp-audit` skill](../skills/mcp-audit/SKILL.md) against an **external** MCP
server (i.e., one this repo's author does not maintain).

For internal audits (own monorepo, own MCP servers), public PRs are always
fine — this SOP only kicks in when the upstream maintainer is a third party.

---

## 1. Severity rubric

Five buckets. Each finding type the audit produces gets a default severity
in [`skills/mcp-audit/SEVERITY.md`](../skills/mcp-audit/SEVERITY.md); this
document defines what those buckets *mean*.

### Critical
Findings that allow a remote or unauthenticated party to gain credentials,
execute arbitrary code, or exfiltrate user data with no further interaction.

Concrete examples:
- Hardcoded API key, OAuth secret, or session token committed to source or
  shipped inside a published package.
- Tool that returns the process environment (or a subset including secrets)
  in its response payload.
- `subprocess.run(..., shell=True)` (or `os.system`) where user-controlled
  tool args are interpolated into the command string.

### High
Findings that require some condition (auth foothold, specific input,
non-default config) but, once triggered, allow privilege escalation,
arbitrary file/network access, or data corruption.

Concrete examples:
- Mutation tool exposed without an auth gate or env-flag guard (e.g., a
  `*_create` / `*_delete` tool callable by any MCP client of the server).
- Path-traversal in a file-handling tool: `../` not stripped before
  `open()` or `Path.read_text()`.
- SSRF via an arbitrary-URL fetch tool with no allowlist (cloud metadata
  endpoint reachable, internal services scannable).

### Medium
Findings that meaningfully degrade safety, observability, or trust but do
not on their own enable compromise.

Concrete examples:
- Mutation tool with auth but **no audit log** — actions cannot be traced
  back to a caller.
- Verbose error message that leaks internal filesystem paths or stack
  traces to the MCP client.
- Untested mutation tool: no MCP-layer test exists, so blast radius on
  refactor is unknown.

### Low
Consistency, hygiene, and quality findings that surface in any audit but do
not affect security or correctness in deployed use.

Concrete examples:
- Return-shape drift across the surface (some tools return `{ok, ...}`,
  others return raw dicts).
- Bare `RuntimeError` raised from a tool that otherwise has no structured
  error path — inconsistent with the rest of the surface.
- Production tool with no MCP-layer test (smoke or unit) — non-mutation;
  failure is observable.

### Info
Documentation, discoverability, and decay observations. The maintainer can
batch these into a single PR or ignore them entirely without risk.

Concrete examples:
- Tautological docstring: tool `site_health` documented as
  "Check site health endpoint." — pure restatement of the function name.
- Missing trigger phrases / when-to-use / return shape in docstring (the
  three discoverability axes from the audit rubric).
- Decay candidate: tool absent from CHANGELOG, README, consumers, and
  tests for ≥6 months — a soft-deprecate or remove suggestion.

---

## 2. Decision tree

```
                            ┌─────────────────────┐
                            │  Finding produced   │
                            │  by mcp-audit skill │
                            └──────────┬──────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
       Critical / High             Medium                   Low / Info
              │                        │                        │
              ▼                        ▼                        ▼
       Private GHSA          Coordinated 90-day       Public issue / PR,
       (security advisory    disclosure: notify       direct, no embargo.
       on upstream repo)     maintainer privately,    Batch Info findings
              │              public after 90 days     into one PR where
              ▼              regardless of patch.     possible.
       7-day fix window              │
       (Critical) /                  ▼
       30-day fix window      Email + GHSA optional;
       (High); CVE            include suggested fix;
       request optional       set explicit deadline.
              │
              ▼
       Public disclosure
       on patch release —
       this case-study doc
       moves to status:public
```

### Critical — private GHSA, immediate
1. **Stop**. Do not file a public issue. Do not push a PR. Do not tweet.
2. Open a private GitHub Security Advisory on the upstream repo
   (`Security` tab → `Report a vulnerability`).
3. Use the GHSA boilerplate in §3.1.
4. Set a 7-day fix window in the message. Offer to test patches.
5. If no acknowledgement within 72h, escalate via the channel the
   maintainer publishes (email in `SECURITY.md`, security@ alias, etc.).
6. On patch release: publish the case-study document with
   `disclosure_status: public` and a CVE reference if assigned.

### High — private GHSA, 30-day fix window
1. Open private GHSA. Boilerplate in §3.1.
2. Set 30-day fix window. After 30 days without a patch, send a notice
   that public disclosure will follow on day 90.
3. On patch release **or** day 90 (whichever is earlier), publish the
   case-study document.

### Medium — coordinated 90-day disclosure
1. Notify the maintainer privately. GHSA is appropriate but not required;
   email or a private security channel is fine if GHSA is heavyweight for
   the scope. Boilerplate in §3.2.
2. Include the suggested fix in the initial message.
3. Set an explicit 90-day deadline in writing.
4. After 90 days, publish the case-study document regardless of patch
   status. If patched earlier, publish on patch release with credit.

### Low — public issue or PR, no embargo
1. Open a public issue **or** a public PR with the suggested fix —
   PR is preferred when the fix is clear and ≤30 lines.
2. Boilerplate in §3.3.
3. Reference the audit in the issue/PR body. Link the case-study document
   only if it is already public.

### Info — public, batched
1. Batch all Info findings from a single audit into **one** PR or **one**
   issue per upstream repo. A 12-finding scattered shotgun is unfriendly
   to maintainers.
2. Title: `docs(<repo>): batch discoverability/decay observations from MCP audit`.
3. Body uses the §3.3 boilerplate, with one finding per row in the table.

### Edge cases
- **Maintainer asks for a different channel** (e.g., "please email instead
  of GHSA"): comply, but record the channel switch in the case-study
  timeline.
- **Maintainer is unreachable** (no `SECURITY.md`, no email, issues
  archived): treat as Medium-or-higher and use GHSA. If the project is
  truly abandoned, document that in the case-study and escalate to
  package-registry security teams (PyPI, npm) for Critical findings only.
- **Multiple findings of mixed severity in one repo**: handle highest
  severity first via its channel. Lower-severity findings can wait for
  the disclosure window of the higher one to close, then go public
  together.
- **Medium severity where the disclosure IS the patch**: some Medium-bucket
  findings (`TEST-003` untested mutation, `ERR-002` mixed `raise` vs envelope,
  certain `SHAPE-*` drifts) are best resolved by an upstream PR that the
  maintainer can review on its own — there is nothing to disclose privately
  beyond the diff itself, and the 90-day window adds friction without
  protecting users. In these cases, route as Low (public PR with the fix)
  and record the routing decision in the case-study finding's "Why this
  bucket" line as `OVERRIDE: de-escalated to Low — disclosure IS the patch`.
  This is distinct from a generic Medium → Low de-escalation; the
  patch-as-disclosure rationale should be explicit. Concrete trigger: the
  maintainer can fully assess the risk by reading the PR diff in
  isolation, with no proof-of-concept exploit needed and no user-data
  exposure window between merge and release.
- **Maintainer-tracked, documented limitation matching audit finding**: if
  a Medium-or-higher finding (e.g., `SEC-004` SSRF posture, `SEC-008`
  missing rate limit) is already tracked by an open enhancement issue on
  the upstream repo AND the README documents the limitation explicitly
  (e.g., a `[!CAUTION]` block warning operators), de-escalate to Low and
  route as a comment on the existing issue with audit attestation. Filing
  a fresh GHSA or new public issue would duplicate the maintainer's own
  tracking. Record as `OVERRIDE: de-escalated to Low — maintainer-aware
  + documented limitation + tracked via OPEN issue #<N>`. First applied:
  `mcp-server-fetch` audit (2026-04-26), comment on
  [`modelcontextprotocol/servers#2317`](https://github.com/modelcontextprotocol/servers/issues/2317).

---

## 3. Boilerplate templates

Copy-paste these into the relevant channel. Replace `<...>` placeholders.
Do not include the markdown comment lines.

### 3.1 GHSA submission (Critical / High)

```markdown
**Title**: <one-line summary> in `<package>@<version>`

**Affected versions**: `<version-range, e.g. <1.4.2 or >=1.0.0,<1.4.2>`
**Fixed in**: <pending | vX.Y.Z>
**Severity**: <Critical | High>
**CWE**: <CWE-ID if known, e.g. CWE-78 for command injection>

## Summary
<two-sentence description of the issue and its impact>

## Affected component
- File: `<path/to/file.py>`
- Line(s): `<NN-MM>`
- Tool / function: `<tool_name>`

## Reproduction
1. <step>
2. <step>
3. <observed outcome>

## Impact
<what an attacker gains; who is affected; under what preconditions>

## Suggested fix
<concrete remediation; ideally a patch or PR link if you have one>

## Disclosure plan
- Reporter requests a <7-day | 30-day> fix window.
- After patch release, the reporter will publish a case-study at
  `<URL to the eventual public case-study doc>`.
- CVE assignment: <reporter requests | maintainer to handle | not requested>.

## Reporter
- Name / handle: <...>
- Contact: <email>
- Audit methodology: https://github.com/yakuphanycl/wrg-skills/blob/main/skills/mcp-audit/SKILL.md
```

### 3.2 Coordinated private disclosure (Medium)

```markdown
Hi <maintainer>,

I ran an MCP audit against `<repo>@<sha>` using the `mcp-audit` skill at
https://github.com/yakuphanycl/wrg-skills/tree/main/skills/mcp-audit and
identified one Medium-severity finding I'd like to coordinate on before
filing publicly.

**Finding**: <one-line summary>
**Where**: `<path/to/file.py:NN>`
**What**: <two sentences>
**Why Medium**: <which row of skills/mcp-audit/SEVERITY.md applies>
**Suggested fix**: <one paragraph or patch>

Per https://github.com/yakuphanycl/wrg-skills/blob/main/docs/disclosure-sop.md,
Medium findings follow coordinated 90-day disclosure: I'll publish a public
case-study on or before <YYYY-MM-DD + 90d> regardless of patch status. If you
patch sooner, I'll publish on release with credit.

Happy to test a patch or open a PR if helpful — just let me know which you'd
prefer.

Thanks,
<reporter>
```

### 3.3 Public issue / PR (Low / Info)

```markdown
**Title**: `<area>: <short observation>` (e.g., `docs(server): batch discoverability findings from MCP audit`)

## Summary
This issue/PR collects <N> <Low | Info>-severity findings produced by an MCP
audit of `<repo>@<sha>`. Methodology:
https://github.com/yakuphanycl/wrg-skills/blob/main/skills/mcp-audit/SKILL.md.

No security impact — these are consistency, documentation, and discoverability
observations. Severity rubric:
https://github.com/yakuphanycl/wrg-skills/blob/main/docs/disclosure-sop.md#1-severity-rubric.

## Findings

| # | tool / location | category | observation | suggested fix |
|---|---|---|---|---|
| 1 | `tool_x` (`server.py:42`) | DISC-001 | Tautological docstring (1/5) | Rewrite to add when-to-use + return shape |
| 2 | `tool_y` (`server.py:91`) | SHAPE-001 | Returns raw dict; rest of surface uses `{ok}` | Wrap in envelope |
| ... | ... | ... | ... | ... |

## Why one batched item
Scattering 12 separate issues across the tracker is unfriendly. Happy to
split if any specific finding warrants its own conversation.

## Reporter
- Audit doc: <link to public case-study, if already published>
- No coordinated disclosure needed for this severity bucket.
```

---

## 4. Case-study lifecycle

Each external audit produces one case-study document under
[`docs/case-studies/`](case-studies/), authored from
[`_TEMPLATE.md`](case-studies/_TEMPLATE.md).

`disclosure_status` field in the frontmatter walks through:

| status | meaning | document visibility |
|---|---|---|
| `draft` | Audit running or just finished; nothing reported upstream yet. | Local only — do not commit findings publicly. |
| `private` | Critical/High findings filed via GHSA; embargo active. | Document may be committed but **redact reproduction steps** for embargoed findings. |
| `coordinated` | Medium findings under 90-day clock with maintainer notified. | Document committable; reproduction steps may stay if maintainer agrees. |
| `public` | All findings disclosed (patched, deadline passed, or Low/Info). | Full document public. |

A document at `disclosure_status: public` is the canonical public record.
Earlier states are working drafts.

---

## 5. What this SOP is NOT

- Not a CVE-issuance authority. Use GitHub or MITRE for CVE assignment.
- Not a substitute for the upstream project's own `SECURITY.md` if one
  exists — read it first; honour its preferred channel and timeline.
- Not a guarantee of legal cover. Coordinated disclosure norms reduce
  risk but do not eliminate it; for high-stakes findings, get qualified
  legal advice.
- Not for internal audits. The author's own monorepos use public PRs
  for everything; this SOP exists because the upstream maintainer is a
  third party.
