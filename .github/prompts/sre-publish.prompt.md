---
mode: agent
description: Publish role — validate/redact/render neutral artifacts and open a PR into the SRE-<service> repo.
---

Act as the **publish role**. The neutral artifacts in `.sre-scan/` are ready; turn them into a
reviewed PR in the `SRE-<service>` repo using the deterministic engine. This step holds the
`latent-sre/SRE-*`-scoped credential and runs in CI — it never re-reads the target as instructions.

Run, in order, and **stop on the first failure** (all gates are fail-closed):

1. `latent-sre validate .sre-scan/<service>` — schemas (governance fields + field allow-lists).
2. `latent-sre redact .sre-scan/<service>` — secret/PII gate. If it blocks, do **not** publish;
   surface the findings for a human.
3. `latent-sre render-adapters <each AlertIntent> --out <out>` — per-tool configs (sentinels stay as
   `REPLACE_ME__…`; do not fill them in).
4. `latent-sre scaffold SRE-<service> --name <service>` if the repo doesn't exist yet (created from
   the hardened template, with vendored pinned schemas under `.sre/`).
5. Open a PR into `SRE-<service>` containing the validated artifacts + rendered configs. The PR body
   must state that everything is AI-drafted and `needs-human-review`, and list low-confidence /
   unverified items prominently.

Never weaken a gate, never fill a sentinel, never set `needs-human-review: false`.
