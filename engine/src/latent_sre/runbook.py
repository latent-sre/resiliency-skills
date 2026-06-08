"""Render a neutral RunbookSpec into a Markdown runbook.

Deterministic and sandboxed (same posture as the alert adapters): the spec's free-text steps are
untrusted-ish, so each interpolated value goes through `sanitize` (collapse newlines/control chars)
to keep one step per Markdown list item — a step cannot inject new headings or list structure.
"""
from __future__ import annotations

from pathlib import Path

from . import __version__, yamlio
from .paths import data_dir
from .templating import make_sandbox_env

TEMPLATE_DIR = data_dir("templates")
_SPEC_SUFFIXES = (".runbookspec.yaml", ".runbookspec.yml", ".yaml", ".yml")


def render_runbook(spec: dict) -> str:
    s = spec.get("spec", {})
    prov = spec.get("provenance", {})
    links = s.get("links", {})
    env = make_sandbox_env(TEMPLATE_DIR)
    tmpl = env.get_template("runbook.md.j2")
    return tmpl.render(
        title=s.get("title", "Untitled"),
        service=spec.get("service", "unknown"),
        severity=s.get("severity", "sev3"),
        summary=s.get("summary", ""),
        signals=s.get("signals", []),
        triage=s.get("triage", []),
        mitigation=s.get("mitigation", []),
        rollback=s.get("rollback", []),
        escalation_team=(s.get("escalation") or {}).get("team", "unknown"),
        dashboard=links.get("dashboard"),
        slo=links.get("slo"),
        alert=links.get("alert"),
        confidence=spec.get("confidence", "low"),
        ownership=spec.get("ownership", "unknown"),
        engine_version=__version__,
        provenance_skill=prov.get("skill", "unknown"),
        provenance_repo=prov.get("repo", "unknown"),
        provenance_commit=prov.get("commit", "unknown"),
    )


def _basename(name: str) -> str:
    for suff in _SPEC_SUFFIXES:
        if name.endswith(suff):
            return name[: -len(suff)]
    return name


def render_runbook_file(spec_path: str | Path, out_dir: str | Path) -> Path:
    spec = yamlio.load(spec_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{_basename(Path(spec_path).name)}.md"
    dest.write_text(render_runbook(spec), encoding="utf-8")
    return dest
