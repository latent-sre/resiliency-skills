"""RunbookSpec -> Markdown rendering, incl. step injection-flattening."""
from pathlib import Path

from latent_sre import runbook, yamlio

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "examples" / "golden" / "runbook-spec.yaml"


def test_renders_expected_sections():
    md = runbook.render_runbook(yamlio.load(GOLDEN))
    assert md.startswith("# Runbook: Checkout 5xx error rate high")
    for heading in ["## Summary", "## Signals", "## Triage", "## Mitigation", "## Escalation", "## Links"]:
        assert heading in md
    assert "needs human review" in md.lower()


def test_step_newline_cannot_inject_a_heading():
    spec = {"service": "s", "spec": {"title": "t", "triage": ["legit step\n## Injected Heading\n- x"]}}
    md = runbook.render_runbook(spec)
    # the newline is collapsed, so the payload can't become its own heading/list line
    assert not any(line.startswith("## Injected") for line in md.splitlines())


def test_render_runbook_file_names_output(tmp_path):
    dest = runbook.render_runbook_file(GOLDEN, tmp_path)
    assert dest.name == "runbook-spec.md" and dest.is_file()
