"""Render a neutral Dashboard spec into a Grafana dashboard JSON.

Built by constructing a Python dict and ``json.dumps``-ing it (rather than a JSON template), so the
output is valid JSON by construction and any attacker-controlled panel title/query is escaped — it
cannot break out of the structure. The org-specific datasource is a ``REPLACE_ME__`` sentinel so an
accidental import fails loud instead of binding to the wrong datasource.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import yamlio
from .render import sentinel

_SPEC_SUFFIXES = (".dashboard.yaml", ".dashboard.yml", ".yaml", ".yml")


def render_dashboard(spec: dict) -> str:
    s = spec.get("spec", {})
    datasource = sentinel("grafana_datasource")
    panels = []
    for i, p in enumerate(s.get("panels", []), start=1):
        sig = p.get("signal", {}) or {}
        expr = sig.get("query") or sig.get("metric") or sentinel("dashboard_query")
        panels.append({
            "id": i,
            "title": p.get("title", f"panel-{i}"),
            "type": p.get("type", "timeseries"),
            "datasource": datasource,
            "fieldConfig": {"defaults": {"unit": p.get("unit", "short")}, "overrides": []},
            "targets": [{"refId": "A", "datasource": datasource, "expr": expr}],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": (i - 1) * 8},
        })
    dashboard = {
        "title": s.get("title", spec.get("service", "service")),
        "tags": ["sre", "ai-drafted", "needs-human-review"],
        "timezone": "",
        "schemaVersion": 39,
        "version": 0,
        "editable": True,
        "refresh": "",
        "annotations": {"list": []},
        "templating": {"list": []},
        "panels": panels,
    }
    return json.dumps(dashboard, indent=2)


def _basename(name: str) -> str:
    for suff in _SPEC_SUFFIXES:
        if name.endswith(suff):
            return name[: -len(suff)]
    return name


def render_dashboard_file(spec_path: str | Path, out_dir: str | Path) -> Path:
    spec = yamlio.load(spec_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{_basename(Path(spec_path).name)}.json"
    dest.write_text(render_dashboard(spec), encoding="utf-8")
    return dest
