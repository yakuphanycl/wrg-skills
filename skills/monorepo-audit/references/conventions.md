# Monorepo layout conventions

What `monorepo-audit` expects to see, and how to adapt when your repo doesn't match.

## Default layout

```
<repo_root>/
├── apps/                      ← configurable via --apps-dir
│   ├── app_a/
│   │   ├── pyproject.toml     ← required; fail_under read from here
│   │   ├── src/app_a/         ← OR flat: apps/app_a/app_a/
│   │   │   ├── __init__.py
│   │   │   └── ...
│   │   └── tests/
│   └── app_b/
│       └── ...
├── artifacts/
│   └── health/
│       ├── release_check_app_a.json    ← coverage record (optional)
│       └── release_check_app_b.json
└── ...
```

## Per-check expectations

### schema_drift

**Required:** The app's source contains `CREATE TABLE` stmts as string literals
(e.g. in `db.py` or `schema.py`).

**Discovery:** The check looks for a live SQLite DB at these paths, in order:

1. `<app>/data/<app>.db`
2. `<app>/<app>.db`
3. `~/.<app>/<app>.db`
4. `~/.<app>/data.db`
5. `~/.wrg/<app>.db` (WRG convention)
6. Any `~/.<app>/*.db` file

If none exist → skipped with a note ("no live DB found"). The check never
fails; missing DBs are expected (app may not have been run yet).

**Known limits:**
- Tables created via ORM migrations (Alembic, Django) won't be detected —
  the check parses raw DDL only.
- Dynamic table names (f-string with variable) are skipped.

### coverage_floor

**Required:** Each app's `pyproject.toml` has:
```toml
[tool.coverage.report]
fail_under = 60
```

**Coverage source**, tried in order:
1. `<repo>/artifacts/health/release_check_<app>.json` — JSON with a top-level
   `coverage` or `total_coverage` field, OR `apps[0].coverage`.
2. `<app>/coverage.xml` — standard coverage.py output (line-rate attribute).

If neither exists → skipped with note. Not a failure.

**Behavior:**
- `actual < floor` → `error` finding (drift is negative).
- `actual >= floor + 10` → advisory note: "floor could be raised".
  Not a failure, just a prompt.

### orphan_modules

**Required:** Each app has a package (either `src/<name>/` or flat `<name>/`)
with `__init__.py`.

**Exemptions:**
- `__init__.py`, `__main__.py`, `main.py` — reachable via import system or
  CLI runner, not through the import graph.
- Any module declared in `pyproject.toml`'s `[project.scripts]` as an entry
  point target (`my-cli = "my_app.cli:main"` → `my_app.cli` is exempt).

**False positives to watch for:**
- **Dynamic imports:** `importlib.import_module("my_app.plugins.foo")` is
  invisible to AST. Plugin architectures (discoverable-by-convention) will
  flag their own modules. Workaround: add them to `[project.scripts]` or
  convention: leave them as expected false positives.
- **Test fixtures imported via pytest's rootdir/conftest discovery** —
  `conftest.py` is usually inside `tests/`, not the package, so this is
  rarely an issue. If it is, move conftest or accept the false positive.

### orphan_tests

**Required:** Each app has a `tests/` directory at `apps/<app>/tests/` with
files matching `test_*.py` (recursive — subdirs like `tests/integration/`
are walked too).

**What it detects:** Absolute imports inside test files that target the
app's own package but resolve to a module that no longer exists in
`src/<app>/` (or the flat-layout package). The detector is happy as long as
either `<app>/<rest>.py` or `<app>/<rest>/__init__.py` exists.

**What it skips:**
- `conftest.py` and any non-`test_*.py` file (helper modules in `tests/` are
  not validated).
- **Relative imports** (`from . import X`, `from .helpers import Y`). They
  resolve against the test's own location, not src/, so they say nothing
  about the package.
- From-import names below the module level — `from my_app.utils import bar`
  validates `my_app.utils` exists; whether `bar` is a submodule, class, or
  function is ambiguous from AST and not flagged.

**False positives to watch for:**
- **Dynamic imports** in tests (`importlib.import_module(name)`) — uncommon
  but possible in plugin tests. Same workaround as orphan_modules: accept
  the false positive or pin the import statically.
- **Imports of the app's own legacy alias** (e.g. an old package name kept
  alive via `sys.modules` shim). The shim isn't visible to AST.

**Severity:** All findings are `warn`. Default exit code is 0 unless
something else triggers an error; use `--strict` to gate CI on these.

## Adapting to your layout

**Different subproject dir (e.g. `packages/` or `services/`):**
```bash
python audit.py --apps-dir packages
```

**Different health directory:**
```bash
python audit.py --health-dir ops/reports
```

**Run one check:**
```bash
python audit.py --only coverage_floor
```

**Skip noisy checks temporarily:**
```bash
python audit.py --skip schema_drift --skip orphan_modules
```

## What the skill can't do

- Multi-language repos (Go + Python mix etc.): only the Python side.
- Non-pyproject packaging (setup.py only, pure Poetry without PEP 621): the
  `fail_under` extraction may silently no-op; skill notes "no floor declared".
- Import graphs across apps: orphan_modules scans WITHIN an app only. A
  module imported only from a sibling app still reports as orphaned.
  Workaround: declare the sibling consumer explicitly or accept.
