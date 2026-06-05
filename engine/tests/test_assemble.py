"""End-to-end publish assembly: scan artifacts -> populated, validated, redacted SRE-<service> tree."""
import shutil
from pathlib import Path

from latent_sre import assemble

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden"
_ARTIFACTS = ["alert-intent.yaml", "criticality.yaml", "dependencies.yaml",
              "pcf-deployment.yaml", "runbook-spec.yaml"]


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
