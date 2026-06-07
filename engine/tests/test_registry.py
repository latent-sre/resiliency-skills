"""The single kind registry stays in sync with schemas, render targets, and the validate contract."""
import json
from pathlib import Path

from latent_sre import registry, render, validate, yamlio

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"


def test_every_data_kind_has_a_schema_file():
    for k in registry.DATA_KINDS:
        assert (SCHEMAS / f"{k.schema}.schema.json").is_file(), k.kind


def test_render_targets_match_alert_schema_enum():
    schema = json.loads((SCHEMAS / "alert-intent.schema.json").read_text())
    enum = schema["properties"]["spec"]["properties"]["renderTargets"]["items"]["enum"]
    assert sorted(render.TARGETS) == sorted(enum)  # code TARGETS must not drift from the schema enum


def test_control_kind_is_recognized_not_errored(tmp_path):
    p = tmp_path / "plan.yaml"
    yamlio.dump({"apiVersion": "sre.latent-sre/v1", "kind": "ScanPlan", "services": []}, p)
    assert validate.validate_file(p) == []  # control-plane kind: recognized, not "no schema found"


def test_unknown_kind_is_reported(tmp_path):
    p = tmp_path / "weird.yaml"
    yamlio.dump({"apiVersion": "sre.latent-sre/v1", "kind": "TotallyMadeUp"}, p)
    problems = validate.validate_file(p)
    assert problems and "unknown or missing kind" in problems[0]
