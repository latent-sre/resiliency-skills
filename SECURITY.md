# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately via GitHub Security Advisories
("Report a vulnerability" on the repository's **Security** tab), not as a public issue. Include
repro steps and impact. We aim to acknowledge within a few business days.

## Supply-chain posture (enforced)

- **Hash-pinned dependencies.** Runtime and dev dependencies are locked in `engine/uv.lock` and
  exported to `engine/requirements.lock` / `engine/requirements-dev.lock`; CI installs with
  `pip install --require-hashes`, so a tampered or substituted artifact fails the build.
- **Digest-pinned Actions.** `renovate.json` pins every GitHub Action to a full commit SHA
  (`helpers:pinGitHubActionDigests`) and keeps the locks fresh. Workflows show readable tags;
  Renovate rewrites them to `@<sha> # <tag>`.
- **Two independent secret gates.** The fail-closed `latent-sre redact` (primary) plus
  `detect-secrets` (independent OSS engine) both run in CI and in every generated `SRE-<service>`
  repo. A gap in one is caught by the other.
- **Trusted Publishing.** Releases publish to PyPI via OIDC (no long-lived token) with build
  attestations (`.github/workflows/release.yml`).
- **Defensive name registration.** The `latent-sre` distribution name is reserved to prevent
  typosquatting.
- **Air-gapped installs.** `scripts/build-offline.sh` produces an offline wheel bundle (engine +
  hash-pinned deps) for PCF runners without egress.

See `docs/security.md` for the full threat model and `docs/setup-and-permissions.md` for operator
preconditions.
