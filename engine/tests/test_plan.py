"""Orchestration & scale: the `plan` command + canonical pipeline over a sample target repo."""
from pathlib import Path

from latent_sre import appnames, assemble, plan, scanstate

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples" / "sample-target"
GOLDEN = ROOT / "examples" / "golden"


def test_pipeline_covers_every_skill_exactly_once():
    skills = [s for _, s in plan._ordered_skills(plan.load_pipeline())]
    declared = sorted(p.parent.name for p in (ROOT / ".github" / "skills").glob("*/SKILL.md"))
    assert sorted(skills) == declared
    assert len(skills) == len(set(skills))  # no skill listed twice


def test_plan_discovers_services_and_orders_skills():
    p = plan.make_plan(SAMPLE)
    assert p["kind"] == "ScanPlan"
    assert [s["service"] for s in p["services"]] == ["checkout", "payments"]
    assert p["requiresHumanConfirm"] is False
    steps = p["services"][0]["skills"]
    assert steps[0]["phase"] == "classify"  # the discover phase contributes no skills
    assert [s["skill"] for s in steps[:2]] == ["assess-tech-stack", "assess-criticality-and-data"]
    assert {s["status"] for s in steps} == {"pending"}


def test_plan_annotates_resume_status_per_service(tmp_path):
    ss = tmp_path / "scan-state.yaml"
    scanstate.mark(ss, "checkout", "assess-tech-stack", "abc123", "0.1.0", "out", "h", status="done")
    p = plan.make_plan(SAMPLE, scan_state_path=ss)
    by = {s["service"]: s for s in p["services"]}
    checkout_done = [s["skill"] for s in by["checkout"]["skills"] if s["status"] == "done"]
    payments_done = [s["skill"] for s in by["payments"]["skills"] if s["status"] == "done"]
    assert checkout_done == ["assess-tech-stack"]
    assert payments_done == []  # resume is per-service — a sibling is NOT falsely reported done


def test_plan_fanout_above_cap_requires_human(tmp_path):
    apps = "".join(f"  - name: svc{i}\n" for i in range(appnames.FANOUT_CAP + 5))
    (tmp_path / "manifest.yml").write_text("applications:\n" + apps)
    p = plan.make_plan(tmp_path)
    assert p["requiresHumanConfirm"] is True
    assert p["fanout"]["total"] == appnames.FANOUT_CAP + 5
    assert p["fanout"]["truncated"] is True


def test_integration_discover_plan_assemble(tmp_path):
    # Discover + plan over the sample target, then assemble the (model-produced) golden artifacts
    # into the first service's hardened repo — the full deterministic orchestration chain.
    p = plan.make_plan(SAMPLE)
    service = p["services"][0]["service"]
    res = assemble.assemble(GOLDEN, tmp_path / "out", service)
    assert res.ok, (res.validation, res.secrets)
    assert res.service == service
    assert res.written and res.root.exists()
