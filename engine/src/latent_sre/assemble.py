"""Deterministic publish ASSEMBLY — the core of the publish role.

Take a directory of validated neutral artifacts (``.sre-scan/<service>/``) and produce a populated,
hardened ``SRE-<service>`` tree: scaffold + copied metadata + rendered alert adapters + rendered
runbooks + a dependency diagram. It then re-runs schema validation (against the *vendored* schemas)
and the fail-closed redact gate over the result.

Two engine-owned guarantees live HERE (not in agent prose):
* **No clobber.** Re-assembly never overwrites a human edit. A live file that diverged from the hash
  we last wrote is preserved; the new draft is routed to ``.proposed/`` (tracked in ``.sre/manifest.yaml``).
* **No silent collision.** Two artifacts that resolve to the same output path are reported as a
  collision (fail-closed), not silently lost.

It does NOT create a git commit or open the cross-repo PR — that is the publish role's job, with the
``latent-sre/SRE-*``-scoped credential. The engine only does the deterministic, in-tree assembly, so
the whole thing is testable end-to-end without any credential.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import SCHEMA_API_VERSION, dashboard, hashdiff, mermaid, redact, registry, render, runbook, scaffold, yamlio
from . import validate as validate_mod


@dataclass
class AssembleResult:
    root: Path
    service: str
    written: list[Path] = field(default_factory=list)
    proposed: list[Path] = field(default_factory=list)   # human-edited files: draft routed here, not clobbered
    validation: list[str] = field(default_factory=list)
    secrets: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.validation and not self.secrets


def _load_artifacts(scan_dir: Path) -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for p in sorted(list(scan_dir.rglob("*.yaml")) + list(scan_dir.rglob("*.yml"))):  # single global sort
        try:
            doc = yamlio.load(p)
        except Exception:
            continue
        if isinstance(doc, dict) and doc.get("kind"):
            out.append((p, doc))
    return out


def _infer_service(docs: list[tuple[Path, dict]]) -> str:
    for _, d in docs:
        svc = d.get("service") or d.get("metadata", {}).get("service")
        if svc:
            return svc
    return "service"


def _copy(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _stage_artifact(kind: str, path: Path, stage: Path, tier: str | None = None) -> list[Path]:
    """Render/copy one artifact into an isolated staging dir; return the files it produced.
    Destination + renderer come from the single registry (no per-kind branches to keep in sync).
    `tier` (the service's Criticality tier) sets the alert severity floor."""
    spec = registry.BY_KIND.get(kind)
    if spec is None:
        return []
    produced = [_copy(path, stage / spec.dest / path.name)]
    if spec.renderer == "alert":
        produced += render.render_file(path, stage / "alerts", tier=tier)
    elif spec.renderer == "runbook":
        produced.append(runbook.render_runbook_file(path, stage / "runbooks"))
    elif spec.renderer == "dashboard":
        produced.append(dashboard.render_dashboard_file(path, stage / "dashboards"))
    return produced


def _validate_rendered(written: list[Path], root: Path) -> list[str]:
    """Sanity-check the rendered *deliverables* (not just the copied source artifacts): they must at
    least parse. Catches a template/IR regression that would otherwise ship a structurally broken config."""
    problems: list[str] = []
    for w in written:
        try:
            if w.suffix == ".json":
                json.loads(w.read_text(encoding="utf-8"))
            elif w.suffix in (".yaml", ".yml"):
                yamlio.load(w)
        except Exception as e:
            problems.append(f"{w.relative_to(root)}: rendered output does not parse: {e}")
    return problems


def assemble(scan_dir: str | Path, out_dir: str | Path, service: str | None = None) -> AssembleResult:
    scan_dir, out_dir = Path(scan_dir), Path(out_dir)
    docs = _load_artifacts(scan_dir)
    service = scaffold.clean_service(service or _infer_service(docs))
    tier = next((d.get("tier") for _, d in docs if d.get("kind") == "Criticality"), None)
    root = scaffold.scaffold(out_dir, service)
    res = AssembleResult(root=root, service=service)

    # 1. Render/copy every artifact into an isolated per-artifact staging tree, so two artifacts that
    #    resolve to the same output path are detected as a collision instead of silently overwriting.
    staging = Path(tempfile.mkdtemp(prefix="latent-sre-asm-"))
    try:
        produced: dict[str, Path] = {}
        collisions: set[str] = set()
        deps_path: Path | None = None

        def _claim(rel: str, src: Path) -> None:
            if rel in produced:
                collisions.add(rel)
            else:
                produced[rel] = src

        for i, (path, doc) in enumerate(docs):
            stage_i = staging / str(i)
            for o in _stage_artifact(doc["kind"], path, stage_i, tier):
                _claim(str(o.relative_to(stage_i)), o)
            if doc["kind"] == "Dependencies":
                deps_path = path
        if deps_path is not None:
            d = staging / "_deps" / "diagrams" / f"{service}-dependencies.md"
            d.parent.mkdir(parents=True, exist_ok=True)
            d.write_text(f"# {service} dependencies\n\n{mermaid.from_dependencies(deps_path)}\n",
                         encoding="utf-8")
            _claim(str(d.relative_to(staging / "_deps")), d)

        for rel in sorted(collisions):
            res.validation.append(f"output name collision: {rel} produced by multiple artifacts")

        # 2. Merge staging -> root with clobber-protection. A live file that diverged from the hash we
        #    last wrote (a human edit) is preserved; the new draft is routed to .proposed/ instead.
        manifest_path = root / ".sre" / "manifest.yaml"
        mdoc = (yamlio.load(manifest_path) or {}) if manifest_path.is_file() else {}
        recorded = mdoc.get("hashes", {}) if isinstance(mdoc, dict) else {}
        hashes: dict[str, str] = dict(recorded)
        for rel in sorted(produced):
            staged, dest = produced[rel], root / rel
            content = staged.read_text(encoding="utf-8")
            if dest.is_file() and rel in recorded and hashdiff.content_hash(dest) != recorded[rel]:
                proposed = root / ".proposed" / rel        # human edit → preserve live, propose the draft;
                proposed.parent.mkdir(parents=True, exist_ok=True)
                proposed.write_text(content, encoding="utf-8")
                res.proposed.append(proposed)              # keep the old recorded hash → keep detecting
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                res.written.append(dest)
                hashes[rel] = hashdiff.content_hash(dest)
        yamlio.dump({"apiVersion": SCHEMA_API_VERSION, "kind": "AssembleManifest", "hashes": hashes},
                    manifest_path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    # 3. Final gates: schema-validate source artifacts against the VENDORED schemas, sanity-check the
    #    rendered deliverables, then run the fail-closed redact gate over the whole tree.
    vendored = root / ".sre" / "schemas"
    for sub in registry.ARTIFACT_DIRS:
        d = root / sub
        if d.is_dir():
            res.validation.extend(validate_mod.validate_tree(d, vendored))
    res.validation.extend(_validate_rendered(res.written, root))
    res.secrets = redact.scan_path(root)
    return res
