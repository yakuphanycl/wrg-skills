from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = ROOT / "skills"
REQUIRED = ("name", "description")
FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, [f"{path}: missing opening frontmatter marker"]

    try:
        end = next(index for index, line in enumerate(lines[1:], start=2) if line.strip() == "---")
    except StopIteration:
        return {}, [f"{path}: missing closing frontmatter marker"]

    data: dict[str, str] = {}
    errors: list[str] = []
    for line_no, raw in enumerate(lines[1 : end - 1], start=2):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = FIELD_RE.match(line)
        if match is None:
            errors.append(f"{path}:{line_no}: unsupported frontmatter line: {raw!r}")
            continue
        key, value = match.groups()
        data[key] = value.strip().strip("\"'")

    return data, errors


def main() -> int:
    errors: list[str] = []
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        errors.append("skills/*/SKILL.md: no skills found")

    for skill_file in skill_files:
        skill_name = skill_file.parent.name
        fields, parse_errors = frontmatter(skill_file)
        errors.extend(parse_errors)

        for key in REQUIRED:
            if not fields.get(key):
                errors.append(f"{skill_file}: missing required frontmatter field: {key}")

        declared_name = fields.get("name")
        if declared_name and declared_name != skill_name:
            errors.append(f"{skill_file}: name field {declared_name!r} must match directory {skill_name!r}")

    if errors:
        print("SKILL.md frontmatter validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(skill_files)} skill frontmatter file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
