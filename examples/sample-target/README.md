# sample-target (test fixture)

A minimal fake service repo used by the engine's integration test (`engine/tests/test_plan.py`):
two PCF `applications:` so `latent-sre app-names` / `latent-sre plan` discover a fan-out of two, plus
a `pom.xml` so tech-stack signatures have something to match.

It represents the **input** to a scan (a target repo). The neutral artifacts a scan would *produce*
live in `examples/golden/`. Contains no secrets; not a real service.
