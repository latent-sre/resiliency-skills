"""Resumable scan checkpoint (review item F6).

Keyed on (service, skill, input commit, skill+engine version) so resume is correct under monorepo
fan-out: marking a skill done for one service must NOT report it done for an unscanned sibling.

No hash-chaining: the security guarantee comes from CI re-running redact/secret-scan unconditionally
on every publish, not from a tamper-evident chain. This is purely a resume/skip optimization.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import SCHEMA_API_VERSION, yamlio


def _load(path: Path) -> dict[str, Any]:
    if Path(path).is_file():
        return yamlio.load(path) or {}
    return {"apiVersion": SCHEMA_API_VERSION, "kind": "ScanState", "services": {}}


def get(path: str | Path, service: str, skill: str) -> dict | None:
    return _load(Path(path)).get("services", {}).get(service, {}).get("skills", {}).get(skill)


def is_done(path: str | Path, service: str, skill: str, commit: str, engine_version: str) -> bool:
    rec = get(path, service, skill)
    return bool(rec and rec.get("status") == "done"
               and rec.get("inputCommit") == commit
               and rec.get("engineVersion") == engine_version)


def mark(path: str | Path, service: str, skill: str, commit: str, engine_version: str,
         output: str, content_hash: str, status: str = "done") -> None:
    p = Path(path)
    state = _load(p)
    skills = state.setdefault("services", {}).setdefault(service, {}).setdefault("skills", {})
    skills[skill] = {
        "status": status,
        "inputCommit": commit,
        "engineVersion": engine_version,
        "output": output,
        "contentHash": content_hash,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    yamlio.dump(state, p)
