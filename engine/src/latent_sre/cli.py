"""`latent-sre` CLI — the deterministic surface the orchestrator/CI invoke.

Exit codes: 0 = ok; 1 = gate failure (validation errors or secret findings — fail-closed);
2 = bad invocation/input (missing file, unreadable path).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    __version__, appnames, assemble, dashboard, hashdiff, mermaid, plan, redact, render, runbook,
    scaffold, scanstate, validate,
)


def _cmd_redact(a) -> int:
    findings = []
    for p in a.path:
        findings.extend(redact.scan_path(Path(p)))
    if findings:
        print(f"redact: BLOCKED — {len(findings)} potential secret(s):", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print("  (add `# latent-sre:allow <reason>` or a `.latent-sre-allow` entry to suppress a false positive)",
              file=sys.stderr)
        return 1
    print("redact: clean")
    return 0


def _cmd_validate(a) -> int:
    schema_dir = Path(a.schema_dir) if a.schema_dir else validate.SCHEMA_DIR
    problems = []
    for path in a.path:
        t = Path(path)
        problems += validate.validate_tree(t, schema_dir) if t.is_dir() else validate.validate_file(t, schema_dir)
    if problems:
        print(f"validate: {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("validate: ok")
    return 0


def _cmd_render(a) -> int:
    written = render.render_file(a.intent, a.out, a.targets or None)
    for w in written:
        print(w)
    return 0


def _cmd_render_runbook(a) -> int:
    print(runbook.render_runbook_file(a.spec, a.out))
    return 0


def _cmd_render_dashboard(a) -> int:
    print(dashboard.render_dashboard_file(a.spec, a.out))
    return 0


def _cmd_assemble(a) -> int:
    res = assemble.assemble(a.scan_dir, a.out, a.service)
    for w in res.written:
        print(w)
    print(f"assemble: {res.service} -> {res.root} ({len(res.written)} files)")
    if res.proposed:
        print(f"  proposed (human edits preserved; review .proposed/) ({len(res.proposed)}):")
        for pf in res.proposed:
            print(f"    {pf}")
    if res.validation:
        print(f"  validation problems ({len(res.validation)}):", file=sys.stderr)
        for v in res.validation:
            print(f"    {v}", file=sys.stderr)
    if res.secrets:
        print(f"  secret findings ({len(res.secrets)}):", file=sys.stderr)
        for s in res.secrets:
            print(f"    {s}", file=sys.stderr)
    return 0 if res.ok else 1


def _cmd_scaffold(a) -> int:
    print(scaffold.scaffold(a.out, a.name))
    return 0


def _cmd_appnames(a) -> int:
    import json
    print(json.dumps(appnames.discover(a.repo), indent=2))
    return 0


def _cmd_mermaid(a) -> int:
    print(mermaid.from_dependencies(a.path))
    return 0


def _cmd_hashdiff(a) -> int:
    print(hashdiff.content_hash(a.path))
    return 0


def _cmd_scanstate(a) -> int:
    rec = scanstate.get(a.path, a.service, a.skill)
    print(rec if rec else f"(no record for {a.service}/{a.skill})")
    return 0


def _cmd_plan(a) -> int:
    import json
    p = plan.make_plan(a.repo, a.pipeline, a.scan_state)
    print(json.dumps(p, indent=2))
    if p["requiresHumanConfirm"]:
        f = p["fanout"]
        print(f"plan: fan-out {f['total']} exceeds cap {f['cap']} — human confirmation required",
              file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="latent-sre", description="SRE skills deterministic engine")
    p.add_argument("--version", action="version", version=f"latent-sre {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("redact", help="fail-closed secret/PII scan")
    s.add_argument("path", nargs="+"); s.set_defaults(fn=_cmd_redact)

    s = sub.add_parser("validate", help="schema-validate artifacts")
    s.add_argument("path", nargs="+")
    s.add_argument("--schema-dir", default=None, help="validate against a vendored schema dir")
    s.set_defaults(fn=_cmd_validate)

    s = sub.add_parser("render-adapters", help="render a neutral AlertIntent to tool configs")
    s.add_argument("intent"); s.add_argument("--out", required=True)
    s.add_argument("--targets", nargs="*"); s.set_defaults(fn=_cmd_render)

    s = sub.add_parser("render-runbook", help="render a neutral RunbookSpec to Markdown")
    s.add_argument("spec"); s.add_argument("--out", required=True); s.set_defaults(fn=_cmd_render_runbook)

    s = sub.add_parser("render-dashboard", help="render a neutral Dashboard to Grafana JSON")
    s.add_argument("spec"); s.add_argument("--out", required=True); s.set_defaults(fn=_cmd_render_dashboard)

    s = sub.add_parser("assemble", help="assemble scan artifacts into a populated SRE-<service> tree")
    s.add_argument("scan_dir"); s.add_argument("--out", required=True)
    s.add_argument("--service", default=None); s.set_defaults(fn=_cmd_assemble)

    s = sub.add_parser("scaffold", help="create an SRE-<service> skeleton")
    s.add_argument("out"); s.add_argument("--name", required=True); s.set_defaults(fn=_cmd_scaffold)

    s = sub.add_parser("app-names", help="list deployable services (monorepo fan-out)")
    s.add_argument("repo"); s.set_defaults(fn=_cmd_appnames)

    s = sub.add_parser("mermaid", help="dependency graph from dependencies.yaml")
    s.add_argument("path"); s.set_defaults(fn=_cmd_mermaid)

    s = sub.add_parser("hash-diff", help="normalized content hash")
    s.add_argument("path"); s.set_defaults(fn=_cmd_hashdiff)

    s = sub.add_parser("scan-state", help="read a scan-state record")
    s.add_argument("path"); s.add_argument("--service", required=True)
    s.add_argument("--skill", required=True); s.set_defaults(fn=_cmd_scanstate)

    s = sub.add_parser("plan", help="emit a per-service scan plan (pipeline x fan-out + resume status)")
    s.add_argument("repo")
    s.add_argument("--pipeline", default=None, help="override the bundled pipeline.yaml")
    s.add_argument("--scan-state", default=None, help="annotate skill status from a scan-state.yaml")
    s.set_defaults(fn=_cmd_plan)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except OSError as e:  # missing/unreadable input → clean message + exit 2, not a stacktrace
        print(f"{args.cmd}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
