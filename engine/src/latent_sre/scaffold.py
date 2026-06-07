"""Lay down a complete, hardened SRE-<service> skeleton (review items S3/F13).

The generated repo:
* vendors the exact schema set + engine version it was born with into ``.sre/`` so its own CI
  validates against the contract that generated it, decoupled from this repo's main;
* ships its own least-privilege CI (validate vs vendored schemas + fail-closed redact);
* ships CODEOWNERS + a PR template so AI-drafted updates cannot merge unreviewed;
* ships a Backstage ``catalog-info.yaml`` and a provenance-stamped README banner.

The operator-facing files (CODEOWNERS, README, …) are returned by ``repo_files()`` so ``assemble``
can route them through clobber-protection — a re-scan must never revert an operator's owning-team or
README edit. The standalone ``scaffold`` command writes them directly (with a manifest, so a later
``assemble`` still preserves edits).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import SCHEMA_API_VERSION, __version__, hashdiff, registry, yamlio
from .paths import data_dir
from .render import make_sandbox_env

SCHEMA_DIR = data_dir("schemas")
TEMPLATE_DIR = data_dir("templates")

# Artifact destination dirs come from the single registry; the rest are fixed scaffold dirs.
_DIRS = list(registry.ARTIFACT_DIRS) + [
    "diagrams", ".proposed", ".sre/schemas", ".provenance", ".github/workflows",
]

# template (relative to templates/) -> destination (relative to the new repo root)
_FILE_TEMPLATES = {
    "sre-repo/README.md.j2": "README.md",
    "sre-repo/catalog-info.yaml.j2": "catalog-info.yaml",
    "sre-repo/CODEOWNERS.j2": ".github/CODEOWNERS",
    "sre-repo/pull_request_template.md.j2": ".github/pull_request_template.md",
    "sre-repo/workflows-validate.yml.j2": ".github/workflows/validate.yml",
    "sre-repo/renovate.json.j2": "renovate.json",
    "sre-repo/gitignore.j2": ".gitignore",
}


def clean_service(s: str) -> str:
    """Service names are untrusted (may come from a hostile manifest). Constrain to a safe charset."""
    return re.sub(r"[^A-Za-z0-9_.-]", "-", str(s)).strip("-")[:63] or "service"


def _render_repo_files(service: str) -> dict[str, str]:
    env = make_sandbox_env(TEMPLATE_DIR)
    ctx = {"service": service, "version": __version__, "apiVersion": SCHEMA_API_VERSION,
           "artifact_dirs": " ".join(registry.ARTIFACT_DIRS)}
    return {dest_rel: env.get_template(tmpl).render(**ctx) for tmpl, dest_rel in _FILE_TEMPLATES.items()}


def repo_files(service: str) -> dict[str, str]:
    """The operator-facing repo files as ``{repo-relative path: content}`` (not written to disk), so
    a caller (``assemble``) can merge them with clobber-protection."""
    return _render_repo_files(clean_service(service))


def scaffold(out: str | Path, service: str, schema_dir: Path = SCHEMA_DIR,
             write_repo_files: bool = True) -> Path:
    service = clean_service(service)
    root = Path(out)
    for d in _DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    # vendor pinned schemas + engine version (engine-owned: always refreshed)
    if schema_dir.is_dir():
        for s in schema_dir.glob("*.schema.json"):
            shutil.copy2(s, root / ".sre" / "schemas" / s.name)
    (root / ".sre" / "version").write_text(f"latent-sre=={__version__}\n", encoding="utf-8")

    # Operator-facing files: written directly for a standalone scaffold (with a manifest so a later
    # `assemble` preserves any edits). `assemble` passes write_repo_files=False and clobber-protects them.
    if write_repo_files:
        hashes: dict[str, str] = {}
        for rel, content in _render_repo_files(service).items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            hashes[rel] = hashdiff.content_hash(dest)
        yamlio.dump({"apiVersion": SCHEMA_API_VERSION, "kind": "AssembleManifest", "hashes": hashes},
                    root / ".sre" / "manifest.yaml")

    (root / ".provenance" / "scan.yaml").write_text(
        "apiVersion: sre.latent-sre/v1\n"
        "kind: ScanProvenance\n"
        f"service: {service}\n"
        f"engineVersion: {__version__}\n"
        "needs-human-review: true\n",
        encoding="utf-8",
    )
    return root
