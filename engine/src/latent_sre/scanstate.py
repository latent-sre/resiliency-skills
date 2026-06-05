"""Resumable scan checkpoint (review item F6).

No hash-chaining: the security guarantee comes from CI re-running redact/secret-scan unconditionally
on every publish, not from a tamper-evident chain. This is purely a resume/skip optimization keyed on
(skill, input commit SHA, skill+engine version).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import yamlio


def _load(path: Path) -> dict[str, Any]:
    if Path(path).is_file():
        return yamlio.load(path) or {}
    return {"apiVersion": "sre.latent-sre/v1", "kind": "ScanState", "skills": {}}


def get(path: str | Path, skill: str) -> dict | None:
    return _load(Path(path)).get("skills", {}).get(skill)


def is_done(path: str | Path, skill: str, commit: str, engine_version: str) -> bool:
    rec = get(path, skill)
    return bool(rec and rec.get("status") == "done"
               and rec.get("inputCommit") == commit
               and rec.get("engineVersion") == engine_version)


def mark(path: str | Path, skill: str, commit: str, engine_version: str,
         output: str, content_hash: str, status: str = "done") -> None:
    p = Path(path)
    state = _load(p)
    state.setdefault("skills", {})[skill] = {
        "status": status,
        "inputCommit": commit,
        "engineVersion": engine_version,
        "output": output,
        "contentHash": content_hash,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    yamlio.dump(state, p)
