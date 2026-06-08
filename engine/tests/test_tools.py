"""Coverage for the two repo-root CI gate scripts (tools/), which previously had no tests despite
being able to block a merge. Loaded by path since they're standalone scripts, not an installed pkg."""
import importlib.util
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lint_skills = _load("lint_skills")
second_secret_gate = _load("second_secret_gate")


# --- lint_skills frontmatter parser (hand-rolled, stdlib-only) ---

def test_frontmatter_inline_and_quoted():
    fm = lint_skills._frontmatter("---\nname: foo\ndescription: 'hello world'\n---\nbody\n")
    assert fm["name"] == "foo"
    assert fm["description"] == "hello world"  # surrounding quotes stripped


def test_frontmatter_folded_block_scalar_joins_with_space():
    text = "---\nname: foo\ndescription: >\n  line one\n  line two\n---\n"
    assert lint_skills._frontmatter(text)["description"] == "line one line two"


def test_frontmatter_literal_block_scalar_keeps_newlines():
    text = "---\nname: foo\ndescription: |\n  line one\n  line two\n---\n"
    assert lint_skills._frontmatter(text)["description"] == "line one\nline two"


def test_frontmatter_requires_opening_and_closing_fence():
    assert lint_skills._frontmatter("name: foo\n") == {}        # no opening fence
    assert lint_skills._frontmatter("---\nname: foo\n") == {}   # never closed


def test_lint_main_passes_on_real_repo():
    assert lint_skills.main() == 0  # the repo's own SKILL.md set must satisfy the lint


# --- second_secret_gate (detect-secrets wrapper) — mock the subprocess so the dep isn't required ---

class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_second_gate_blocks_on_findings(monkeypatch, capsys):
    out = json.dumps({"results": {"examples/x.yaml": [{"type": "AWS Access Key"}]}})
    monkeypatch.setattr(second_secret_gate.subprocess, "run", lambda *a, **k: _Proc(0, out))
    assert second_secret_gate.main() == 1
    assert "BLOCKED" in capsys.readouterr().err


def test_second_gate_clean(monkeypatch):
    monkeypatch.setattr(second_secret_gate.subprocess, "run",
                        lambda *a, **k: _Proc(0, json.dumps({"results": {}})))
    assert second_secret_gate.main() == 0


def test_second_gate_propagates_tool_failure(monkeypatch):
    monkeypatch.setattr(second_secret_gate.subprocess, "run",
                        lambda *a, **k: _Proc(2, stderr="detect-secrets exploded"))
    assert second_secret_gate.main() == 2  # a broken scanner must not read as "clean"
