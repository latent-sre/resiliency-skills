"""Per-service scan plan: ties app-names (fan-out discovery) to the canonical pipeline (ordered
skills), annotated with resume status from an optional scan-state checkpoint.

This is the deterministic orchestration surface the sre-analyst follows: which services exist, which
skills run in what order, what is already done, and whether the monorepo fan-out exceeds the cap
(`requiresHumanConfirm`) so automation stops and a human decides — never mass-create.
"""
from __future__ import annotations

from pathlib import Path

from . import SCHEMA_API_VERSION, appnames, scanstate, yamlio
from .paths import data_file


def load_pipeline(path: str | Path | None = None) -> dict:
    return yamlio.load(Path(path) if path else data_file("pipeline.yaml")) or {}


def _ordered_skills(pipe: dict) -> list[tuple[str, str]]:
    """Flatten phases → [(phase, skill), ...] in pipeline order."""
    out: list[tuple[str, str]] = []
    for phase in pipe.get("phases", []) or []:
        for skill in phase.get("skills", []) or []:
            out.append((phase.get("name", ""), skill))
    return out


def make_plan(repo: str | Path, pipeline_path: str | Path | None = None,
              scan_state_path: str | Path | None = None) -> dict:
    disc = appnames.discover(repo)
    ordered = _ordered_skills(load_pipeline(pipeline_path))

    services = []
    for svc in disc["services"]:
        steps = []
        for phase, skill in ordered:
            status = "pending"
            if scan_state_path:
                rec = scanstate.get(scan_state_path, svc, skill)  # per-service resume, not global
                if rec:
                    status = rec.get("status", "pending")
            steps.append({"phase": phase, "skill": skill, "status": status})
        services.append({"service": svc, "skills": steps})

    return {
        "apiVersion": SCHEMA_API_VERSION,
        "kind": "ScanPlan",
        "repo": str(repo),
        "fanout": {
            "total": disc["total"],
            "cap": appnames.FANOUT_CAP,
            "truncated": disc["truncated"],
        },
        "requiresHumanConfirm": disc["requiresHumanConfirm"],
        "services": services,
    }
