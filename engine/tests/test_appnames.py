"""Monorepo fan-out discovery + cap (review item N2)."""
from latent_sre import appnames


def _write_manifest(path, app_names):
    apps = "\n".join(f"  - name: {n}" for n in app_names)
    path.write_text(f"applications:\n{apps}\n", encoding="utf-8")


def test_discovers_multiple_services(tmp_path):
    _write_manifest(tmp_path / "manifest.yml", ["checkout", "payments"])
    result = appnames.discover(tmp_path)
    assert set(result["services"]) == {"checkout", "payments"}
    assert result["requiresHumanConfirm"] is False


def test_fanout_cap_triggers_human_confirm(tmp_path):
    _write_manifest(tmp_path / "manifest.yml", [f"svc{i}" for i in range(appnames.FANOUT_CAP + 5)])
    result = appnames.discover(tmp_path)
    assert result["truncated"] is True
    assert result["requiresHumanConfirm"] is True
    assert len(result["services"]) == appnames.FANOUT_CAP


def test_hostile_name_is_cleaned(tmp_path):
    (tmp_path / "manifest.yml").write_text(
        "applications:\n  - name: 'evil\"];}-->`$(whoami)'\n", encoding="utf-8"
    )
    svc = appnames.discover(tmp_path)["services"][0]
    assert all(c.isalnum() or c in "-_." for c in svc)
