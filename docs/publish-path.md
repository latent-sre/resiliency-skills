# The publish path

How validated neutral artifacts in `.sre-scan/<service>/` become a reviewed PR in the
`SRE-<service>` repo. The deterministic part is the engine's `assemble`; the only credentialed part
is opening the PR.

## `latent-sre assemble <scan-dir> --out SRE-<service>`

Deterministic, side-effect-free, and testable without any credential. It:

1. **Scaffolds** a hardened `SRE-<service>` skeleton (`scaffold`): vendored pinned schemas under
   `.sre/`, the repo's own least-privilege CI, `CODEOWNERS`, a PR template, a Backstage
   `catalog-info.yaml`, and a provenance README banner.
2. **Dispatches each artifact by `kind`** (not by path, so a flat scan dir works):
   - `AlertIntent` → copied to `alerts/intent/`, and rendered to `alerts/<tool>/…` via `render-adapters`.
   - `RunbookSpec` → copied to `runbooks/`, and rendered to `runbooks/<name>.md` via `render-runbook`.
   - `Criticality` / `Dependencies` / `PcfDeployment` → copied to `metadata/`.
   - `Dependencies` also produces `diagrams/<service>-dependencies.md` via `mermaid`.
3. **Re-runs the gates** over the assembled tree — schema validation against the **vendored** schemas
   (`.sre/schemas`, i.e. the contract the repo was born with) and the **fail-closed** redact scan.
   `assemble` exits non-zero (and the publish role must not publish) if either gate finds a problem.

## What the credentialed publish role does

Only the final, non-deterministic step: take the assembled tree and open a PR into `SRE-<service>`
using the `latent-sre/SRE-*`-scoped credential (hosted GitHub MCP). It does not re-interpret the
target repo, and it never weakens a gate, fills a sentinel, or sets `needs-human-review: false`. See
`docs/ownership-boundary.md`.

## The generated repo ships its own defenses (operator must activate)

Each `SRE-<service>` ships:
- **its own CI** that validates against the *vendored* `.sre/schemas` (decoupled from this repo's
  `main`) and runs the fail-closed redact gate;
- **`CODEOWNERS`** with a `REPLACE_ME__owning_team` sentinel. Review enforcement is **not automatic**:
  it needs (a) the sentinel replaced with a real team and (b) branch protection requiring Code Owner
  review. The generated CI **fails closed on the unreplaced sentinel** so a repo can't silently ship
  unprotected — but only the credentialed publish role can configure branch protection (the scaffold
  writes files, it cannot configure the repo), so the publish role should set it via the GitHub API at
  repo-creation time;
- a **PR template** that restates "AI-drafted, needs human review" and lists the low-confidence /
  sentinel / unverified checks a reviewer must clear.

## Not overwriting humans

Re-assembly never clobbers human edits — enforced **in `assemble`**, not in agent prose. `assemble`
records a normalized content hash of every file it writes in `.sre/manifest.yaml`; on the next scan a
live file whose hash diverged (a human edit) is left untouched and the AI re-proposal is written to
`.proposed/<path>` instead. Cosmetic-only changes (comments, key reordering) are normalized away, so
they are not mistaken for edits.
