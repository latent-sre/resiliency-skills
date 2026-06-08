"""Render a dependency graph as Mermaid. Node labels come from untrusted manifests, so they are
sanitized to an inert charset to avoid injecting active content into the rendered README (review M2/N4)."""
from __future__ import annotations

import re
from pathlib import Path

from . import yamlio

_SAFE = re.compile(r"[^A-Za-z0-9_.\- ]")


def _label(s: str) -> str:
    return _SAFE.sub("", str(s))[:60] or "unknown"


def _base_id(s: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", str(s))[:40]


def _id_allocator():
    """Map each distinct name to a unique node id. Sanitizing to an inert charset and truncating to 40
    chars means distinct names (``redis.cache`` vs ``redis-cache``, or two names sharing a 40-char
    prefix) can collide to the same id and silently merge into one graph node — so disambiguate
    collisions with a numeric suffix while keeping the same name → same id (repeated edges connect)."""
    ids: dict[str, str] = {}
    used: set[str] = set()

    def node_id(name) -> str:
        key = str(name)
        if key in ids:
            return ids[key]
        base = _base_id(key)
        candidate, n = base, 2
        while candidate in used:
            candidate, n = f"{base}_{n}", n + 1
        ids[key] = candidate
        used.add(candidate)
        return candidate

    return node_id


def from_dependencies(path: str | Path) -> str:
    doc = yamlio.load(path) or {}
    svc = doc.get("service", "service")
    node_id = _id_allocator()
    svc_id = node_id(svc)
    lines = ["```mermaid", "graph LR", f"  {svc_id}[{_label(svc)}]"]
    for dep in doc.get("dependencies", []) or []:
        name = dep.get("name", "dep")
        direction = dep.get("direction", "downstream")
        edge = "-->" if direction == "downstream" else "-.->"
        lines.append(f"  {svc_id} {edge} {node_id(name)}[{_label(name)}]")
    lines.append("```")
    return "\n".join(lines)
