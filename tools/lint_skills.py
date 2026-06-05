#!/usr/bin/env python3
"""Lint .github/skills/*/SKILL.md frontmatter.

Rules (kept deliberately small — the schema/engine do the heavy lifting):
* every skill dir has a SKILL.md with a YAML frontmatter block,
* `name` is present and equals the directory name,
* `description` is present and 10..1024 chars.

Exit non-zero on any problem so CI blocks. No third-party deps (stdlib only).
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".github" / "skills"


def _frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML frontmatter reader (stdlib only). Handles inline scalars and block scalars
    (`>`, `>-`, `|`, `|-`) so multi-line descriptions parse correctly."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    lines = text[3:end].splitlines()
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.strip().startswith("#") or line[:1].isspace() or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val and val[0] in "|>":  # block scalar: gather indented continuation lines
            fold = val[0] == ">"
            block: list[str] = []
            while i < len(lines) and (lines[i][:1].isspace() or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            out[key] = (" ".join(block) if fold else "\n".join(block)).strip()
        else:
            out[key] = val.strip("'\"")
    return out


def main() -> int:
    if not SKILLS.is_dir():
        print("lint-skills: no .github/skills/ yet — ok")
        return 0
    problems: list[str] = []
    skill_dirs = [d for d in SKILLS.iterdir() if d.is_dir()]
    for d in sorted(skill_dirs):
        md = d / "SKILL.md"
        if not md.is_file():
            problems.append(f"{d.name}: missing SKILL.md")
            continue
        fm = _frontmatter(md.read_text(encoding="utf-8"))
        if fm.get("name") != d.name:
            problems.append(f"{d.name}: frontmatter name={fm.get('name')!r} must equal dir name")
        desc = fm.get("description", "")
        if not (10 <= len(desc) <= 1024):
            problems.append(f"{d.name}: description must be 10..1024 chars (got {len(desc)})")

    if problems:
        print(f"lint-skills: {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"lint-skills: ok ({len(skill_dirs)} skill(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
