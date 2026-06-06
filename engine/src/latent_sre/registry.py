"""Single declarative registry of artifact kinds → (schema, destination, renderer).

The kind→schema→template→directory wiring used to be duplicated across assemble, validate, scaffold,
and the generated CI template — miss one site and a gate is silently skipped. This is now the one
place to add or change a kind. Control-plane kinds (orchestration artifacts the engine emits *about*
a scan, not deliverables) are listed separately: they have no data schema by design.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactKind:
    kind: str             # the artifact's `kind`
    schema: str           # schema stem: "alert-intent" -> alert-intent.schema.json
    dest: str             # subdir under SRE-<service>/ the source artifact is copied to
    renderer: str | None  # "alert" | "runbook" | "dashboard" | None (copy-only)


DATA_KINDS: tuple[ArtifactKind, ...] = (
    ArtifactKind("AlertIntent", "alert-intent", "alerts/intent", "alert"),
    ArtifactKind("RunbookSpec", "runbook-spec", "runbooks", "runbook"),
    ArtifactKind("Slo", "slo", "slos", None),
    ArtifactKind("Dashboard", "dashboard", "dashboards", "dashboard"),
    ArtifactKind("Criticality", "criticality", "metadata", None),
    ArtifactKind("Dependencies", "dependencies", "metadata", None),
    ArtifactKind("PcfDeployment", "pcf-deployment", "metadata", None),
    ArtifactKind("TechStack", "tech-stack", "metadata", None),
    ArtifactKind("Architecture", "architecture", "metadata", None),
    ArtifactKind("Infrastructure", "infrastructure", "metadata", None),
    ArtifactKind("ApiContracts", "api-contracts", "metadata", None),
    ArtifactKind("Messaging", "messaging", "metadata", None),
    ArtifactKind("Jobs", "jobs", "metadata", None),
    ArtifactKind("Resiliency", "resiliency", "metadata", None),
    ArtifactKind("Logging", "logging", "metadata", None),
    ArtifactKind("Delivery", "delivery", "metadata", None),
    ArtifactKind("ObservabilityCoverage", "observability-coverage", "metadata", None),
)

BY_KIND: dict[str, ArtifactKind] = {k.kind: k for k in DATA_KINDS}

# Orchestration kinds the engine emits about a scan (not deliverable artifacts); no data schema by
# design — validate recognizes these rather than erroring "no schema found".
CONTROL_KINDS: frozenset[str] = frozenset({
    "ScanPlan", "ScanState", "ScanProvenance", "Pipeline", "AssembleManifest",
})

# Distinct destination subdirs — drives scaffold dirs, assemble's validation loop, and the generated CI.
ARTIFACT_DIRS: tuple[str, ...] = tuple(sorted({k.dest for k in DATA_KINDS}))
