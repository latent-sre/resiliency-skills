"""Render a dependency graph as Mermaid. Node labels come from untrusted manifests, so they are
sanitized to an inert charset to avoid injecting active content into the rendered README (review M2/N4)."""
from __future__ import annotations

import re
from pathlib import Path

from . import yamlio

_SAFE = re.compile(r"[^A-Za-z0-9_.\- ]")


def _label(s: str) -> str:
    return _SAFE.sub("", str(s))[:60] or "unknown"


def _node_id(s: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", str(s))[:40]


def from_dependencies(path: str | Path) -> str:
    doc = yamlio.load(path) or {}
    svc = doc.get("service", "service")
    lines = ["```mermaid", "graph LR", f"  {_node_id(svc)}[{_label(svc)}]"]
    for dep in doc.get("dependencies", []) or []:
        name = dep.get("name", "dep")
        direction = dep.get("direction", "downstream")
        edge = "-->" if direction == "downstream" else "-.->"
        lines.append(f"  {_node_id(svc)} {edge} {_node_id(name)}[{_label(name)}]")
    lines.append("```")
    return "\n".join(lines)
