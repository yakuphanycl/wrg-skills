"""monorepo-audit — three static checks for a Python monorepo.

No external deps beyond stdlib; tries `tomllib` (3.11+) or `tomli` as
fallback. Safe to run: read-only, no network, no mutation. Finishes in
seconds on typical repos.

Checks:
  schema_drift   — parse CREATE TABLE stmts from source, compare to
                   live SQLite DBs under likely-default locations.
                   Opt-out: no DB found → skipped with a note.
  coverage_floor — read each app's pyproject fail_under, compare to
                   recorded coverage (release_check JSON or coverage.xml).
  orphan_modules — AST import graph per app, flag .py files nobody imports.
                   Exempt: __init__.py, __main__.py, main.py, and any
                   module that backs a `[project.scripts]` entry point.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sqlite3
import sys

# Windows default cp1254 can't encode emoji markers — force utf-8
# so the skill works identically on any terminal. Safe no-op on Unix.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────────
# Shared types
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Finding:
    check: str
    app: str
    detail: str
    severity: str = "warn"  # "warn" or "error"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckResult:
    name: str
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# TOML loader (3.11+ stdlib or 3.10 fallback)
# ──────────────────────────────────────────────────────────────────────


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ──────────────────────────────────────────────────────────────────────
# App discovery
# ──────────────────────────────────────────────────────────────────────


def discover_apps(repo_root: Path, apps_dir: str) -> list[Path]:
    root = repo_root / apps_dir
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and (p / "pyproject.toml").is_file()
    )


def _app_package_dir(app_path: Path) -> Path | None:
    """Return the package source directory: either src/<pkg> or flat <pkg>."""
    name_hint = app_path.name
    candidates = [
        app_path / "src" / name_hint,
        app_path / name_hint,
    ]
    for c in candidates:
        if c.is_dir() and (c / "__init__.py").is_file():
            return c
    # Fallback: any subdir with __init__.py under src/ or app root
    for base in (app_path / "src", app_path):
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir() and (child / "__init__.py").is_file():
                    return child
    return None


# ──────────────────────────────────────────────────────────────────────
# Check 1: schema_drift
# ──────────────────────────────────────────────────────────────────────


_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def _extract_ddl(app_pkg: Path) -> list[str]:
    """Scan .py files for string literals containing CREATE TABLE."""
    ddls: list[str] = []
    for py in app_pkg.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _CREATE_TABLE_RE.search(node.value):
                    ddls.append(node.value)
    return ddls


def _expected_schema(ddls: list[str]) -> dict[str, set[str]]:
    """Materialize DDL in-memory and read back column sets per table."""
    if not ddls:
        return {}
    try:
        conn = sqlite3.connect(":memory:")
        for ddl in ddls:
            try:
                conn.executescript(ddl)
            except sqlite3.Error:
                continue
        tables: dict[str, set[str]] = {}
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            tname = row[0]
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tname})")}
            tables[tname] = cols
        conn.close()
        return tables
    except sqlite3.Error:
        return {}


def _actual_schema(db_path: Path) -> dict[str, set[str]]:
    conn = sqlite3.connect(str(db_path))
    tables: dict[str, set[str]] = {}
    try:
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            tname = row[0]
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tname})")}
            tables[tname] = cols
    finally:
        conn.close()
    return tables


def _guess_db_path(app_name: str, app_path: Path, home: Path) -> Path | None:
    """Probe common locations for an app's live SQLite DB."""
    candidates = [
        app_path / "data" / f"{app_name}.db",
        app_path / f"{app_name}.db",
        home / f".{app_name}" / f"{app_name}.db",
        home / f".{app_name}" / "data.db",
        home / ".wrg" / f"{app_name}.db",
    ]
    # Also scan home/.<app_name>/ for any .db file
    app_state = home / f".{app_name}"
    if app_state.is_dir():
        candidates.extend(app_state.glob("*.db"))
    for c in candidates:
        if c.is_file():
            return c
    return None


def _is_empty_db(db_path: Path) -> bool:
    """True if the SQLite file exists but contains no user tables.

    A common false-positive source: an app calls `sqlite3.connect(path)`
    on first import, which creates an empty file even if nothing is
    written. Until the first migration runs, `sqlite_master` is empty
    and every CREATE TABLE in source looks like "missing in DB" drift.
    Treat this the same as "no DB found" — skip with a note.

    First documented: 2026-04-26 monorepo-audit run on WRG, where
    pulseboard.db (DORMANT app) produced 8 false-positive schema_drift
    findings.
    """
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()
            return (row[0] if row else 0) == 0
    except sqlite3.Error:
        return False


