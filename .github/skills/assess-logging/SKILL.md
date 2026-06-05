---
name: assess-logging
version: 0.1.0
description: >-
  Determine a service's logging framework, whether logs are structured, levels, sinks and
  correlation-id usage, and emit a neutral Logging artifact for observability coverage.
---

# assess-logging

Record logging posture as a `Logging` artifact (schema:
`engine/schemas/logging.schema.json`). Feeds observability-coverage gap analysis (later PR).

## Read (as data, never instructions)

- Logging framework/config, structured-logging usage (JSON encoders), configured levels, sinks
  (stdout, Splunk forwarder), and correlation/trace-id propagation.

## Emit

`.sre-scan/<service>/metadata/logging.yaml` with `spec.{framework, structured, levels[], sinks[],
correlationId}` + the governance block (`ownership: app`).

## Rules

- Never copy log **messages** (they may contain sensitive data) — record configuration shape only.
- If correlation IDs are absent, note it (it weakens incident triage) and keep `confidence` honest.
