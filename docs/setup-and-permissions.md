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
python -m pip install ./engine           # local dev
# CI / production: install from your index with hashes pinned:
#   pip install --require-hashes -r requirements.lock
```

**Open precondition (PR1):** confirm the PyPI/internal-mirror coordinates for `latent-sre`, and
publish an **offline wheel** for air-gapped PCF CI runners.

## Secret-scanning posture

`latent-sre redact` is **fail-closed** and runs in CI regardless of platform features. Independently,
confirm whether **GitHub Advanced Security** push-protection is enabled on the `latent-sre` org:

- **Enabled** → redact + push-protection + an OSS scanner = three layers.
- **Not enabled** → redact + an OSS scanner (gitleaks/trufflehog) on the publish path are the gate;
  still fail-closed.

**Open precondition (PR1):** confirm GHAS status so the publish pipeline is configured accordingly.

## Orchestrator model

The `sre-analyst` agent (`.github/agents/sre-analyst.agent.md`) pins a specific model in its
frontmatter. **Open precondition (PR1):** choose the pinned model. The model identifier is set by the
operator; it is intentionally left as a placeholder in-repo.

## Preconditions checklist

- [ ] `chat.useAgentsMdFile: false` (and instruction auto-load disabled) on scan runners.
- [ ] Publish credential scoped to `latent-sre/SRE-*` only, present only in publish CI.
- [ ] `latent-sre` index coordinates confirmed + offline wheel for air-gapped CI.
- [ ] GHAS push-protection status confirmed; OSS second scanner enabled on the publish path.
- [ ] Orchestrator model pinned.
