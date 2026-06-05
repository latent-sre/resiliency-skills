"""Dashboard spec -> Grafana JSON: valid by construction, sentinel datasource, injection-safe."""
import json
from pathlib import Path

from latent_sre import dashboard, yamlio

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden" / "dashboard.yaml"


def test_renders_valid_grafana_json():
    doc = json.loads(dashboard.render_dashboard(yamlio.load(GOLDEN)))
    assert doc["title"] == "Checkout overview"
    assert len(doc["panels"]) == 2
    assert "ai-drafted" in doc["tags"]


def test_datasource_is_a_failloud_sentinel():
    doc = json.loads(dashboard.render_dashboard(yamlio.load(GOLDEN)))
    assert all(p["datasource"].startswith("REPLACE_ME__") for p in doc["panels"])


def test_missing_query_uses_sentinel():
    spec = {"service": "s", "spec": {"title": "t", "panels": [{"title": "p", "type": "stat"}]}}
    doc = json.loads(dashboard.render_dashboard(spec))
    assert doc["panels"][0]["targets"][0]["expr"].startswith("REPLACE_ME__")


def test_injection_in_panel_title_is_escaped():
    spec = {"service": "s", "spec": {"title": '"]}evil', "panels": [{"title": '"}]inject', "type": "stat"}]}}
    doc = json.loads(dashboard.render_dashboard(spec))  # must remain valid JSON
    assert doc["title"] == '"]}evil'
    assert doc["panels"][0]["title"] == '"}]inject'


def test_render_dashboard_file_names_output(tmp_path):
    dest = dashboard.render_dashboard_file(GOLDEN, tmp_path)
    assert dest.name == "dashboard.json" and dest.is_file()
