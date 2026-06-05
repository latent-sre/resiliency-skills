#!/usr/bin/env python3
"""Second, independent OSS secret gate (detect-secrets) — defense-in-depth behind `latent-sre redact`.

Runs detect-secrets over the publishable content dirs only (same scope as the primary gate): engine/
is excluded because it legitimately contains secret *patterns* (the detector), and the dependency
lockfiles are excluded because their sha256 hashes are high-entropy by design. detect-secrets is
hash-pinned via uv.lock (dev group). Exits non-zero on any finding.
"""
from __future__ import annotations

import json
import subprocess
import sys

DIRS = ["examples", "lib", "docs"]


def main() -> int:
    cmd = [sys.executable, "-m", "detect_secrets", "scan", *DIRS]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    results = json.loads(proc.stdout).get("results", {})
    if results:
        print(f"second-secret-gate: BLOCKED — findings in {len(results)} file(s):", file=sys.stderr)
        for f, items in results.items():
            print(f"  {f}: {sorted({i.get('type') for i in items})}", file=sys.stderr)
        return 1
    print("second-secret-gate: clean (detect-secrets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
