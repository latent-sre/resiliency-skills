"""CLI exit-code contract: 0 = ok, 1 = gate failure, 2 = bad input (missing/unreadable path)."""
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
