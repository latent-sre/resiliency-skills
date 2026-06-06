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


def test_malformed_yaml_is_reported_not_raised(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("a: : [\n", encoding="utf-8")
    problems = validate.validate_file(bad)
    assert problems and "could not parse" in problems[0]


def test_non_mapping_document_is_reported(tmp_path):
    f = tmp_path / "scalar.yaml"
    f.write_text("just a string\n", encoding="utf-8")
    problems = validate.validate_file(f)
    assert problems and "not a mapping" in problems[0]


def test_one_bad_file_does_not_abort_the_tree(tmp_path):
    # a malformed file must be reported but NOT blind the validator to its siblings
    (tmp_path / "bad.yaml").write_text("a: : [\n", encoding="utf-8")
    yamlio.dump(yamlio.load(GOLDEN / "criticality.yaml"), tmp_path / "good.yaml")
    problems = validate.validate_tree(tmp_path)
    assert any("could not parse" in p for p in problems)   # bad file surfaced
    assert all("good.yaml" not in p for p in problems)      # good sibling still validated (clean)
