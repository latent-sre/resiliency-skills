#!/bin/bash
# SessionStart hook: prepare a fresh Claude Code on the web session to run the engine's
# tests, the latent-sre CLI gates, and the SKILL.md linter — mirroring .github/workflows/validate.yml.
# Synchronous (no async) so deps are guaranteed installed before the agent loop starts.
set -euo pipefail

# Web/remote sessions only; a local machine is assumed already set up.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Hash-pinned dev deps (pytest, jsonschema, ruamel.yaml, jinja2, detect-secrets, …) then the engine
# itself --no-deps so nothing resolves unpinned. Idempotent: pip is a no-op if already satisfied.
# --ignore-installed: don't try to uninstall a distro-managed package (e.g. a system PyYAML whose
# RECORD pip can't remove); install the pinned versions alongside instead.
python -m pip install --quiet --ignore-installed --require-hashes -r engine/requirements-dev.lock
python -m pip install --quiet --no-deps ./engine

# Make the engine importable for ad-hoc `python -m latent_sre.cli ...` / pytest runs from the repo root.
echo 'export PYTHONPATH="engine/src${PYTHONPATH:+:$PYTHONPATH}"' >> "$CLAUDE_ENV_FILE"
