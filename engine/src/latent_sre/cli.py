"""`latent-sre` CLI — the deterministic surface the orchestrator/CI invoke.

Exit codes: 0 = ok; 1 = gate failure (validation errors or secret findings — fail-closed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, appnames, hashdiff, mermaid, redact, render, scaffold, scanstate, validate


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
    target = Path(a.path)
    problems = validate.validate_tree(target) if target.is_dir() else validate.validate_file(target)
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
    rec = scanstate.get(a.path, a.skill)
    print(rec if rec else f"(no record for {a.skill})")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="latent-sre", description="SRE skills deterministic engine")
    p.add_argument("--version", action="version", version=f"latent-sre {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("redact", help="fail-closed secret/PII scan")
    s.add_argument("path", nargs="+"); s.set_defaults(fn=_cmd_redact)

    s = sub.add_parser("validate", help="schema-validate artifacts")
    s.add_argument("path"); s.set_defaults(fn=_cmd_validate)

    s = sub.add_parser("render-adapters", help="render a neutral AlertIntent to tool configs")
    s.add_argument("intent"); s.add_argument("--out", required=True)
    s.add_argument("--targets", nargs="*"); s.set_defaults(fn=_cmd_render)

    s = sub.add_parser("scaffold", help="create an SRE-<service> skeleton")
    s.add_argument("out"); s.add_argument("--name", required=True); s.set_defaults(fn=_cmd_scaffold)

    s = sub.add_parser("app-names", help="list deployable services (monorepo fan-out)")
    s.add_argument("repo"); s.set_defaults(fn=_cmd_appnames)

    s = sub.add_parser("mermaid", help="dependency graph from dependencies.yaml")
    s.add_argument("path"); s.set_defaults(fn=_cmd_mermaid)

    s = sub.add_parser("hash-diff", help="normalized content hash")
    s.add_argument("path"); s.set_defaults(fn=_cmd_hashdiff)

    s = sub.add_parser("scan-state", help="read a scan-state record")
    s.add_argument("path"); s.add_argument("--skill", required=True); s.set_defaults(fn=_cmd_scanstate)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
