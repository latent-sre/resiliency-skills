"""Lay down a complete, hardened SRE-<service> skeleton (review items S3/F13).

The generated repo:
* vendors the exact schema set + engine version it was born with into ``.sre/`` so its own CI
  validates against the contract that generated it, decoupled from this repo's main;
* ships its own least-privilege CI (validate vs vendored schemas + fail-closed redact);
* ships CODEOWNERS + a PR template so AI-drafted updates cannot merge unreviewed;
* ships a Backstage ``catalog-info.yaml`` and a provenance-stamped README banner.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import SCHEMA_API_VERSION, __version__
from .paths import data_dir
from .render import make_sandbox_env

SCHEMA_DIR = data_dir("schemas")
TEMPLATE_DIR = data_dir("templates")

_DIRS = [
    "metadata", "slos", "alerts/intent", "dashboards", "runbooks", "diagrams",
    ".proposed", ".sre/schemas", ".provenance", ".github/workflows",
]

# template (relative to templates/) -> destination (relative to the new repo root)
_FILE_TEMPLATES = {
    "sre-repo/README.md.j2": "README.md",
    "sre-repo/catalog-info.yaml.j2": "catalog-info.yaml",
    "sre-repo/CODEOWNERS.j2": ".github/CODEOWNERS",
    "sre-repo/pull_request_template.md.j2": ".github/pull_request_template.md",
    "sre-repo/workflows-validate.yml.j2": ".github/workflows/validate.yml",
    "sre-repo/gitignore.j2": ".gitignore",
}


def clean_service(s: str) -> str:
    """Service names are untrusted (may come from a hostile manifest). Constrain to a safe charset."""
    return re.sub(r"[^A-Za-z0-9_.-]", "-", str(s)).strip("-")[:63] or "service"


def scaffold(out: str | Path, service: str, schema_dir: Path = SCHEMA_DIR) -> Path:
    service = clean_service(service)
    root = Path(out)
    for d in _DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    # vendor pinned schemas + engine version
    if schema_dir.is_dir():
        for s in schema_dir.glob("*.schema.json"):
            shutil.copy2(s, root / ".sre" / "schemas" / s.name)
    (root / ".sre" / "version").write_text(f"latent-sre=={__version__}\n", encoding="utf-8")

    # render templated repo files
    env = make_sandbox_env(TEMPLATE_DIR)
    ctx = {"service": service, "version": __version__, "apiVersion": SCHEMA_API_VERSION}
    for tmpl_name, dest_rel in _FILE_TEMPLATES.items():
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(env.get_template(tmpl_name).render(**ctx), encoding="utf-8")

    (root / ".provenance" / "scan.yaml").write_text(
        "apiVersion: sre.latent-sre/v1\n"
        "kind: ScanProvenance\n"
        f"service: {service}\n"
        f"engineVersion: {__version__}\n"
        "needs-human-review: true\n",
        encoding="utf-8",
    )
    return root
