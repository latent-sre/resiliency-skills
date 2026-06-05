"""latent-sre — deterministic transform engine for the SRE resiliency skills suite.

The model (Copilot skills) does inference and emits *neutral* artifacts; this package does the
deterministic, security-critical transforms in CI:

    validate         schema-validate artifacts (governance fields + positive field allow-lists)
    render-adapters  expand a neutral AlertIntent into per-tool configs (sandboxed Jinja2 + sentinels)
    redact           fail-closed secret/PII gate (the single load-bearing safety control)
    scaffold         lay down an SRE-<service> skeleton with vendored, pinned schemas
    scan-state       read/update the resumable scan checkpoint
    hash-diff        normalized content hashing for clobber-protection
    mermaid          dependency graph (untrusted labels escaped)
    app-names        list deployable services in a repo (monorepo fan-out, capped)
    plan             per-service scan plan: canonical pipeline x fan-out, with resume status
"""

__version__ = "0.1.0"
SCHEMA_API_VERSION = "sre.latent-sre/v1"
