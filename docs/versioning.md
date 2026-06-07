# Versioning & compatibility

Three things version independently, joined by one `apiVersion`.

## The contract: `apiVersion: sre.latent-sre/v1`

Every artifact and schema carries `apiVersion: sre.latent-sre/v1`. A breaking change to any
artifact shape bumps this (`v1` → `v2`). Additive, backward-compatible changes (new optional field)
do **not** bump it.

## Engine (`latent-sre`) — semver

- **patch** — bug fix, new detector pattern, no artifact-shape change.
- **minor** — new optional field/feature, backward compatible within the same `apiVersion`.
- **major** — drops/renames a field or changes validation semantics → ships with an `apiVersion` bump.

Dependencies are pinned by hash (`uv.lock`, `--require-hashes`) so a given engine version always
resolves to identical bytes.

## Skills — semver in `SKILL.md` frontmatter

Each skill carries its own `version`. The scan checkpoint (`scan-state`) records the skill+engine
version that produced each output, so a re-scan after an upgrade can tell "stale because input
changed" from "stale because the producing logic changed."

## Vendored, pinned schemas in each `SRE-<service>`

`latent-sre scaffold` copies the **exact** schema set + engine version into the generated repo under:

```
SRE-<service>/.sre/schemas/*.schema.json
SRE-<service>/.sre/version          # e.g. latent-sre==0.1.0
```

So the generated repo's own CI validates against the contract it was **born with**, decoupled from
this repo's `main`. This prevents a schema change here from retroactively failing every downstream
repo. Renovate (or the next scan) bumps the pin deliberately, as a reviewed PR — at which point any
required migration is applied and re-validated. Each schema's `$id` is versioned
(`…/schemas/v1/<name>.schema.json`), so a future `v2` set cannot collide with `v1` in a shared validator.

## Compatibility rules

1. CI refuses to publish if an artifact's `apiVersion` major is newer than the engine understands —
   enforced by the `latent-sre validate` gate (a clear "newer than this engine supports" error).
2. Within an `apiVersion`, the engine reads older minor artifacts (additive fields are optional).
3. A major/`apiVersion` bump requires a migration note in the PR and a re-vendor of `.sre/schemas`.
