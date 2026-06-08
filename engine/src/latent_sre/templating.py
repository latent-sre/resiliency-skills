"""Shared deterministic-rendering primitives: a sandboxed Jinja2 environment, the fail-loud
``REPLACE_ME__`` sentinel, and a control-char ``sanitize`` filter.

Pulled out of ``render.py`` so the alert-adapter module isn't a hub that ``scaffold``, ``runbook`` and
``dashboard`` all import rendering helpers from. Security posture is unchanged: the environment is
sandboxed (blocks template-level attacks) with autoescape OFF because outputs are config/markdown,
not HTML — per-value escaping is done with ``tojson`` (JSON/YAML) or ``sanitize`` (line/list text).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sanitize(v: object) -> str:
    """Collapse newlines/control chars so an untrusted value can't inject new lines/stanzas into a
    line-oriented config (Splunk .conf, Wavefront) or a Markdown list. Length-capped."""
    return _CONTROL.sub(" ", str(v))[:2000]


def sentinel(field: str) -> str:
    """Org-specific connection field placeholder: an accidental apply FAILS LOUD instead of silently
    targeting the wrong system."""
    return f"REPLACE_ME__{field}"


def make_sandbox_env(template_dir: Path) -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tojson"] = lambda v: json.dumps(v)
    env.filters["sanitize"] = sanitize
    return env
