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

## The generated repo defends itself

Each `SRE-<service>` ships:
- **its own CI** that validates against the *vendored* `.sre/schemas` (decoupled from this repo's
  `main`) and runs the fail-closed redact gate;
- **`CODEOWNERS`** (with a `REPLACE_ME__owning_team` sentinel) so that — once a real team is set and
  branch protection requires Code Owner review — AI-drafted updates cannot merge unreviewed;
- a **PR template** that restates "AI-drafted, needs human review" and lists the low-confidence /
  sentinel / unverified checks a reviewer must clear.

## Not overwriting humans

Re-assembly never clobbers human edits: `hash-diff`'s normalized content hash detects a file a human
has changed and routes the AI re-proposal to `.proposed/` instead of overwriting it.
