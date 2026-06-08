"""CLI exit-code contract: 0 = ok, 1 = gate failure, 2 = bad input (missing/unreadable path)."""
import json

from latent_sre import cli


def test_app_names_missing_repo_returns_2(capsys):
    assert cli.main(["app-names", "/no/such/dir/xyz"]) == 2
    assert "app-names:" in capsys.readouterr().err  # clean message, not a stacktrace


def test_mermaid_missing_file_returns_2():
    assert cli.main(["mermaid", "/no/such/file.yaml"]) == 2


def test_validate_malformed_file_is_a_problem_not_a_crash(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("a: : [\n", encoding="utf-8")
    assert cli.main(["validate", str(bad)]) == 1
    assert "could not parse" in capsys.readouterr().err


def test_redact_json_output_is_machine_readable(tmp_path, capsys):
    secret = "AKIA" + "Q" * 16  # assembled so no secret-shaped literal lands in this repo
    (tmp_path / "creds.yaml").write_text(f"k: {secret}\n", encoding="utf-8")
    assert cli.main(["--json", "redact", str(tmp_path)]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "redact" and doc["blocked"] is True
    assert doc["findings"] and doc["findings"][0]["rule"] == "aws-access-key-id"


def test_validate_json_reports_ok(tmp_path, capsys):
    from pathlib import Path
    golden = Path(__file__).resolve().parents[2] / "examples" / "golden" / "criticality.yaml"
    assert cli.main(["--json", "validate", str(golden)]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc == {"command": "validate", "ok": True, "problems": []}


def test_scan_state_set_then_read_roundtrips(tmp_path, capsys):
    ss = tmp_path / "scan-state.yaml"
    assert cli.main(["scan-state-set", str(ss), "--service", "checkout",
                     "--skill", "assess-tech-stack", "--commit", "abc123"]) == 0
    assert cli.main(["scan-state", str(ss), "--service", "checkout",
                     "--skill", "assess-tech-stack"]) == 0
    assert "'status': 'done'" in capsys.readouterr().out
