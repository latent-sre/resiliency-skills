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
