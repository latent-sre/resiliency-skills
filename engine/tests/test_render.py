"""Adapter rendering: determinism, sentinels, and injection-safety (review items M2/S6)."""
import json
from pathlib import Path

from latent_sre import render, yamlio

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden" / "alert-intent.yaml"


def test_renders_prometheus_and_grafana():
    intent = yamlio.load(GOLDEN)
    prom = render.render_intent(intent, "prometheus")
    assert "alert:" in prom and "checkout-high-error-rate" in prom
    graf = render.render_intent(intent, "grafana")
    assert "checkout" in graf and "runbook_url" in graf


def test_missing_query_emits_failloud_sentinel():
    intent = {"metadata": {"name": "x", "service": "s"}, "spec": {"signal": {"type": "metric", "source": "splunk"}}}
    out = render.render_intent(intent, "splunk")
    assert "REPLACE_ME__" in out  # connection-critical fields fail loud, not silently wrong


def test_injection_in_service_name_is_safely_encoded():
    # A hostile service name must not break out of the JSON adapter structure.
    intent = {
        "metadata": {"name": "x", "service": '"]}injected\n{"evil":1'},
        "spec": {"signal": {"type": "metric", "source": "appdynamics"}, "severity": "sev3"},
    }
    out = render.render_intent(intent, "appdynamics")
    parsed = json.loads(out)  # must remain valid JSON
    assert parsed["affectedService"] == '"]}injected\n{"evil":1'


def test_render_is_deterministic():
    intent = yamlio.load(GOLDEN)
    assert render.render_intent(intent, "prometheus") == render.render_intent(intent, "prometheus")


def test_malicious_name_cannot_escape_output_dir(tmp_path):
    # A hostile metadata.name must not write outside out_dir (path traversal). assemble renders before
    # it validates, so render_file has to self-protect even against a schema-invalid name.
    intent = tmp_path / "intent.yaml"
    intent.write_text(
        "apiVersion: sre.latent-sre/v1\n"
        "kind: AlertIntent\n"
        "metadata:\n"
        "  name: '../../../pwned'\n"
        "  service: checkout\n"
        "spec:\n"
        "  signal: {type: metric, source: prometheus, query: up}\n"
        "  condition: {comparator: '<', threshold: 1}\n"
        "  severity: sev2\n"
        "  renderTargets: [prometheus]\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    written = render.render_file(intent, out)
    assert written
    for w in written:
        assert out.resolve() in w.resolve().parents      # stays under out_dir
    assert not (tmp_path / "pwned.yaml").exists()         # did not escape the tree


def test_empty_render_targets_renders_nothing(tmp_path):
    # An explicit empty renderTargets means "render nothing" — it must not fall back to all targets.
    intent = tmp_path / "intent.yaml"
    intent.write_text(
        "apiVersion: sre.latent-sre/v1\n"
        "kind: AlertIntent\n"
        "metadata:\n"
        "  name: x\n"
        "  service: s\n"
        "spec:\n"
        "  signal: {type: metric, source: prometheus}\n"
        "  condition: {comparator: '<', threshold: 1}\n"
        "  severity: sev3\n"
        "  renderTargets: []\n",
        encoding="utf-8",
    )
    assert render.render_file(intent, tmp_path / "out") == []


def _min_intent(severity="sev3", klass=None):
    spec = {"signal": {"type": "metric", "source": "prometheus", "query": "up"},
            "condition": {"comparator": "<", "threshold": 1}, "severity": severity}
    if klass:
        spec["class"] = klass
    return {"metadata": {"name": "x", "service": "s"}, "spec": spec}


def test_tier_raises_severity_floor():
    intent = _min_intent("sev3")
    assert '"sev3"' in render.render_intent(intent, "prometheus")                # no tier → declared
    assert '"sev1"' in render.render_intent(intent, "prometheus", tier="tier0")  # tier0 floors up to sev1


def test_tier_floor_never_lowers_severity():
    intent = _min_intent("sev1")
    assert '"sev1"' in render.render_intent(intent, "prometheus", tier="tier3")  # floor never lowers


def test_alert_class_is_rendered():
    out = render.render_intent(_min_intent("sev2", klass="cause"), "prometheus")
    assert "class:" in out and '"cause"' in out
