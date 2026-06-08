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

import re
from pathlib import Path

from . import yamlio
from .paths import data_dir
from .templating import make_sandbox_env, sentinel

ADAPTER_DIR = data_dir("templates") / "adapters"
TARGETS = ["grafana", "prometheus", "splunk", "wavefront", "appdynamics", "thousandeyes"]

_SEV_RANK = {"sev1": 1, "sev2": 2, "sev3": 3}
TIER_SEVERITY_FLOOR = {"tier0": "sev1", "tier1": "sev2", "tier2": "sev3", "tier3": "sev3"}


def _effective_severity(declared: str, tier: str | None) -> str:
    """A service's criticality tier sets a severity FLOOR (deterministic, not LLM-dependent); the
    floor can only RAISE severity to match the tier, never lower the author's declared severity."""
    floor = TIER_SEVERITY_FLOOR.get(tier or "")
    if not floor:
        return declared
    return declared if _SEV_RANK.get(declared, 3) <= _SEV_RANK.get(floor, 3) else floor


def render_intent(intent: dict, target: str, adapter_dir: Path = ADAPTER_DIR, tier: str | None = None) -> str:
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}")
    env = make_sandbox_env(adapter_dir)
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
        "severity": _effective_severity(spec.get("severity", "sev3"), tier),
        "severity_class": spec.get("class", "symptom"),
        "occurrences": spec.get("condition", {}).get("occurrences"),
        "for": spec.get("for", "10m"),
        "runbook": spec.get("links", {}).get("runbook", ""),
        "summary": spec.get("annotations", {}).get("summary", ""),
        "unverified": True,
    }
    return tmpl.render(**ctx)


def _safe_basename(name: str, fallback: str = "alert") -> str:
    """The output filename derives from untrusted artifact content (`metadata.name`); strip any path
    components and constrain to a safe charset so a hostile name can't escape the target dir
    (path traversal — see render_file). The schema constrains name, but assemble renders before it
    validates, so this must self-protect."""
    base = re.sub(r"[^A-Za-z0-9._-]", "-", Path(str(name)).name).strip("._-")
    return base or fallback


def render_file(intent_path: str | Path, out_dir: str | Path, targets: list[str] | None = None,
                adapter_dir: Path = ADAPTER_DIR, tier: str | None = None) -> list[Path]:
    intent = yamlio.load(intent_path)
    if targets is None:  # an explicit empty renderTargets means "render nothing"; only None falls back
        targets = intent.get("spec", {}).get("renderTargets", TARGETS)
    out_dir = Path(out_dir)
    written: list[Path] = []
    name = _safe_basename(intent.get("metadata", {}).get("name", "alert"))
    for t in targets:
        if t not in TARGETS:
            continue  # unknown target from an (untrusted) artifact's renderTargets — skip rather than
                      # crash; schema validation of the artifact flags it (the CLI validates --targets).
        rendered = render_intent(intent, t, adapter_dir, tier=tier)
        ext = "json" if t in ("appdynamics", "thousandeyes") else "yaml" if t in ("grafana", "prometheus") else "conf"
        dest = out_dir / t / f"{name}.{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        written.append(dest)
    return written
