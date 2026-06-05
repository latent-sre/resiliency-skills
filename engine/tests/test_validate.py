"""Schema validation: golden fixtures pass; governance gaps and stray keys fail (review items M7/F4)."""
from pathlib import Path

from latent_sre import validate, yamlio

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden"


def test_golden_fixtures_validate():
    golden = sorted(GOLDEN.glob("*.yaml"))
    assert golden, "no golden fixtures found"
    for path in golden:
        assert validate.validate_file(path) == [], path.name


def test_missing_governance_field_fails(tmp_path):
    doc = yamlio.load(GOLDEN / "criticality.yaml")
    del doc["needs-human-review"]  # drop a required governance field
    p = tmp_path / "bad.yaml"
    yamlio.dump(doc, p)
    assert validate.validate_file(p), "missing needs-human-review must fail"


def test_unknown_field_rejected_by_allowlist(tmp_path):
    doc = yamlio.load(GOLDEN / "criticality.yaml")
    doc["leaked_extra_field"] = "some copied value"  # not in the positive allow-list
    p = tmp_path / "extra.yaml"
    yamlio.dump(doc, p)
    assert validate.validate_file(p), "additionalProperties:false must reject stray keys"