def check_schema_drift(apps: list[Path], home: Path) -> CheckResult:
    result = CheckResult(name="schema_drift")
    for app_path in apps:
        app_name = app_path.name
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue
        ddls = _extract_ddl(pkg)
        if not ddls:
            continue  # silent — app has no SQL, nothing to check
        expected = _expected_schema(ddls)
        if not expected:
            result.notes.append(f"{app_name}: DDL found but failed to parse")
            continue
        db_path = _guess_db_path(app_name, app_path, home)
        if db_path is None:
            result.notes.append(
                f"{app_name}: skipped, no live DB found at common paths"
            )
            continue
        if _is_empty_db(db_path):
            result.notes.append(
                f"{app_name}: skipped, DB exists at {db_path.name} but contains "
                f"zero user tables (likely created on import, never migrated)"
            )
            continue
        try:
            actual = _actual_schema(db_path)
        except sqlite3.Error as exc:
            result.findings.append(Finding(
                check="schema_drift", app=app_name,
                detail=f"live DB read failed: {exc}",
                severity="error",
            ))
            continue
        for table, expected_cols in expected.items():
            if table not in actual:
                result.findings.append(Finding(
                    check="schema_drift", app=app_name,
                    detail=f"table '{table}' in code but missing from {db_path.name}",
                ))
                continue
            actual_cols = actual[table]
            only_in_db = actual_cols - expected_cols
            only_in_ddl = expected_cols - actual_cols
            for col in sorted(only_in_db):
                result.findings.append(Finding(
                    check="schema_drift", app=app_name,
                    detail=f"table '{table}' column '{col}' in DB but not in code",
                ))
            for col in sorted(only_in_ddl):
                result.findings.append(Finding(
                    check="schema_drift", app=app_name,
                    detail=f"table '{table}' column '{col}' in code but not in DB",
                ))
        for table in sorted(set(actual) - set(expected)):
            result.notes.append(
                f"{app_name}: table '{table}' in DB but not in code "
                f"(might be legacy / external)"
            )
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 2: coverage_floor
# ──────────────────────────────────────────────────────────────────────


