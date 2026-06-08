"""Output-filename helpers shared by the renderers.

Two concerns that were duplicated across render/dashboard/runbook:
* strip a known artifact suffix (``foo.runbookspec.yaml`` -> ``foo``), and
* constrain an untrusted name to a path-safe charset (``metadata.name`` is attacker-influenced and
  assemble renders BEFORE it validates, so the filename derivation must self-protect against traversal).
"""
from __future__ import annotations

import re
from pathlib import Path


def strip_known_suffix(name: str, suffixes: tuple[str, ...]) -> str:
    for suff in suffixes:
        if name.endswith(suff):
            return name[: -len(suff)]
    return name


def safe_basename(name: str, fallback: str = "alert") -> str:
    """Strip path components and constrain to a safe charset so a hostile name can't escape the
    target dir (path traversal)."""
    base = re.sub(r"[^A-Za-z0-9._-]", "-", Path(str(name)).name).strip("._-")
    return base or fallback
