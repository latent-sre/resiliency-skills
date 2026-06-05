# Governance block (required in every artifact schema)

Every artifact embeds the same governance fields so `latent-sre validate` (ajv/jsonschema) fails the
build when a skill omits them — turning convention into a hard gate (review items M7 / F4):

```yaml
provenance:
  repo: github.com/acme/widget          # required
  commit: 9d779ba…                       # required (the scanned SHA)
  scanDate: 2026-06-04T12:00:00Z         # required
  skill: map-dependencies                # required
  skillVersion: 0.1.0
  modelVersion: <pinned model>           # set at run time; not committed to this repo
ownership: app                            # required — app | platform | shared
confidence: medium                        # required — high | medium | low
needs-human-review: true                  # required — always true for AI output
```

`additionalProperties: false` on each schema is what enforces the *positive field allow-list*: an
artifact may only contain the enumerated keys, so a stray copied value cannot ride along unnoticed.
