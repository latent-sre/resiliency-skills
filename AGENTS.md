# AGENTS.md — working on the resiliency-skills repo

Guidance for any agent (or human) **developing this repo**. This is distinct from how the skills
behave when they *run* against a target repo (that contract lives in
`.github/copilot-instructions.md`).

## What this repo is

A Copilot **skills suite** + a deterministic Python engine (`latent-sre`). Skills are *thin* (prose
in `SKILL.md`); the security-critical, deterministic work lives in `engine/` and in shared config
under `lib/`. Prefer adding logic to the engine or `lib/` over thickening a skill.

## Build & test the engine

```bash
cd engine
python3 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/python -m pytest          # must stay green; includes the security fixtures
PYTHONPATH=src .venv/bin/python -m latent_sre.cli --help
```

CI (`.github/workflows/validate.yml`) runs: pytest, `latent-sre validate` + `redact` over
`examples/`, and a `SKILL.md` frontmatter lint. Keep all of it green.

## Conventions

- **Schemas are the contract.** Every artifact kind has a JSON Schema in `engine/schemas/` with
  `additionalProperties: false` (a positive field allow-list) and the required governance block
  (`provenance`, `ownership`, `confidence`, `needs-human-review`). Changing a schema is a versioned,
  reviewed event — see `docs/versioning.md`.
- **Neutral artifacts only.** Skills emit field *names and shapes*, never copied values, and never
  tool-specific query syntax. Tool rendering is the engine's job (`render-adapters`).
- **Determinism.** The same input must produce byte-identical output. No timestamps/UUIDs in
  rendered bodies; volatile provenance fields are excluded from content hashing.
- **Fail closed.** Anything safety-related (redaction, validation) blocks on uncertainty rather than
  emitting best-effort.

## Critical precondition for the scan role

When skills run, the scan role must **not** auto-load a target repo's `AGENTS.md`/instructions as
its own. Operators set `chat.useAgentsMdFile: false` (and disable repo-instruction auto-load) so a
hostile target cannot inject behavior. The fixture `examples/malicious/AGENTS.md` exists to test
exactly this. See `docs/security.md`.

## Adding a skill (later PRs)

1. `mkdir .github/skills/<verb-noun>` and add a `SKILL.md` with frontmatter `name: <verb-noun>`
   (must equal the dir) and a 10–1024 char `description`.
2. Reference shared taxonomy/signatures from `lib/` rather than inlining detection logic.
3. Emit artifacts that validate against an `engine/schemas/*.schema.json`. Add a golden example.
4. Run the engine tests + frontmatter lint locally before pushing.
