# Setup & permissions

What an operator configures before running the suite, and the least-privilege posture each piece
runs under.

## VS Code / Copilot settings (the scan role)

Set these so a hostile target repo cannot inject behavior (see `docs/security.md`, T1):

```jsonc
{
  // Do NOT auto-load a target repo's AGENTS.md / instruction files as agent instructions.
  "chat.useAgentsMdFile": false,
  // Keep the scan role read-only: no terminal/tool auto-approval.
  "chat.tools.autoApprove": false
}
```

The scan role runs with **no terminal, no network, and no write credential**. It writes neutral
artifacts to `.sre-scan/` only.

## MCP (the publish role)

`.vscode/mcp.json` configures the **hosted GitHub MCP server only**, used by the publish role to open
PRs into `latent-sre/SRE-*`. There is no local/custom MCP server — the `latent-sre` engine runs as a
CLI in CI, not as an MCP server. If `.vscode/mcp.json` is absent in your checkout, create it as:

```json
{ "servers": { "github": { "type": "http", "url": "https://api.githubcopilot.com/mcp/" } } }
```

## The publish credential

A single credential (GitHub App installation token or fine-grained PAT) **scoped only to the
`latent-sre/SRE-*` repositories**, with `contents:write` + `pull_requests:write`. It lives only in
the publish CI environment and is never present in the scan context. It must NOT have access to the
source/target org.

## Engine install (CI and local)

```bash
python -m pip install ./engine                                  # local dev
# CI / production (hash-pinned; see engine/uv.lock):
python -m pip install --require-hashes -r engine/requirements-dev.lock
python -m pip install --no-deps ./engine
# Air-gapped (PCF): build a bundle on a connected host, then install offline:
bash scripts/build-offline.sh vendor/
python -m pip install --no-index --find-links vendor/ latent-sre
```

Locks are generated with `uv` (`uv lock` → `uv export`). The offline bundler is provided
(`scripts/build-offline.sh`). **Open precondition:** confirm the PyPI/internal-mirror coordinates for
publishing `latent-sre`.

## Secret-scanning posture

`latent-sre redact` is **fail-closed** and runs in CI regardless of platform features. Independently,
confirm whether **GitHub Advanced Security** push-protection is enabled on the `latent-sre` org:

- **Enabled** → redact + push-protection + the `detect-secrets` second gate = three layers.
- **Not enabled** → redact + the `detect-secrets` second gate (CI, `tools/second_secret_gate.py`)
  are the gate; still fail-closed.

The independent OSS second gate (`detect-secrets`) is now wired into CI here and in the generated
`SRE-<service>` CI template (PR5). **Open precondition:** confirm GHAS status so the publish pipeline
adds push-protection as a third layer where available.

## Orchestrator model

The `sre-analyst` agent (`.github/agents/sre-analyst.agent.md`) pins a specific model in its
frontmatter. **Open precondition (PR1):** choose the pinned model. The model identifier is set by the
operator; it is intentionally left as a placeholder in-repo.

## Preconditions checklist

- [ ] `chat.useAgentsMdFile: false` (and instruction auto-load disabled) on scan runners.
- [ ] Publish credential scoped to `latent-sre/SRE-*` only, present only in publish CI.
- [ ] `latent-sre` index coordinates confirmed (offline bundler provided: `scripts/build-offline.sh`).
- [ ] GHAS push-protection status confirmed (the `detect-secrets` second gate is already wired in CI).
- [ ] Renovate enabled on the org so Action digests get pinned and locks maintained.
- [ ] Orchestrator model pinned.
