"""Deterministic publish ASSEMBLY — the core of the publish role.

Take a directory of validated neutral artifacts (``.sre-scan/<service>/``) and produce a populated,
hardened ``SRE-<service>`` tree: scaffold + copied metadata + rendered alert adapters + rendered
runbooks + a dependency diagram. It then re-runs schema validation (against the *vendored* schemas)
and the fail-closed redact gate over the result.

It does NOT create a git commit or open the cross-repo PR — that is the publish role's job, with the
``latent-sre/SRE-*``-scoped credential. The engine only does the deterministic, in-tree assembly, so
the whole thing is testable end-to-end without any credential.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import mermaid, redact, render, runbook, scaffold, yamlio
from . import validate as validate_mod

_METADATA_KINDS = {
    "Criticality", "Dependencies", "PcfDeployment", "TechStack", "Architecture", "Infrastructure",
    "ApiContracts", "Messaging", "Jobs", "Resiliency", "Logging", "Delivery",
}


@dataclass
class AssembleResult:
    root: Path
    service: str
    written: list[Path] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    secrets: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.validation and not self.secrets


def _load_artifacts(scan_dir: Path) -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for p in sorted(scan_dir.rglob("*.yaml")) + sorted(scan_dir.rglob("*.yml")):
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


def assemble(scan_dir: str | Path, out_dir: str | Path, service: str | None = None) -> AssembleResult:
    scan_dir, out_dir = Path(scan_dir), Path(out_dir)
    docs = _load_artifacts(scan_dir)
    service = scaffold.clean_service(service or _infer_service(docs))

    root = scaffold.scaffold(out_dir, service)
    res = AssembleResult(root=root, service=service)

    deps_path: Path | None = None
    for path, doc in docs:
        kind = doc["kind"]
        if kind == "AlertIntent":
            res.written.append(_copy(path, root / "alerts" / "intent" / path.name))
            res.written.extend(render.render_file(path, root / "alerts"))  # alerts/<tool>/<name>.<ext>
        elif kind == "RunbookSpec":
            res.written.append(_copy(path, root / "runbooks" / path.name))
            res.written.append(runbook.render_runbook_file(path, root / "runbooks"))
        elif kind in _METADATA_KINDS:
            res.written.append(_copy(path, root / "metadata" / path.name))
            if kind == "Dependencies":
                deps_path = path

    if deps_path is not None:
        diagram = mermaid.from_dependencies(deps_path)
        dest = root / "diagrams" / f"{service}-dependencies.md"
        dest.write_text(f"# {service} dependencies\n\n{diagram}\n", encoding="utf-8")
        res.written.append(dest)

    # Final gates over the assembled tree: validate against the VENDORED schemas, then fail-closed redact.
    vendored = root / ".sre" / "schemas"
    for sub in ("metadata", "alerts/intent", "runbooks"):
        d = root / sub
        if d.is_dir():
            res.validation.extend(validate_mod.validate_tree(d, vendored))
    res.secrets = redact.scan_path(root)
    return res
