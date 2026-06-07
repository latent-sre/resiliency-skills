# The AlertIntent model

Skills never emit Splunk SPL, Wavefront WQL, PromQL, or AppDynamics JSON directly. They emit a
**neutral `AlertIntent`** — what to alert on and why — and the `latent-sre` engine renders it
deterministically into each tool's config. One reasoning step, many faithful outputs.

## Why neutral

- **Determinism & testability.** The engine renders each tool's *structure* deterministically
  (sandbox + per-value escaping), so output is byte-stable and injection-safe (see `docs/security.md`).
  Today the `signal.query` expression itself is author-provided and emitted as-is — treat it as native
  to `signal.source`; per-dialect query synthesis (one neutral signal → valid PromQL *and* SPL *and*
  WQL) is tracked as future work.
- **Portability.** Add or change a tool by adding/editing a template in
  `engine/templates/adapters/`, not by re-running the model.
- **Reviewability.** A human reviews intent (severity, threshold, signal) once, not six dialects.

## Shape

Validated by `engine/schemas/alert-intent.schema.json` (`additionalProperties:false` → only these
fields allowed; governance block required):

```yaml
apiVersion: sre.latent-sre/v1
kind: AlertIntent
metadata: { name, service, source: { repo, commit, path } }
spec:
  signal: { type: metric|log|trace|synthetic, source, query?, index?, metric?, app?, description? }
  condition: { comparator, threshold, window?, occurrences? }
  burnRate: { slo?, shortWindow?, longWindow?, factor? }     # for SLO burn-rate alerts
  severity: sev1|sev2|sev3
  class: symptom|cause   # symptom = page-eligible; cause = diagnostic/ticket
  for: 10m
  labels: {…}            # string map
  annotations: { summary, description }
  links: { runbook, slo }
  renderTargets: [prometheus, grafana, splunk, wavefront, appdynamics, thousandeyes]
  unverified-against-live: true
provenance: { repo, commit, scanDate, skill }   # required
ownership: app|platform|shared                    # required
confidence: high|medium|low                       # required
needs-human-review: true                          # required
```

The engine floors `severity` by the service's `Criticality.tier` deterministically (tier0→sev1 …
tier3→sev3): the floor can only *raise* the declared severity, never lower it, so paging level does
not depend on model consistency. `class` separates page-worthy **symptom** alerts from diagnostic
**cause** alerts (rendered as a label).

## Rendering & the deliverable spectrum

`latent-sre render-adapters <intent> --out <dir> --targets …` produces one file per target. Targets
sit on a spectrum:

- **Deliverable** — `grafana`, `prometheus`: complete rule files.
- **Needs-config** — `splunk`, `wavefront`, `appdynamics`: templates where org-specific
  connection fields (Splunk index, Wavefront metric, AppD application) render as `REPLACE_ME__<field>`
  sentinels, so an accidental apply **fails loud**.
- **Proposal-only** — `thousandeyes`: emitted as a clearly-labelled proposal, not an applyable test,
  because a synthetic test needs account/agent/target context the repo cannot supply.

Connection-critical fields that are absent always become sentinels rather than guesses, and every
scan-derived alert stays `unverified-against-live: true` until validated against a live signal.

## Example

See `examples/golden/alert-intent.yaml` (a checkout 5xx burn-rate alert) and run:

```bash
PYTHONPATH=engine/src python -m latent_sre.cli render-adapters \
  examples/golden/alert-intent.yaml --out /tmp/out --targets prometheus splunk appdynamics
```
