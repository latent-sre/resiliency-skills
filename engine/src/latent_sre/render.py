"""Deterministically render a neutral AlertIntent into per-tool adapter configs.

Security (review items M2/F7): the intent is *untrusted* (service/metric names can be
attacker-influenced). So:
* Jinja2 runs in a ``SandboxedEnvironment`` with ``autoescape`` for text targets.
* JSON targets serialize values via ``tojson`` (json.dumps) — never raw string interpolation —
  so an attacker string can't break out of the JSON structure.
Connection-critical fields that need org-specific config emit ``REPLACE_ME__<context>`` sentinels
so an accidental apply FAILS LOUD instead of silently targeting the wrong system (review item S6).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from . import yamlio
from .paths import data_dir

ADAPTER_DIR = data_dir("templates") / "adapters"
TARGETS = ["grafana", "prometheus", "splunk", "wavefront", "appdynamics", "thousandeyes"]

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize(v: object) -> str:
    """Collapse newlines/control chars so an untrusted value can't inject new lines/stanzas into a
    line-oriented config (Splunk .conf, Wavefront). Length-capped."""
    return _CONTROL.sub(" ", str(v))[:2000]


def _env(adapter_dir: Path) -> SandboxedEnvironment:
    # Sandboxed (blocks template-level attacks); autoescape OFF because outputs are config formats,
    # not HTML — per-value escaping is done with `tojson` (JSON/YAML) or `sanitize` (line configs).
    env = SandboxedEnvironment(
        loader=FileSystemLoader(str(adapter_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tojson"] = lambda v: json.dumps(v)
    env.filters["sanitize"] = _sanitize
    return env


def sentinel(field: str) -> str:
    return f"REPLACE_ME__{field}"


def render_intent(intent: dict, target: str, adapter_dir: Path = ADAPTER_DIR) -> str:
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}")
    env = _env(adapter_dir)
    tmpl = env.get_template(f"{target}.j2")
    spec = intent.get("spec", {})
    meta = intent.get("metadata", {})
    signal = spec.get("signal", {})
    # org-specific connection fields → sentinel when absent (fail-loud)
    ctx = {
        "name": meta.get("name", sentinel("name")),
        "service": meta.get("service", sentinel("service")),
        "ownership": meta.get("ownership", "unknown"),
        "query": signal.get("query") or sentinel("query"),
        "source": signal.get("source", "unknown"),
        "index": signal.get("index") or sentinel("splunk_index"),
        "metric": signal.get("metric") or sentinel("wavefront_metric"),
        "app": signal.get("app") or sentinel("appd_application"),
        "comparator": spec.get("condition", {}).get("comparator", ">"),
        "threshold": spec.get("condition", {}).get("threshold", sentinel("threshold")),
        "window": spec.get("condition", {}).get("window", "5m"),
        "severity": spec.get("severity", "sev3"),
        "for": spec.get("for", "10m"),
        "runbook": spec.get("links", {}).get("runbook", ""),
        "summary": spec.get("annotations", {}).get("summary", ""),
        "unverified": True,
    }
    return tmpl.render(**ctx)


def render_file(intent_path: str | Path, out_dir: str | Path, targets: list[str] | None = None,
                adapter_dir: Path = ADAPTER_DIR) -> list[Path]:
    intent = yamlio.load(intent_path)
    targets = targets or intent.get("spec", {}).get("renderTargets", TARGETS)
    out_dir = Path(out_dir)
    written: list[Path] = []
    name = intent.get("metadata", {}).get("name", "alert")
    for t in targets:
        rendered = render_intent(intent, t, adapter_dir)
        ext = "json" if t in ("appdynamics", "thousandeyes") else "yaml" if t in ("grafana", "prometheus") else "conf"
        dest = out_dir / t / f"{name}.{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        written.append(dest)
    return written
