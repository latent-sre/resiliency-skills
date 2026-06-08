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


def test_assemble_reports_unparseable_artifact_instead_of_dropping_it(tmp_path):
    # A corrupted source artifact must fail the gate (be reported), not silently vanish from the tree.
    scan = _scan(tmp_path)
    (scan / "broken.yaml").write_text("kind: AlertIntent\n  bad: : [\n", encoding="utf-8")
    res = assemble.assemble(scan, tmp_path / "SRE-checkout")
    assert not res.ok
    assert any("could not parse" in v and "broken.yaml" in v for v in res.validation)


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


def test_reassembly_preserves_operator_codeowners_edit(tmp_path):
    # H1: scaffold's operator-facing files must be clobber-protected too (was unconditionally rewritten)
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)
    co = out / ".github" / "CODEOWNERS"
    edited = "* @acme/payments-team\n"
    co.write_text(edited, encoding="utf-8")           # operator sets the real owning team
    assemble.assemble(scan, out)                       # re-scan
    assert co.read_text() == edited                    # NOT reverted to the REPLACE_ME__ sentinel
    assert (out / ".proposed" / ".github" / "CODEOWNERS").is_file()  # engine draft proposed instead


def test_hostile_render_targets_does_not_crash_and_is_flagged(tmp_path):
    # H2: an unknown renderTargets value must not raise out of assemble (render before validate)
    scan = tmp_path / "scan"
    scan.mkdir()
    intent = yamlio.load(GOLDEN / "alert-intent.yaml")
    intent["spec"]["renderTargets"] = ["evil-target"]
    yamlio.dump(intent, scan / "a.yaml")
    res = assemble.assemble(scan, tmp_path / "out")    # must not raise
    assert not res.ok                                   # schema validation flags the bad renderTargets


def test_malformed_human_edit_does_not_crash_assemble(tmp_path):
    # H3: the clobber-protection path itself must not crash on a human's broken-YAML edit
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)
    crit = out / "metadata" / "criticality.yaml"
    crit.write_text("{{{ not valid yaml :::\n", encoding="utf-8")
    assemble.assemble(scan, out)                        # must not raise
    assert crit.read_text().startswith("{{{")           # broken human edit preserved, not clobbered


def test_orphaned_ai_output_is_pruned(tmp_path):
    # H4: outputs whose producing artifact disappeared are removed on the next scan
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)
    assert (out / "dashboards" / "dashboard.json").is_file()
    (scan / "dashboard.yaml").unlink()                  # producing artifact removed
    res = assemble.assemble(scan, out)
    assert not (out / "dashboards" / "dashboard.json").is_file()   # rendered orphan pruned
    assert not (out / "dashboards" / "dashboard.yaml").is_file()   # copied-source orphan pruned
    assert any("dashboard" in p.name for p in res.removed)


def test_orphan_pruning_keeps_human_edited_file(tmp_path):
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)
    rb = out / "runbooks" / "runbook-spec.md"
    rb.write_text(rb.read_text() + "\n<!-- mine -->\n", encoding="utf-8")  # human edit
    (scan / "runbook-spec.yaml").unlink()              # producing artifact removed
    assemble.assemble(scan, out)
    assert rb.is_file()                                 # human-edited orphan is NOT deleted


def test_corrupt_manifest_does_not_crash(tmp_path):
    # L1: a corrupt .sre/manifest.yaml must be tolerated, not crash assemble
    scan = _scan(tmp_path)
    out = tmp_path / "SRE-checkout"
    assemble.assemble(scan, out)
    (out / ".sre" / "manifest.yaml").write_text("{{{ broken manifest", encoding="utf-8")
    res = assemble.assemble(scan, out)                 # must not raise
    assert res.written


def test_multiple_dependencies_artifacts_flagged(tmp_path):
    # L3: more than one Dependencies artifact is reported (was silently last-wins)
    scan = _scan(tmp_path)
    yamlio.dump(yamlio.load(GOLDEN / "dependencies.yaml"), scan / "dependencies-2.yaml")
    res = assemble.assemble(scan, tmp_path / "out")
    assert any("multiple Dependencies" in v for v in res.validation)
