"""End-to-end publish assembly: scan artifacts -> populated, validated, redacted SRE-<service> tree."""
import shutil
from pathlib import Path

from latent_sre import assemble, yamlio

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden"
_ARTIFACTS = [
    "alert-intent.yaml", "criticality.yaml", "dependencies.yaml", "pcf-deployment.yaml",
    "runbook-spec.yaml", "tech-stack.yaml", "architecture.yaml", "infrastructure.yaml",
    "api-contracts.yaml", "messaging.yaml", "jobs.yaml", "resiliency.yaml", "logging.yaml",
    "delivery.yaml", "slo.yaml", "observability-coverage.yaml", "dashboard.yaml",
]


def _scan(tmp_path) -> Path:
    # flat .sre-scan/<service> dir from the goldens; assemble dispatches by `kind`, not path
    scan = tmp_path / "scan" / "checkout"
    scan.mkdir(parents=True)
    for name in _ARTIFACTS:
        shutil.copy(GOLDEN / name, scan / name)
    return scan


def test_assemble_produces_valid_clean_repo(tmp_path):
    res = assemble.assemble(_scan(tmp_path), tmp_path / "SRE-checkout")
    assert res.service == "checkout"
    assert res.ok, (res.validation, [str(s) for s in res.secrets])
    root = res.root
    assert (root / "alerts" / "intent" / "alert-intent.yaml").is_file()           # neutral intent copied
    assert (root / "alerts" / "prometheus" / "checkout-high-error-rate.yaml").is_file()  # rendered adapter
    assert (root / "runbooks" / "runbook-spec.md").is_file()                       # rendered runbook
    assert (root / "metadata" / "criticality.yaml").is_file()                      # metadata copied
    assert (root / "metadata" / "tech-stack.yaml").is_file()                       # new metadata kind dispatched
    assert (root / "metadata" / "delivery.yaml").is_file()
    assert (root / "slos" / "slo.yaml").is_file()                                  # SLO -> slos/
    assert (root / "dashboards" / "dashboard.yaml").is_file()                       # dashboard spec
    assert (root / "dashboards" / "dashboard.json").is_file()                       # rendered Grafana JSON
    assert (root / "diagrams" / "checkout-dependencies.md").is_file()              # dependency graph
    assert (root / ".github" / "workflows" / "validate.yml").is_file()             # hardened CI
    assert (root / ".sre" / "schemas" / "alert-intent.schema.json").is_file()      # vendored schema


def test_assemble_is_fail_closed_on_secret(tmp_path):
    scan = _scan(tmp_path)
    planted = "AKIA" + "I" * 16  # assembled at runtime; no secret-shaped literal committed
    bad = scan / "criticality.yaml"
    bad.write_text(bad.read_text() + f"\n# leaked-by-test: {planted}\n")
    res = assemble.assemble(scan, tmp_path / "out2")
    assert not res.ok and res.secrets  # redact gate blocks publish


def test_reassembly_preserves_human_edits(tmp_path):
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)                                   # first scan
    rb = out / "runbooks" / "runbook-spec.md"
    human = rb.read_text() + "\n<!-- human-tuned, do not clobber -->\n"
    rb.write_text(human, encoding="utf-8")
    res = assemble.assemble(scan, out)                             # re-scan
    assert rb.read_text() == human                                 # human edit preserved, NOT overwritten
    assert (out / ".proposed" / "runbooks" / "runbook-spec.md").is_file()  # AI draft proposed instead
    assert res.proposed                                            # and surfaced on the result


def test_duplicate_output_names_are_flagged_not_silently_clobbered(tmp_path):
    scan = tmp_path / "scan"
    scan.mkdir()
    intent = yamlio.load(GOLDEN / "alert-intent.yaml")
    yamlio.dump(intent, scan / "a.yaml")
    yamlio.dump(intent, scan / "b.yaml")  # same metadata.name -> same rendered path
    res = assemble.assemble(scan, tmp_path / "out")
    assert not res.ok
    assert any("collision" in v for v in res.validation)


def test_assemble_floors_alert_severity_by_criticality_tier(tmp_path):
    scan = _scan(tmp_path)
    crit = scan / "criticality.yaml"
    d = yamlio.load(crit)
    d["tier"] = "tier0"  # tier0 -> sev1 floor; the golden alert is sev2
    yamlio.dump(d, crit)
    res = assemble.assemble(scan, tmp_path / "out")
    prom = (res.root / "alerts" / "prometheus" / "checkout-high-error-rate.yaml").read_text()
    assert '"sev1"' in prom  # severity raised to the tier0 floor