def _floor_from_pyproject(pyproject: Path) -> int | None:
    data = _load_toml(pyproject)
    tool = data.get("tool", {})
    cov = tool.get("coverage", {})
    report = cov.get("report", {})
    val = report.get("fail_under")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _coverage_from_health_json(path: Path) -> int | None:
    """Look for a 'coverage' or 'total' percent in a release-check JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for key in ("coverage", "total_coverage", "pct"):
        if key in data and isinstance(data[key], (int, float)):
            return int(data[key])
    # Nested structure (common): apps[0].coverage
    apps = data.get("apps")
    if isinstance(apps, list) and apps:
        first = apps[0]
        if isinstance(first, dict):
            for key in ("coverage", "pct"):
                if key in first and isinstance(first[key], (int, float)):
                    return int(first[key])
    return None


def _coverage_from_coverage_xml(xml_path: Path) -> int | None:
    """Very loose parse of coverage.py XML for line-rate."""
    try:
        text = xml_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'line-rate="([0-9.]+)"', text)
    if m:
        try:
            return int(round(float(m.group(1)) * 100))
        except ValueError:
            return None
    return None


def check_coverage_floor(apps: list[Path], health_dir: Path) -> CheckResult:
    result = CheckResult(name="coverage_floor")
    for app_path in apps:
        app_name = app_path.name
        pyproj = app_path / "pyproject.toml"
        if not pyproj.is_file():
            continue
        floor = _floor_from_pyproject(pyproj)
        if floor is None:
            result.notes.append(f"{app_name}: no fail_under declared")
            continue

        actual: int | None = None
        health_json = health_dir / f"release_check_{app_name}.json"
        if health_json.is_file():
            actual = _coverage_from_health_json(health_json)
        if actual is None:
            cov_xml = app_path / "coverage.xml"
            if cov_xml.is_file():
                actual = _coverage_from_coverage_xml(cov_xml)

        if actual is None:
            result.notes.append(
                f"{app_name}: fail_under={floor}, no coverage record found"
            )
            continue
        drift = actual - floor
        if drift < 0:
            result.findings.append(Finding(
                check="coverage_floor", app=app_name,
                detail=f"fail_under={floor}, actual={actual} (drift: {drift:+d})",
                severity="error",
            ))
        elif drift >= 10:
            # Not a finding — an advisory note: floor could be raised
            result.notes.append(
                f"{app_name}: fail_under={floor}, actual={actual} "
                f"(floor could be raised)"
            )
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 3: orphan_modules
# ──────────────────────────────────────────────────────────────────────


_EXEMPT_FILENAMES = {"__init__.py", "__main__.py", "main.py"}

# §6.2: ASGI app frameworks whose `app = Framework(...)` at module top
# marks the file as an entrypoint loaded externally (uvicorn, hypercorn).
_ASGI_FRAMEWORK_NAMES = {"FastAPI", "Starlette", "Flask", "Quart", "Sanic"}

# §6.1: dynamic-dispatch markers — call patterns that load sibling modules
# at runtime via reflection rather than static import. Files in directories
# containing these patterns are dispatched, not orphaned.
_DYNAMIC_DISPATCH_MARKERS = ("pkgutil.iter_modules", "importlib.import_module")


def _script_targets(pyproject: Path) -> set[str]:
    """Dotted module paths that back `[project.scripts]` entries."""
    data = _load_toml(pyproject)
    scripts = data.get("project", {}).get("scripts", {}) or {}
    targets: set[str] = set()
    for _name, spec in scripts.items():
        if isinstance(spec, str) and ":" in spec:
            mod = spec.split(":", 1)[0]
            targets.add(mod)
            # also exempt any parent packages
            parts = mod.split(".")
            for i in range(1, len(parts)):
                targets.add(".".join(parts[:i]))
    return targets


def _imports_from_file(py: Path) -> set[str]:
    """Extract all import targets from a file.

    Handles three patterns that orphan detection needs to see:
      import pkg.mod              → "pkg", "pkg.mod"
      from pkg import mod         → "pkg", "pkg.mod"  (mod might be a submodule)
      from . import mod           → "mod"              (bare, match via suffix)
      from .submod import X       → "submod", "submod.X"
    """
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name)
                # Also add parent packages: pkg.sub.leaf → pkg, pkg.sub
                parts = n.name.split(".")
                for i in range(1, len(parts)):
                    imports.add(".".join(parts[:i]))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
                # Each imported name might be a submodule of the parent
                for n in node.names:
                    if n.name != "*":
                        imports.add(f"{node.module}.{n.name}")
            # Relative imports (from . import foo / from .sub import X):
            # record bare name; suffix match on full dotted module will catch it.
            for n in node.names:
                if n.name != "*":
                    imports.add(n.name)
    return imports


def _is_asgi_entrypoint(py: Path) -> bool:
    """§6.2: True if the file declares `app = <ASGI framework>(...)` at module top.

    Catches uvicorn-/hypercorn-mounted ASGI apps that have no static
    importers (the runtime loads them via the `module:variable` string).
    """
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "app" for t in node.targets
        ):
            continue
        if isinstance(node.value, ast.Call):
            fn = node.value.func
            name = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else None
            )
            if name in _ASGI_FRAMEWORK_NAMES:
                return True
    return False


def _is_plugin_entrypoint(py: Path) -> bool:
    """§6.2: True if filename is `plugin.py` AND module-level marker present.

    Pluggable monorepo convention (e.g., Control Center HTTP-mount
    discovery): each app drops a `plugin.py` that the host loads via a
    discovery mechanism. No static importer in source.

    Marker = either docstring containing 'plugin' / 'entrypoint', or a
    top-level dunder like `__plugin__ = True` / `PLUGIN = ...`.
    """
    if py.name != "plugin.py":
        return False
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    docstring = ast.get_docstring(tree) or ""
    if any(k in docstring.lower() for k in ("plugin", "entrypoint", "entry point")):
        return True
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and (
                    t.id.startswith("__plugin")
                    or t.id == "PLUGIN"
                    or t.id == "PLUGINS"
                ):
                    return True
    return False


def _is_dynamic_dispatch_dir(directory: Path) -> bool:
    """§6.1: True if a same-level sibling uses dispatch markers.

    The canonical pattern: a parent module sits next to a submodule
    directory and does `pkgutil.iter_modules(<dir>.__path__)` +
    `importlib.import_module(...)` to load every submodule of <dir> by
    name. Submodules in <dir> are loaded at runtime, not via static
    `import`, so they appear as orphans without this check.

    "Same-level sibling" = a `.py` file directly in `directory.parent`,
    OR `directory/__init__.py`, OR a registry/loader file in the
    sibling tree at depth ≤2. We deliberately bound the search radius
    so a project-wide dispatcher (e.g., a single `plugin_loader.py` at
    repo root) doesn't auto-exempt every directory.

    First documented: 2026-04-26 monorepo-audit run on WRG, where 22 of
    34 orphan_modules findings (52%) were `research_motor/cli/handlers/*`,
    all dispatched by their parent `cli/registry.py` (a same-level
    sibling at `directory.parent / registry.py`).
    """
    if not directory.is_dir():
        return False
    candidates: list[Path] = []
    # 1. Files directly in the parent dir (sibling of `directory`)
    candidates.extend(p for p in directory.parent.glob("*.py"))
    # 2. The directory's own __init__.py (parent module loading children)
    init = directory / "__init__.py"
    if init.is_file():
        candidates.append(init)
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if all(marker in text for marker in _DYNAMIC_DISPATCH_MARKERS):
            return True
    return False


def _is_test_only_consumer(py: Path, mod: str, app_path: Path) -> bool:
    """§6.2: True if at least one `tests/test_*.py` actually imports this module.

    Daemon/worker modules with only sibling `tests/test_*.py` consumers
    look like orphans to the static pkg graph (which doesn't scan tests/),
    but they're entrypoints — the test is verifying the entrypoint
    contract. We've already established there are no pkg-graph consumers
    by the time this runs; if a test really imports the module, it's
    not dead.

    Match logic: parse each `tests/test_*.py` AST and look at actual
    import nodes. A leaf substring would over-match (a string literal,
    variable name, or docstring containing the leaf would falsely
    exempt a genuinely orphan adapter).

    Match: import target equals `mod`, OR equals the leaf name from a
    `from <pkg> import <leaf>` where `<pkg>` is a prefix of `mod`.
    """
    tests_dir = app_path / "tests"
    if not tests_dir.is_dir():
        return False
    leaf = mod.rsplit(".", 1)[-1]
    parent_pkg = mod.rsplit(".", 1)[0] if "." in mod else ""
    for test_py in tests_dir.rglob("test_*.py"):
        try:
            tree = ast.parse(test_py.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name == mod:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module == mod:
                    return True
                # `from <parent_pkg> import <leaf>` matches when <parent_pkg>
                # is a true prefix of <mod> AND <leaf> appears in the import list
                if node.module and parent_pkg and (
                    node.module == parent_pkg
                    or parent_pkg.startswith(node.module + ".")
                ):
                    if any(n.name == leaf for n in node.names):
                        return True
    return False


def check_orphan_modules(apps: list[Path]) -> CheckResult:
    result = CheckResult(name="orphan_modules")
    for app_path in apps:
        app_name = app_path.name
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue
        py_files = list(pkg.rglob("*.py"))
        if not py_files:
            continue
        script_mods = _script_targets(app_path / "pyproject.toml")

        # Build module name for each file
        file_to_mod: dict[Path, str] = {}
        mod_to_file: dict[str, Path] = {}
        for py in py_files:
            rel = py.relative_to(pkg.parent)
            parts = rel.with_suffix("").parts
            mod = ".".join(parts)
            file_to_mod[py] = mod
            mod_to_file[mod] = py

        # Collect all imports from every file
        all_imports: set[str] = set()
        for py in py_files:
            all_imports |= _imports_from_file(py)

        # For each file, is there any importer?
        for py, mod in file_to_mod.items():
            if py.name in _EXEMPT_FILENAMES:
                continue
            if mod in script_mods:
                continue  # exempt: registered as CLI entry
            # Considered imported if some import name equals mod or starts with mod + "."
            referenced = any(
                imp == mod or imp.startswith(mod + ".") or
                mod.endswith("." + imp) or mod == imp
                for imp in all_imports
            )
            if referenced:
                continue
            # §6.1: dynamic dispatch — file in a dispatched directory
            if _is_dynamic_dispatch_dir(py.parent):
                continue
            # §6.2: ASGI entrypoint
            if _is_asgi_entrypoint(py):
                continue
            # §6.2: plugin.py entrypoint convention
            if _is_plugin_entrypoint(py):
                continue
            # §6.2: test-only consumer (worker/daemon entrypoints)
            if _is_test_only_consumer(py, mod, app_path):
                continue
            rel_display = py.relative_to(app_path)
            result.findings.append(Finding(
                check="orphan_modules", app=app_name,
                detail=f"{rel_display} — no importers found",
            ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 4: required_adapters
# ──────────────────────────────────────────────────────────────────────


def _required_adapter_names(init_path: Path) -> tuple[list[str], str] | None:
    """Parse __all__ or REQUIRED_ADAPTERS from an adapters/__init__.py.

    Returns (names, source) where source is "REQUIRED_ADAPTERS" or
    "__all__", or None if neither contract list is present.
    REQUIRED_ADAPTERS wins when both are declared.
    """
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            continue
        names: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
        if not names:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in (
                "__all__", "REQUIRED_ADAPTERS"
            ):
                found[target.id] = names
    if "REQUIRED_ADAPTERS" in found:
        return found["REQUIRED_ADAPTERS"], "REQUIRED_ADAPTERS"
    if "__all__" in found:
        return found["__all__"], "__all__"
    return None


def detect_required_adapters(apps: list[Path]) -> CheckResult:
    """Flag declared adapters that have no matching <name>.py module.

    Pattern: an adapter package's `__init__.py` declares a contract list
    (`REQUIRED_ADAPTERS = [...]` or `__all__ = [...]`) of adapter names.
    Each name should resolve to either `<name>.py` or `<name>/__init__.py`
    under the same `adapters/` directory. A missing file means the
    declared contract drifted from the implementation — typically a
    re-export typo or a deleted module that __all__ still mentions.

    Severity: ADAPTER-001 (Medium). REQUIRED_ADAPTERS lists are treated
    as strict module-name contracts (every name must resolve). Plain
    `__all__` is treated leniently: it is only flagged when at least one
    of its names resolves to a module — that's the signal __all__ is
    being used as a module-name list (not a re-export symbol list).
    """
    result = CheckResult(name="required_adapters")
    for app_path in apps:
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue
        adapters_dir = pkg / "adapters"
        init = adapters_dir / "__init__.py"
        if not init.is_file():
            continue
        parsed = _required_adapter_names(init)
        if parsed is None:
            continue
        names, source = parsed
        # Lenient mode for plain __all__: skip unless the convention is
        # clearly module-name-style (≥1 name resolves to a real module).
        if source == "__all__":
            any_resolves = any(
                (adapters_dir / f"{n}.py").is_file()
                or (adapters_dir / n / "__init__.py").is_file()
                for n in names
            )
            if not any_resolves:
                result.notes.append(
                    f"{app_path.name}: adapters/__init__.py __all__ looks like "
                    f"re-export symbols (no name maps to a module) — skipped"
                )
                continue
        for name in names:
            mod_file = adapters_dir / f"{name}.py"
            sub_init = adapters_dir / name / "__init__.py"
            if mod_file.is_file() or sub_init.is_file():
                continue
            result.findings.append(Finding(
                check="required_adapters", app=app_path.name,
                detail=(
                    f"adapters/__init__.py {source} declares '{name}' but "
                    f"adapters/{name}.py / adapters/{name}/ not found"
                ),
            ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 5: type_contract_drift
# ──────────────────────────────────────────────────────────────────────


def _annotation_name(node: ast.AST | None) -> str | None:
    """Resolve a single-name type annotation: `X` or `pkg.X` → 'X'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_name(node: ast.AST) -> str | None:
    """`@runtime_checkable` or `@typing.runtime_checkable` → 'runtime_checkable'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None


def _collect_protocols_in_file(py: Path) -> dict[str, dict[str, Any]]:
    """Return {ProtocolName: {"methods": set[str], "runtime_checkable": bool}}.

    A class counts as a Protocol if any base resolves to the bare name
    `Protocol` (covers both `class X(Protocol)` and
    `class Y(Other, Protocol)`). Method set excludes most dunders but
    keeps protocol-relevant ones (`__enter__`, `__exit__`, `__call__`,
    `__iter__`, `__aiter__`, `__anext__`).
    """
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    keep_dunder = {
        "__enter__", "__exit__", "__call__", "__iter__",
        "__aiter__", "__anext__", "__aenter__", "__aexit__",
        "__getitem__", "__setitem__", "__contains__", "__len__",
    }
    protocols: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        is_protocol = any(
            _annotation_name(b) == "Protocol" for b in node.bases
        )
        if not is_protocol:
            continue
        methods: set[str] = set()
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("__") and child.name not in keep_dunder:
                    continue
                methods.add(child.name)
        runtime_checkable = any(
            _decorator_name(d) == "runtime_checkable"
            for d in node.decorator_list
        )
        protocols[node.name] = {
            "methods": methods,
            "runtime_checkable": runtime_checkable,
        }
    return protocols


def _has_isinstance_test(tests_dir: Path, proto_name: str) -> bool:
    """True if any tests/test_*.py calls isinstance(_, proto_name)."""
    if not tests_dir.is_dir():
        return False
    for test_py in tests_dir.rglob("test_*.py"):
        try:
            tree = ast.parse(test_py.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for sub in ast.walk(tree):
            if not isinstance(sub, ast.Call):
                continue
            fn = sub.func
            fname = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else None
            )
            if fname != "isinstance" or len(sub.args) < 2:
                continue
            if _annotation_name(sub.args[1]) == proto_name:
                return True
    return False


def _called_class_name(node: ast.AST) -> str | None:
    """For `Foo(...)` or `pkg.Foo(...)` extract 'Foo'; else None."""
    if not isinstance(node, ast.Call):
        return None
    return _annotation_name(node.func)


def _find_implementer_classes(
    pkg: Path, proto_name: str
) -> set[tuple[Path, str]]:
    """Find classes claimed to implement `proto_name`.

    Two patterns:
      1. Typed assignment   `var: ProtoName = SomeClass(...)`
      2. Factory return     `def f(...) -> ProtoName: return SomeClass(...)`

    Bare name returns (`return SomeClass`) and instance returns of
    other variables are intentionally skipped — they would require
    flow-sensitive analysis to resolve cleanly.
    """
    out: set[tuple[Path, str]] = set()
    for py in pkg.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                if _annotation_name(node.annotation) != proto_name:
                    continue
                if node.value is None:
                    continue
                cls = _called_class_name(node.value)
                if cls and cls != proto_name:
                    out.add((py, cls))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _annotation_name(node.returns) != proto_name:
                    continue
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and sub.value is not None:
                        cls = _called_class_name(sub.value)
                        if cls and cls != proto_name:
                            out.add((py, cls))
    return out


def _class_methods(pkg: Path, class_name: str) -> set[str] | None:
    """Resolve a top-level class definition by name, return method names.

    Searches all .py files in pkg for `class <class_name>` at module
    scope. Returns None if not found (caller should treat as
    unresolvable and skip — conservative, no false positives from
    aliased / dynamic / cross-pkg classes).
    """
    for py in pkg.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                methods: set[str] = set()
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(child.name)
                return methods
    return None


def detect_type_contract_drift(apps: list[Path]) -> CheckResult:
    """Flag classes claiming a Protocol but missing one or more methods.

    Scope per app: protocols defined in `<pkg>/**/protocols.py` or
    `<pkg>/**/*_proto.py`. Implementer claims found via two AST
    patterns (typed assignment, factory return annotation).

    Skip rule: if a Protocol is decorated `@runtime_checkable` AND any
    `tests/test_*.py` actually calls `isinstance(_, <Protocol>)`, the
    runtime check is treated as the contract — static drift is no
    longer authoritative for that protocol.

    Severity: TYPE-001 (Medium). Findings list the missing method
    names so the maintainer can either add them or correct the type
    annotation.
    """
    result = CheckResult(name="type_contract_drift")
    for app_path in apps:
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue
        protocols: dict[str, dict[str, Any]] = {}
        for py in pkg.rglob("*.py"):
            if py.name == "protocols.py" or py.name.endswith("_proto.py"):
                protocols.update(_collect_protocols_in_file(py))
        if not protocols:
            continue
        tests_dir = app_path / "tests"
        for proto_name, meta in protocols.items():
            required = meta["methods"]
            if not required:
                continue
            if meta["runtime_checkable"] and _has_isinstance_test(
                tests_dir, proto_name
            ):
                result.notes.append(
                    f"{app_path.name}: {proto_name} runtime-checkable + "
                    f"isinstance test present — runtime check is the contract"
                )
                continue
            for impl_file, cls in _find_implementer_classes(pkg, proto_name):
                methods = _class_methods(pkg, cls)
                if methods is None:
                    continue
                missing = required - methods
                if not missing:
                    continue
                rel = impl_file.relative_to(app_path)
                result.findings.append(Finding(
                    check="type_contract_drift", app=app_path.name,
                    detail=(
                        f"{rel}: class '{cls}' claims '{proto_name}' but "
                        f"missing methods: {sorted(missing)}"
                    ),
                ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 6: plugin_loader_drift
# ──────────────────────────────────────────────────────────────────────


def _has_plugin_loader_call(pkg: Path) -> bool:
    """AST-scan package for importlib.metadata.entry_points() or
    pkg_resources.iter_entry_points() calls."""
    for py in pkg.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in (
                "entry_points", "iter_entry_points",
            ):
                return True
            if isinstance(func, ast.Name) and func.id in (
                "entry_points", "iter_entry_points",
            ):
                return True
    return False


def _resolve_entry_point_target(
    pkg_parent: Path, dotted_module: str, symbol: str,
) -> bool:
    """Check whether *module:symbol* resolves to a real AST-level name.

    *pkg_parent* is the directory that contains the top-level package
    (e.g. ``apps/my_app/src/``).  We convert the dotted module path to
    a filesystem path and then AST-walk the file looking for *symbol*
    as a class, function, or assignment target.
    """
    parts = dotted_module.split(".")
    mod_file = pkg_parent / Path(*parts).with_suffix(".py")
    mod_init = pkg_parent / Path(*parts) / "__init__.py"

    target_file: Path | None = None
    if mod_file.is_file():
        target_file = mod_file
    elif mod_init.is_file():
        target_file = mod_init
    if target_file is None:
        return False

    try:
        tree = ast.parse(target_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol:
                return True
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == symbol:
                    return True
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == symbol:
                return True
    return False


def check_plugin_loader_drift(apps: list[Path]) -> CheckResult:
    """Detect entry-point plugin loaders and flag unresolvable targets.

    Two-phase check per app:
      1. AST-scan for ``importlib.metadata.entry_points()`` or
         ``pkg_resources.iter_entry_points()`` calls — if absent, skip.
      2. Parse ``pyproject.toml`` ``[project.entry-points.*]`` groups and
         verify every ``module:attr`` target resolves to an importable
         symbol under the app's package directory.

    Severity: S2 (warn).
    """
    result = CheckResult(name="plugin_loader_drift")
    for app_path in apps:
        app_name = app_path.name
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue

        if not _has_plugin_loader_call(pkg):
            continue  # app doesn't use plugin loading — nothing to check

        pyproject = app_path / "pyproject.toml"
        if not pyproject.is_file():
            continue
        data = _load_toml(pyproject)
        entry_points = data.get("project", {}).get("entry-points", {})
        if not entry_points:
            result.notes.append(
                f"{app_name}: code calls entry_points() but pyproject has "
                f"no [project.entry-points] groups"
            )
            continue

        pkg_parent = pkg.parent  # e.g. apps/my_app/src/

        for group, entries in entry_points.items():
            if not isinstance(entries, dict):
                continue
            for ep_name, target_spec in entries.items():
                if not isinstance(target_spec, str) or ":" not in target_spec:
                    result.findings.append(Finding(
                        check="plugin_loader_drift", app=app_name,
                        detail=(
                            f"entry-point '{group}.{ep_name}' has malformed "
                            f"target '{target_spec}' (expected module:attr)"
                        ),
                    ))
                    continue
                mod_path, attr_name = target_spec.split(":", 1)
                if not _resolve_entry_point_target(pkg_parent, mod_path, attr_name):
                    result.findings.append(Finding(
                        check="plugin_loader_drift", app=app_name,
                        detail=(
                            f"entry-point '{group}.{ep_name}' target "
                            f"'{target_spec}' does not resolve to an "
                            f"importable symbol in src/"
                        ),
                    ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 7: public_api_not_reexported
# ──────────────────────────────────────────────────────────────────────


_BACKTICK_DOTTED_RE = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)`")


def _exported_names(init_py: Path) -> set[str] | None:
    """Return the public-API name set from a package ``__init__.py``.

    Returns the contents of ``__all__`` if defined, else all non-``_``
    names bound at module level (including re-imported names).
    Returns *None* if the file can't be parsed.
    """
    try:
        tree = ast.parse(init_py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None

    # Look for __all__ = [...]
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        names: set[str] = set()
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.add(elt.value)
                        return names

    # No __all__: collect all non-_ public names at top level
    public: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                public.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_"):
                    public.add(t.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if not name.startswith("_") and name != "*":
                    public.add(name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                if not name.startswith("_"):
                    public.add(name)
    return public


def _readme_documented_symbols(readme: Path, pkg_name: str) -> dict[str, str]:
    """Parse README for backticked ``pkg.module.symbol`` references.

    Returns ``{symbol_name: full_backtick_ref}`` so the finding can
    quote the exact README reference.
    """
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return {}

    symbols: dict[str, str] = {}
    for m in _BACKTICK_DOTTED_RE.finditer(text):
        ref = m.group(1)
        parts = ref.split(".")
        # Must start with the package name to be relevant
        if parts[0] != pkg_name:
            continue
        if len(parts) < 2:
            continue
        # The "symbol" is the leaf name
        symbol = parts[-1]
        symbols[symbol] = ref
    return symbols


def check_public_api_not_reexported(apps: list[Path]) -> CheckResult:
    """Flag README-documented symbols absent from __init__.py public surface.

    For each app:
      1. Build the exported name set from the top-level ``__init__.py``
         (``__all__`` if present, else all non-``_`` names).
      2. Scan ``README.md`` for backticked ``pkg.module.Symbol`` references.
      3. Flag any README-promised symbol that is not in the exported set.

    Rationale: README promises != import surface = doc drift.
    Severity: warn (S3) by default; treated as S2 under ``--strict``.
    """
    result = CheckResult(name="public_api_not_reexported")
    for app_path in apps:
        app_name = app_path.name
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue

        init_py = pkg / "__init__.py"
        if not init_py.is_file():
            continue

        exported = _exported_names(init_py)
        if exported is None:
            continue  # parse failure

        readme = app_path / "README.md"
        if not readme.is_file():
            continue

        pkg_name = pkg.name
        documented = _readme_documented_symbols(readme, pkg_name)
        if not documented:
            continue

        missing = {sym: ref for sym, ref in documented.items() if sym not in exported}
        for sym in sorted(missing):
            result.findings.append(Finding(
                check="public_api_not_reexported", app=app_name,
                detail=(
                    f"README documents `{missing[sym]}` but "
                    f"'{sym}' is not re-exported from "
                    f"{pkg_name}/__init__.py"
                ),
                severity="warn",
            ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Check 8: orphan_tests
# ──────────────────────────────────────────────────────────────────────


def _importable_modules(pkg: Path) -> set[str]:
    """Build the set of dotted module paths that absolute imports can target.

    Includes the package itself, every submodule, and every subpackage
    (the `__init__.py`-less form, since `from pkg.sub import x` resolves
    against `pkg.sub` whether `sub` is a module or a package).
    """
    importable: set[str] = {pkg.name}
    for py in pkg.rglob("*.py"):
        rel = py.relative_to(pkg.parent)
        parts = rel.with_suffix("").parts
        mod = ".".join(parts)
        importable.add(mod)
        if mod.endswith(".__init__"):
            importable.add(mod[: -len(".__init__")])
    return importable


def check_orphan_tests(apps: list[Path]) -> CheckResult:
    """Find test files whose package imports point to modules that no longer exist.

    Heuristic: AST-walk every `tests/test_*.py`, collect absolute imports that
    target the app's own package, and flag any whose dotted path doesn't
    resolve to a real module on disk. Relative imports (`from . import ...`)
    are ignored — they resolve against the test's own location, not src/.
    Single-name from-imports (`from pkg.mod import Symbol`) are validated at
    the module level only; whether `Symbol` is a class/function/submodule is
    ambiguous from AST alone, so we don't flag those.
    """
    result = CheckResult(name="orphan_tests")
    for app_path in apps:
        app_name = app_path.name
        pkg = _app_package_dir(app_path)
        if pkg is None:
            continue
        tests_dir = app_path / "tests"
        if not tests_dir.is_dir():
            continue

        pkg_name = pkg.name
        importable = _importable_modules(pkg)

        def _targets_pkg(modname: str) -> bool:
            return modname == pkg_name or modname.startswith(pkg_name + ".")

        for test_py in sorted(tests_dir.rglob("test_*.py")):
            try:
                tree = ast.parse(test_py.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue

            missing: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        if _targets_pkg(n.name) and n.name not in importable:
                            missing.add(n.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        continue
                    if node.module and _targets_pkg(node.module) and node.module not in importable:
                        missing.add(node.module)

            if missing:
                rel_display = test_py.relative_to(app_path)
                result.findings.append(Finding(
                    check="orphan_tests", app=app_name,
                    detail=f"{rel_display} — imports missing module(s): {', '.join(sorted(missing))}",
                ))
    return result


# ──────────────────────────────────────────────────────────────────────
# Report assembly
# ──────────────────────────────────────────────────────────────────────


ALL_CHECKS = (
    "schema_drift",
    "coverage_floor",
    "orphan_modules",
    "required_adapters",
    "type_contract_drift",
    "plugin_loader_drift",
    "public_api_not_reexported",
    "orphan_tests",
)


def run_audit(
    repo_root: Path,
    apps_dir: str,
    health_dir: Path,
    only: str | None,
    skip: set[str],
) -> dict[str, Any]:
    selected = [c for c in ALL_CHECKS if (only is None or c == only) and c not in skip]
    apps = discover_apps(repo_root, apps_dir)
    home = Path.home()
    results: list[CheckResult] = []

    for check in selected:
        if check == "schema_drift":
            results.append(check_schema_drift(apps, home))
        elif check == "coverage_floor":
            results.append(check_coverage_floor(apps, health_dir))
        elif check == "orphan_modules":
            results.append(check_orphan_modules(apps))
        elif check == "required_adapters":
            results.append(detect_required_adapters(apps))
        elif check == "type_contract_drift":
            results.append(detect_type_contract_drift(apps))
        elif check == "plugin_loader_drift":
            results.append(check_plugin_loader_drift(apps))
        elif check == "public_api_not_reexported":
            results.append(check_public_api_not_reexported(apps))
        elif check == "orphan_tests":
            results.append(check_orphan_tests(apps))

    all_findings: list[Finding] = []
    all_notes: list[str] = []
    for r in results:
        all_findings.extend(r.findings)
        all_notes.extend(f"{r.name}: {n}" for n in r.notes)

    return {
        "repo_root": str(repo_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apps_scanned": len(apps),
        "checks": [r.name for r in results],
        "findings": [f.to_dict() for f in all_findings],
        "notes": all_notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    repo_name = Path(report["repo_root"]).name or report["repo_root"]
    findings = report["findings"]
    error_count = sum(1 for f in findings if f["severity"] == "error")
    warn_count = sum(1 for f in findings if f["severity"] == "warn")

    lines = [
        f"# Monorepo audit — {repo_name}",
        f"_Generated {report['generated_at']}_",
        "",
        "## Summary",
        f"- {len(report['checks'])} checks ran: {', '.join(report['checks'])}",
        f"- {len(findings)} findings ({error_count} error, {warn_count} warn)",
        f"- {report['apps_scanned']} apps scanned",
        "",
    ]

    if not findings:
        lines.append("✅ No findings. Repo is clean.")
    else:
        # Group findings by check
        by_check: dict[str, list[dict]] = {}
        for f in findings:
            by_check.setdefault(f["check"], []).append(f)
        for check_name in report["checks"]:
            items = by_check.get(check_name, [])
            lines.append(f"## {check_name}")
            if not items:
                lines.append("_No findings._")
            else:
                for f in items:
                    sev = f["severity"]
                    marker = "🔴" if sev == "error" else "⚠️"
                    lines.append(f"- {marker} **{f['app']}** [{sev}]: {f['detail']}")
            lines.append("")

    notes = report.get("notes", [])
    if notes:
        lines.append("## Notes (skipped / advisory)")
        for n in notes:
            lines.append(f"- {n}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="monorepo-audit",
        description="Schema-drift / coverage-floor / orphan-module audit for a Python monorepo.",
    )
    p.add_argument("--repo-root", type=Path, default=Path.cwd(),
                   help="Repo root (default: CWD).")
    p.add_argument("--apps-dir", default="apps",
                   help="Subproject directory name (default: apps).")
    p.add_argument("--health-dir", type=Path, default=None,
                   help="Where release_check JSONs live (default: <repo>/artifacts/health).")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of markdown.")
    p.add_argument("--only", choices=ALL_CHECKS, default=None,
                   help="Run only one check.")
    p.add_argument("--skip", action="append", choices=ALL_CHECKS, default=[],
                   help="Skip a check (repeatable).")
    p.add_argument("--strict", action="store_true",
                   help="Exit non-zero on any finding. Default exits non-zero "
                        "only on `error`-severity findings (warns are advisory).")
    args = p.parse_args(argv)

    repo_root = args.repo_root.resolve()
    health_dir = args.health_dir or (repo_root / "artifacts" / "health")

    report = run_audit(
        repo_root=repo_root,
        apps_dir=args.apps_dir,
        health_dir=health_dir,
        only=args.only,
        skip=set(args.skip),
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report))

    findings = report["findings"]
    if args.strict:
        return 1 if findings else 0
    has_error = any(f["severity"] == "error" for f in findings)
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
