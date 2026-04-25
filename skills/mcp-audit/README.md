# `mcp-audit` skill

Audit a FastMCP server for tool discoverability, return-shape consistency,
test coverage, and decay candidates. Skill procedure: [`SKILL.md`](SKILL.md).
Report template: [`references/audit_template.md`](references/audit_template.md).

## Audit infrastructure

| Document | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Skill procedure — what the audit does and how Claude runs it. |
| [`SEVERITY.md`](SEVERITY.md) | 32-row matrix mapping every finding type the audit produces to a default severity bucket (Critical / High / Medium / Low / Info). |
| [`references/audit_template.md`](references/audit_template.md) | Standalone audit report template (the per-tool 5-axis matrix). |
| [`docs/disclosure-sop.md`](../../docs/disclosure-sop.md) | Disclosure SOP for **external** audits — severity rubric, decision tree, GHSA + public-issue boilerplate. |
| [`docs/case-studies/_TEMPLATE.md`](../../docs/case-studies/_TEMPLATE.md) | Case-study document template — frontmatter, scope, methodology, findings table, disclosure timeline, upstream response, reusable patterns. |

## Real-world case studies

External audits that have used (or are using) this skill, with severity
summaries and disclosure status. Critical/High findings under embargo are
listed without reproduction detail until public disclosure.

| Target | Audit date | Status | Severity summary | Case-study |
|---|---|---|---|---|
| `modelcontextprotocol/servers` (`@modelcontextprotocol/server-filesystem@0.6.3`) | 2026-04-26 | public | 0 Critical / 0 High / 0 Medium / 6 Low / 2 Info | [filesystem-mcp-2026-04-26](../../docs/case-studies/filesystem-mcp-2026-04-26.md) |

When an audit lands, the row's "Case-study" column links to the document
under [`docs/case-studies/`](../../docs/case-studies/). Internal audits
(WRG monorepo, instinct) live in their own repos; the
[`SKILL.md` examples-in-the-wild section](SKILL.md#examples-in-the-wild)
links to those.

## Where to start

- **Running an audit on your own MCP server** → read [`SKILL.md`](SKILL.md).
  Public PR is fine; no SOP needed.
- **Running an audit on someone else's MCP server** → read
  [`SKILL.md`](SKILL.md), then [`SEVERITY.md`](SEVERITY.md), then
  [`docs/disclosure-sop.md`](../../docs/disclosure-sop.md) **before**
  opening any issue or PR upstream.
- **Writing up an audit** → copy
  [`docs/case-studies/_TEMPLATE.md`](../../docs/case-studies/_TEMPLATE.md)
  into `docs/case-studies/<target-slug>-<YYYY-MM-DD>.md` and fill it in
  per the frontmatter conventions.

## Why the disclosure SOP exists

The skill itself is severity-agnostic — it scores tools and surfaces
findings. The decision of *what to do* with a finding (private GHSA?
public PR? batched issue?) depends on whether the upstream maintainer is
the auditor or a third party. The SOP only kicks in for external audits;
internal monorepo audits keep using public PRs as before.
