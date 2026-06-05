"""Normalized content hashing for clobber-protection (never overwrite human edits).

The hash is computed over canonical YAML (sorted keys) with volatile provenance fields stripped, so
cosmetic reordering or a new scan timestamp does not look like a human edit.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import yamlio

_VOLATILE = {"scanDate", "modelVersion", "engineVersion"}


def _strip_volatile(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _VOLATILE}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


def content_hash(path: str | Path) -> str:
    p = Path(path)
    if p.suffix in (".yaml", ".yml"):
        canonical = yamlio.dumps(_strip_volatile(yamlio.load(p)))
    else:
        canonical = p.read_text(encoding="utf-8")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_human_edited(path: str | Path, recorded_hash: str) -> bool:
    """True if the live file diverges from the last AI-written hash → route to .proposed/."""
    return content_hash(path) != recorded_hash
