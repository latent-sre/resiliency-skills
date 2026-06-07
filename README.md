# resiliency-skills

A suite of **GitHub Copilot skills** that scan a developer repository to build a deep SRE
understanding of it, and emit that understanding as structured YAML + Markdown into a separate
**`SRE-<service>`** knowledge repo (one per deployable service).

It is built **thin skills, fat config, deterministic transforms**: the Copilot agent (the *scan
role*) reads code and emits *neutral* artifacts; the deterministic, security-critical work
(rendering alerts to your tools, schema validation, secret redaction, scaffolding) is done by the
`latent-sre` Python engine in CI.

> **Status:** the full vertical slice is in review as a stack on top of the PR1 contract + security
> core — end-to-end publish path (PR2), the 18-skill suite (PR3), observability/SLOs/dashboards (PR4),
> supply-chain & release hardening (PR5), and orchestration (PR6). See
> [`docs/roadmap.md`](docs/roadmap.md).

## What it produces

Per scanned service, an `SRE-<service>` repo containing: a Backstage `catalog-info.yaml`, `metadata/`
(techstack, architecture, PCF, infra, dependencies, API contracts, messaging, jobs, resiliency,
logging, delivery, observability coverage), `slos/`, `alerts/` (neutral intents + rendered Splunk/
Wavefront/AppDynamics/ThousandEyes/Grafana/Prometheus), `dashboards/`, `runbooks/`, and provenance.

## Architecture (two roles, one boundary)

- **Scan role** — read-only Copilot agent (no terminal, no write token). Treats the target repo as
  **untrusted data, never instructions**. Emits neutral artifacts (field names/shapes, never values).
- **Publish role** — CI + a publish step with a credential scoped only to `latent-sre/SRE-*`. CI runs
  the `latent-sre` engine to render adapters, validate against schemas, and run the **fail-closed
  secret gate**, then opens a PR into the `SRE-<service>` repo (created from a hardened template).

The scan role and the write credential **never share a context** — this contains prompt-injection
from a hostile target repo. See `docs/security.md` and `docs/ownership-boundary.md`.

## The engine (`engine/`)

`latent-sre` — a Python package (the deterministic surface CI/agents invoke):

```
latent-sre assemble <scan-dir>       # scan artifacts -> populated, validated, redacted SRE-<service> tree
latent-sre validate <path...>        # schema-validate artifacts (--schema-dir to use vendored schemas)
latent-sre render-adapters <intent>  # neutral AlertIntent -> per-tool configs (sandboxed, sentinel-guarded)
latent-sre render-runbook <spec>     # neutral RunbookSpec -> Markdown runbook (sandboxed)
latent-sre redact <path...>          # fail-closed secret/PII gate
latent-sre scaffold <dir> --name <s> # hardened SRE-<service> skeleton (vendored schemas, own CI, CODEOWNERS)
latent-sre app-names <repo>          # deployable services (monorepo fan-out, capped)
latent-sre plan <repo>               # per-service scan plan: canonical pipeline x fan-out, resumable
latent-sre mermaid <deps.yaml>       # dependency graph (untrusted labels sanitized)
latent-sre hash-diff <path>          # normalized content hash (clobber-protection)
latent-sre scan-state <path> --service <s> --skill <k>  # read a per-service resume checkpoint
```

`assemble` is the deterministic core of the publish role: it scaffolds a hardened repo, copies the
neutral metadata, renders the alert adapters + runbooks + dependency diagram, then re-runs validation
(against the *vendored* schemas) and the fail-closed redact gate. It **never clobbers a human edit**
(a diverged file is routed to `.proposed/`, tracked in `.sre/manifest.yaml`) and reports output-name
collisions. Opening the cross-repo PR is the only step left to the credentialed publish role. See
[`docs/publish-path.md`](docs/publish-path.md).

Develop & test the engine:

```bash
cd engine
python3 -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/python -m pytest        # incl. the malicious-secret + injection-safety fixtures
```

## Repository layout

```
engine/                 latent-sre Python package, schemas, adapter templates, tests
.github/
  copilot-instructions.md   scan-role behavior + untrusted-content rules
  agents/                   orchestrator agent (sre-analyst)
  prompts/                  entry-point prompts (full-scan, publish)
  skills/                   thin SKILL.md units (exemplars in PR1)
lib/                    shared taxonomy + detection signatures (the "fat config")
docs/                   security, permissions, the AlertIntent model, versioning, the role boundary
examples/               golden (valid) + malicious (hostile target) fixtures
.vscode/mcp.json        hosted GitHub MCP server (publish role only)
```

## Decisions still required before the full build (PR1 preconditions)

1. **Distribution coordinates** for `latent-sre` — internal mirror or source/offline wheel (offline bundler provided; not published to public PyPI).
2. **GHAS / secret-protection status** on the `latent-sre` org (sets whether push-protection exists
   or `latent-sre redact` is the sole gate — it is fail-closed either way).
3. The **pinned model** for the orchestrator agent.

See `docs/setup-and-permissions.md`, `docs/security.md`, and `docs/versioning.md`.
