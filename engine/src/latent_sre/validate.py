"""Schema validation (jsonschema Draft 2020-12).

Schemas use ``additionalProperties: false`` + enumerated properties, so unknown keys are rejected —
this is how the *positive field allow-list* (review item F4) is enforced. Required governance fields
(provenance, ownership, confidence, needs-human-review) live in each schema's ``required``.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAMLError

from . import yamlio
from .paths import data_dir

SCHEMA_DIR = data_dir("schemas")


def _schema_for(doc: dict, schema_dir: Path) -> Path | None:
    """Map an artifact to its schema by `kind` (preferred) or by filename stem."""
    kind = (doc or {}).get("kind")
    if kind:
        cand = schema_dir / f"{_kebab(kind)}.schema.json"
        if cand.is_file():
            return cand
    return None


def _kebab(s: str) -> str:
    out = []
    for i, ch in enumerate(s):
        if ch.isupper() and i and not s[i - 1].isupper():
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


def validate_file(path: str | Path, schema_dir: Path = SCHEMA_DIR) -> list[str]:
    path = Path(path)
    # Untrusted input: a malformed or non-mapping artifact must yield a clean per-file problem,
    # never an exception that aborts the whole tree scan (validate is a fail-closed gate).
    try:
        if path.suffix in (".yaml", ".yml"):
            doc = yamlio.load(path)
        else:
            doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, YAMLError) as e:
        return [f"{path}: could not parse: {e}"]
    if not isinstance(doc, dict):
        return [f"{path}: top-level document is not a mapping ({type(doc).__name__})"]

    schema_path = _schema_for(doc, schema_dir)
    if schema_path is None:
        return [f"{path}: no schema found for kind={doc.get('kind')!r}"]

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return [f"{path}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def validate_tree(root: str | Path, schema_dir: Path = SCHEMA_DIR) -> list[str]:
    root = Path(root)
    problems: list[str] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in (".yaml", ".yml") and ".git" not in p.parts:
            problems.extend(validate_file(p, schema_dir))
    return problems
