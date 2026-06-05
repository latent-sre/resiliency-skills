# Roadmap

How the SRE resiliency-skills suite is being built, in reviewable slices. Each PR is independently
mergeable and keeps `main` green (engine tests + the validate/redact/lint gates).

Guiding order: **prove the pipeline end-to-end first, then scale breadth, then harden the supply
chain.** A working vertical slice is more valuable than many half-wired skills.

## Status

| PR | Theme | State |
|----|-------|-------|
| PR1 | Contract + security core | ✅ merged (#1) |
| PR2 | End-to-end publish path | ✅ pushed (stacked) |
| PR3 | Skill suite — metadata breadth | ✅ pushed (stacked) |
| PR4 | Observability, SLOs & dashboards | 🚧 in progress (stacked on PR3) |
| PR5 | Supply-chain & release hardening | planned |
| PR6 | Orchestration & scale | planned |

## PR1 — Contract + security core ✅

The deterministic engine (`latent-sre`: redact, validate, render-adapters, scaffold, app-names,
mermaid, hash-diff, scan-state), the artifact schemas, six exemplar skills, the two-role security
model + docs, and CI. See `README.md` and `docs/security.md`.

## PR2 — End-to-end publish path 🚧

Make the suite produce a **real, reviewable `SRE-<service>` repo** from the artifacts the PR1 skills
already emit, without yet adding new skills.

- Harden `scaffold` into a **complete** `SRE-<service>` skeleton: its own CI (validate against the
  *vendored* `.sre/schemas`, fail-closed redact, OSS second-scanner stub), `CODEOWNERS` (forces human
  review), a PR template that states the output is AI-drafted + lists low-confidence/unverified items,
  a Backstage `catalog-info.yaml`, and a provenance-stamped README banner.
- `render-runbook`: `RunbookSpec` → Markdown runbook (deterministic, sandboxed/escaped like the alert
  adapters).
- `assemble`: deterministic publish *assembly* — take a `.sre-scan/<service>/` of validated neutral
  artifacts and lay down the populated `SRE-<service>` tree (metadata + rendered alert adapters +
  rendered runbooks + catalog). The actual cross-repo PR is still done by the publish role with the
  `latent-sre/SRE-*`-scoped credential; the engine only does the deterministic assembly.
- Tests for scaffold completeness + runbook rendering + assembly; docs updates.

## PR3 — Skill suite, metadata breadth 🚧

The remaining metadata skills, each as a thin `SKILL.md` + a JSON Schema + a golden example:
TechStack, Architecture, Infrastructure, ApiContracts, Messaging, Jobs, Resiliency, Logging,
Delivery. No new engine surface — they reuse validate/redact/assemble; `assemble` now dispatches
these kinds into `metadata/`, and they validate against the vendored schemas in an assembled repo.

## PR4 — Observability, SLOs & dashboards 🚧

`generate-slos` (`Slo`), `assess-observability-coverage` (`ObservabilityCoverage`), and
`generate-dashboards` (`Dashboard`) skills + schemas + goldens, plus the **dashboard renderer**
(`render-dashboard`: Dashboard → Grafana JSON, built by construction so it's valid JSON and
injection-safe, with a `REPLACE_ME__grafana_datasource` sentinel). `assemble` now routes `Slo` →
`slos/`, `Dashboard` → `dashboards/` (spec + rendered JSON), and `ObservabilityCoverage` → `metadata/`,
all validated against the vendored schemas.

## PR5 — Supply-chain & release hardening

Close the "documented but not enforced" gaps from PR1: generate `uv.lock` and switch CI to
`--require-hashes`, pin all GitHub Actions by commit SHA, wire the OSS second secret scanner
(gitleaks/trufflehog) into the publish gate, add Renovate, and publish an offline wheel for
air-gapped PCF CI.

## PR6 — Orchestration & scale

Full `sre-analyst` sequencing across every skill, monorepo fan-out UX (above the cap → human
confirm), resumability hardening, and an end-to-end integration test that scans a sample target repo
and assembles its `SRE-<service>` output.

## Open preconditions (not blocking, but needed before production)

- `latent-sre` PyPI / internal-mirror coordinates (+ offline wheel for air-gapped PCF CI).
- GitHub Advanced Security push-protection status on the `latent-sre` org.
- The pinned orchestrator model (currently `PINNED_MODEL_PLACEHOLDER`).

See `docs/setup-and-permissions.md`.
