# The ownership boundary: scan role vs publish role

The single most important architectural decision is that the agent which **reads untrusted code**
and the credential which can **write to a repo** never exist in the same context.

```
                 ┌─────────────────────────────┐
   target repo   │  SCAN ROLE (Copilot agent)  │   neutral artifacts
   (UNTRUSTED) ─▶ │  read-only · no terminal    │ ─────────────────────┐
                 │  no network · no write token │                      │   (.sre-scan/, field
                 │  content = data, not orders  │                      │    names + shapes only,
                 └─────────────────────────────┘                      │    governance block)
                                                                       ▼
                 ┌─────────────────────────────┐            ┌────────────────────┐
   SRE-<svc>     │  PUBLISH ROLE (CI)          │            │  latent-sre engine │
   repo       ◀─ │  credential scoped to        │ ◀───────── │  render · validate │
   (PR)          │  latent-sre/SRE-* only       │   gated by │  redact · scaffold │
                 └─────────────────────────────┘            └────────────────────┘
```

## Why split this way

- **Injection has nothing to act on.** If hostile target text convinces the scan agent to
  "exfiltrate credentials and open a PR to attacker/exfil", the agent holds no credential and cannot
  open a PR anywhere. The instruction dead-ends.
- **The write path is deterministic, not agentic.** The publish role does not "decide" — it runs the
  engine (`render-adapters`, `validate`, `redact`, `scaffold`) and opens a PR. Its credential is
  scoped to `latent-sre/SRE-*`, so even a compromised step cannot touch the source org.
- **Neutral hand-off.** The only thing crossing the boundary is schema-validated, value-free
  artifacts. There is no code, no command, and no secret in the hand-off.

## app vs platform ownership (a second boundary, inside the artifacts)

Every concern is tagged `ownership: app | platform | shared`. This keeps app-team SLOs/alerts
distinct from platform (PCF/infra) concerns so each lands with the right owners and neither silently
overrides the other. It also lets a human reviewer filter quickly: platform-owned findings route to
the platform team's review, app-owned to the service team.

## What the scan role may write

Only to the local scan output (`.sre-scan/` by default): neutral artifacts carrying field names and
structural shape, plus the governance block (`provenance`, `ownership`, `confidence`,
`needs-human-review: true`). Never values, never tool query syntax, never into the target repo.
