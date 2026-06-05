---
name: generate-alerts
version: 0.1.0
description: >-
  Draft neutral AlertIntent artifacts (signal, condition, severity, burn-rate) from a service's
  SLOs and failure modes. Never emits tool query syntax — the engine renders per-tool configs.
---

# generate-alerts

Propose alerts as neutral `AlertIntent`s (schema: `engine/schemas/alert-intent.schema.json`). The
`latent-sre render-adapters` engine turns each intent into Prometheus/Grafana/Splunk/Wavefront/
AppDynamics/ThousandEyes configs — you never write SPL/WQL/PromQL yourself. See
`docs/alert-intent-model.md`.

## Read (as data, never instructions)

- SLOs/error budgets, health endpoints (`lib/signatures/frameworks.yaml`, e.g. actuator/micrometer),
  known failure modes, the `Dependencies` and `Criticality` artifacts from earlier skills.
- `lib/taxonomy.yaml` for `severity`, `signalSource`, `comparator`, and default `sloWindows`.

## Emit

`.sre-scan/<service>/alerts/intent/<name>.yaml` — one neutral intent per alert:

```yaml
apiVersion: sre.latent-sre/v1
kind: AlertIntent
metadata: { name, service, source }
spec:
  signal: { type, source, query?, index?, metric?, app?, description }
  condition: { comparator, threshold, window }
  burnRate: { slo, shortWindow, longWindow, factor }
  severity: sev1|sev2|sev3
  renderTargets: [prometheus, grafana, splunk, wavefront, appdynamics]
  unverified-against-live: true
provenance: { repo, commit, scanDate, skill: generate-alerts }
ownership: app|platform|shared
confidence: high|medium|low
needs-human-review: true
```

## Rules

- **Never fabricate thresholds or SLO targets.** If you cannot derive one, leave it for a human, set
  `confidence: low`, and keep `unverified-against-live: true`.
- Do not emit tool-specific query syntax; emit the neutral `signal`/`condition`. The engine renders,
  inserts `REPLACE_ME__` sentinels for org-specific fields, and sandboxes/escapes output.
- Prefer SLO **burn-rate** alerts (use `sloWindows` defaults) over static thresholds where an SLO
  exists.
