"""Schema validation (jsonschema Draft 2020-12).

Schemas use ``additionalProperties: false`` + enumerated properties, so unknown keys are rejected —
this is how the *positive field allow-list* (review item F4) is enforced. Required governance fields
(provenance, ownership, confidence, needs-human-review) live in each schema's ``required``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAMLError

from . import SCHEMA_API_VERSION, registry, yamlio
from .paths import data_dir

SCHEMA_DIR = data_dir("schemas")
_API_RE = re.compile(r"^sre\.latent-sre/v(\d+)$")
_ENGINE_API_MAJOR = int(_API_RE.match(SCHEMA_API_VERSION).group(1))


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

    av = doc.get("apiVersion")
    if isinstance(av, str):  # enforce the fleet contract version, not just the schema's per-field const
        m = _API_RE.match(av)
        if not m:
            return [f"{path}: unrecognized apiVersion {av!r} (expected sre.latent-sre/vN)"]
        if int(m.group(1)) > _ENGINE_API_MAJOR:
            return [f"{path}: apiVersion {av} is newer than this engine supports "
                    f"(max v{_ENGINE_API_MAJOR}) — upgrade latent-sre"]

    kind = doc.get("kind")
    if kind in registry.CONTROL_KINDS:
        return []  # control-plane (orchestration) artifact — no data schema by design
    spec = registry.BY_KIND.get(kind) if isinstance(kind, str) else None
    if spec is None:
        return [f"{path}: unknown or missing kind={kind!r}"]
    schema_path = schema_dir / f"{spec.schema}.schema.json"
    if not schema_path.is_file():
        return [f"{path}: schema {spec.schema}.schema.json not found in {schema_dir}"]

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
