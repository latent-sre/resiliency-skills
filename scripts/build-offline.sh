#!/usr/bin/env bash
# Build an offline bundle for air-gapped (e.g. PCF) CI runners: the latent-sre wheel plus every
# hash-pinned runtime dependency as a wheel. Install on the air-gapped side with:
#
#   pip install --no-index --find-links vendor/ latent-sre
#
# Run on a connected machine; commit/transfer the resulting directory to the air-gapped environment.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$repo/vendor}"
mkdir -p "$out"

# Hash-pinned runtime dependencies (verified against engine/requirements.lock).
python -m pip download --require-hashes -r "$repo/engine/requirements.lock" --dest "$out"
# The engine wheel itself (built from source, no deps).
python -m pip wheel --no-deps "$repo/engine" --wheel-dir "$out"

echo "Offline bundle written to: $out"
echo "Install with: pip install --no-index --find-links $out latent-sre"
