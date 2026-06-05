"""Discover deployable services in a (possibly mono-) repo → list of service names.

Monorepos fan out to one SRE-<service> per service; fan-out is CAPPED and above the cap requires
explicit human confirmation, so a malicious manifest with thousands of fabricated `applications:`
entries cannot drive mass repo creation (review item N2). Service names are untrusted strings.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import yamlio

FANOUT_CAP = 20
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.\-]")


def _clean(name: str) -> str:
    return _SAFE_NAME.sub("-", str(name)).strip("-")[:63] or "unnamed"


def discover(repo: str | Path) -> dict:
    repo = Path(repo)
    names: list[str] = []

    # PCF/Tanzu application manifests
    for mf in list(repo.rglob("manifest.yml")) + list(repo.rglob("manifest.yaml")):
        try:
            doc = yamlio.load(mf) or {}
        except Exception:
            continue
        for app in doc.get("applications", []) or []:
            if isinstance(app, dict) and app.get("name"):
                names.append(_clean(app["name"]))

    # Fallback: repo name when nothing else is found
    if not names:
        names.append(_clean(repo.resolve().name))

    unique = sorted(dict.fromkeys(names))
    return {
        "services": unique[:FANOUT_CAP],
        "truncated": len(unique) > FANOUT_CAP,
        "total": len(unique),
        "requiresHumanConfirm": len(unique) > FANOUT_CAP,
    }
