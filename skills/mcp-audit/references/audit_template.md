# MCP tool audit — `<server-name>` (<YYYY-MM-DD>)

> Evidence-only audit of the MCP tool surface for `<server-name>` (path: `<src/path/to/server/>`). Read-only — no code changes. Output is a "this-week pick" of ≤1hr fixes plus a deferred next-session backlog.
>
> **Author**: <maintainer or agent name>, <YYYY-MM-DD>.

---

## 1. Tool inventory

Total tools: **N** (across <M> modules).

| # | Tool | Module | Category | Description (first sentence) | Args | Return |
|---|---|---|---|---|---|---|
| 1 | `tool_a` | `server.py:NN` | core | `Description here.` | (path: str) | dict |
| 2 | `tool_b` | `server.py:NN` | export | `Description here.` | () | str |
| ... | ... | ... | ... | ... | ... | ... |

**Distribution across modules**: `module_x.py` ×N, `module_y.py` ×M.

---

## 2. Discoverability score (1-5 per tool)

Rubric:
- **5** — description has trigger phrases + when-to-use + return shape
- **4** — has 2 of the 3 (e.g., trigger phrases + return shape, missing when-to-use)
- **3** — has 1 of the 3
- **2** — present but uninformative beyond function name
- **1** — docstring just restates the function name ("Check site health endpoint." for `site_health`)

| Tool | Score | Justification (only for <5) |
|---|---|---|
| `tool_a` | 5/5 | — |
| `tool_b` | 4/5 | Has trigger phrases + return shape; missing when-to-use |
| `tool_c` | 1/5 | "Check X endpoint." — pure tautology |
| ... | ... | ... |

**Average**: `<sum>/<N>` = **<X.YZ>/5**

**Distribution**: `5/5: <count>` | `4/5: <count>` | `3/5: <count>` | `2/5: <count>` | `1/5: <count>`

**Top tautological docstrings** (1/5):
- `tool_c` (`server.py:NN`) — "Check X endpoint."
- `tool_d` (`server.py:NN`) — "Get the Y."
- ...

---

## 3. Consistency audit

### 3.1 Return-shape

| Idiom | Count | Tools |
|---|---|---|
| `{ok: True, ...}` envelope | <N> / <total> | `tool_a`, `tool_b`, ... |
| Raw dict (no ok field) | <N> | `tool_x`, ... |
| Raw list / raw str | <N> | `tool_y`, ... |
| Raises on error | <N> | `tool_z`, ... |
| Error-by-key-presence (`{error: "..."}`) | <N> | `tool_w`, ... |

**Consistency**: `<percentage>% with `{ok}` envelope`. **Outliers**: list specific tools.

### 3.2 Naming

- Snake_case: ✓ / ✗ (any exceptions: list)
- Domain prefix (e.g., `memory_*`): ✓ / ✗ / mixed (which prefixes exist, which tools lack one)
- Action verb consistency: any `get_x` vs `fetch_y` vs `read_z` collisions?

### 3.3 Error handling

| Tool | Error path |
|---|---|
| `tool_a` | raise `ValueError` |
| `tool_b` | returns `{ok: False, error: ...}` |
| `tool_c` | returns `{}` (silent) |

Recommendation if mixed: pick one canonical pattern, name it as a follow-up.

---

## 4. Test coverage

| Tool | Layer where tested | Coverage |
|---|---|---|
| `tool_a` | CLI + store | dedicated unit + smoke |
| `tool_b` | store only | smoke only at MCP layer |
| `tool_c` | none | no test fixture |

**Summary**: `<N>/<total>` tools have dedicated MCP-layer tests. `<M>/<total>` are smoke-only or untested at the wrapper.

---

## 5. Decay candidates

For each tool, four signals: CHANGELOG mention? README mention? imported by any consumer? exercised in tests?

| Tool | CHANGELOG | README | Consumer | Test | Decay risk |
|---|---|---|---|---|---|
| `tool_a` | ✓ | ✓ | ✓ | ✓ | none |
| `tool_d` | ✗ | ✗ | ✗ | ✗ | **high** |
| `tool_e` | ✓ | ✗ | ✗ | smoke only | medium |

**Decay candidates** (failing 3+ signals): `tool_d`, `tool_e`, ...

**Recommendation per candidate**:
- `tool_d` → **REMOVE** (no users found; safe to drop in next minor)
- `tool_e` → **SOFT-DEPRECATE** (add deprecation notice in docstring, keep callable for ≥6 months)
- `tool_f` → **KEEP** (low signal but recently added; re-audit in 30 days)

---

## 6. Decision gate

### Numbers
- Total tools: **N**
- Average discoverability: **<X.YZ>/5**
- Return-shape consistency: **<percentage>%**
- MCP-layer test coverage: **<N>/<total>**

### This-week pick (≤1hr each, name specific tools)

1. **<concrete fix>** — e.g., "Add `"ok": True` to `connector_status` (server.py:92)" — 5 min
2. **<concrete fix>** — e.g., "Rewrite 4 tautological docstrings: `site_health`, `site_post`, `pulseboard_health`, `research_motor_healthz`" — 30 min

### Next-session backlog (deferred, >1hr each)

3. **<concrete fix>** — e.g., "Align all 3 `research_motor_*` tools to `{ok}` envelope" — 1-2 hr (touches structured error path)
4. **<concrete fix>** — e.g., "Add behavioural test for `tool_x` (most user-facing untested)" — 1 hr
5. **<concrete fix>** — e.g., "SOFT-DEPRECATE 5 PulseBoard tools" — 30 min + 6-month re-eval calendar

### Decay-candidate fates

- `tool_d` → REMOVE
- `tool_e` → SOFT-DEPRECATE
- ...

---

## Maintainer checklist

- [ ] Read §1 — agrees with the inventory count and module distribution
- [ ] Read §2 — agrees the 1/5 docstrings are genuinely tautological (not "would-take-too-long-to-explain")
- [ ] Read §3.1 — agrees with the consistency outliers
- [ ] Read §6 — picks 1-2 from "this-week pick" to land THIS week
- [ ] Files a follow-up issue for "next-session backlog" items so they don't fall off the radar

---

## References

- Audit precedent: [`yakuphanycl/WinstonRedGuard#295`](https://github.com/yakuphanycl/WinstonRedGuard/pull/295) (wrg_mcp_server)
- Audit precedent: [`yakuphanycl/instinct#26`](https://github.com/yakuphanycl/instinct/pull/26) (instinct)
- Skill source: [`yakuphanycl/wrg-skills/skills/mcp-audit`](https://github.com/yakuphanycl/wrg-skills/tree/main/skills/mcp-audit)
