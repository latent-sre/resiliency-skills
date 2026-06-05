"""Scaffold lays down a complete, hardened SRE-<service> skeleton (review items S3/F13)."""
from latent_sre import scaffold


def test_scaffold_creates_hardened_skeleton(tmp_path):
    root = scaffold.scaffold(tmp_path / "SRE-checkout", "checkout")
    for rel in [
        "README.md", "catalog-info.yaml", ".github/CODEOWNERS",
        ".github/pull_request_template.md", ".github/workflows/validate.yml",
        ".sre/version", ".gitignore", ".provenance/scan.yaml",
    ]:
        assert (root / rel).is_file(), rel
    # vendored, pinned schemas + version
    assert list((root / ".sre" / "schemas").glob("*.schema.json"))
    assert "latent-sre==" in (root / ".sre" / "version").read_text()
    # forces human review; service name interpolated
    assert "REPLACE_ME__owning_team" in (root / ".github" / "CODEOWNERS").read_text()
    assert "SRE-checkout" in (root / "README.md").read_text()
    # generated CI validates against the vendored schemas, not this repo's main
    assert ".sre/schemas" in (root / ".github" / "workflows" / "validate.yml").read_text()


def test_clean_service_constrains_hostile_name():
    out = scaffold.clean_service('evil"];}-->`$(whoami)')
    assert out and all(c.isalnum() or c in "-_." for c in out)
