# -*- coding: utf-8 -*-
"""报告规格测试：REP-001 五段式必须齐备（决策指令/KPI/归因/护栏/灰度）。"""
import argparse
import importlib
import json
import os

from agents.shared.report_engine import build_report_spec, derive_verdict
from agents.shared.report_generator import validate_spec

ROLE = "r04"
SKILL = "artifact"
ACTION = "verify"
EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "examples", "artifact_verify.json")


def _result() -> dict:
    from skills import SKILLS
    mod = next(m for m in SKILLS if m.NAME == SKILL)
    if hasattr(mod, "run"):
        out = mod.run(argparse.Namespace(action=ACTION, input=EXAMPLE))
    else:
        with open(EXAMPLE, encoding="utf-8-sig") as f:
            out = getattr(mod, ACTION)(json.load(f))
    return out if isinstance(out, dict) else {"ok": True}


def test_spec_passes_rep001_gate():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图",
                             input_path=EXAMPLE)
    violations = validate_spec(
        spec["report_title"], spec["executive_summary"], spec["decision_directive"],
        spec["kpi_metrics"], spec["analysis_sections"], spec["guardrails"],
        spec["rollout_plan"], spec["next_steps"], spec["rca"])
    assert not violations, f"REP-001 门禁未过: {violations}"


def test_spec_has_three_level_rca():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    levels = [r["level"] for r in spec["rca"]]
    assert levels == ["L1", "L2", "L3"]


def test_rollout_is_staged():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    assert len(spec["rollout_plan"]) >= 2, "禁止一键全量，至少两档灰度"
    scopes = " ".join(p["scope"] for p in spec["rollout_plan"])
    assert "5%" in scopes or "20%" in scopes


def test_guardrails_have_threshold():
    spec = build_report_spec(ROLE, _result(), SKILL, ACTION, "单元测试意图")
    for g in spec["guardrails"]:
        assert g.get("threshold"), "每条护栏必须有熔断阈值"


def test_verdict_is_normalized():
    assert derive_verdict({"verdict": "PASS"}) == "PASS"
    assert derive_verdict({"verdict": "BLOCKED"}) == "FAIL"
    assert derive_verdict({"ok": False}) == "FAIL"
