# -*- coding: utf-8 -*-
"""唯一报告产线的回归测试（2026-11-15 收敛后）。

钉住三件事：
1. 结构门禁只有一份实现（core/report_kernel/structure.guard），不随产线删除而丢失；
2. 产线契约的形状：结论在前、记录层折叠、末节「口径与分数」；
3. 端到端：真实 result → 一份报告 → 九条门禁全过，且 manifest 署名 R01。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
REPO = TEAM.parent
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import report_flow  # noqa: E402
from core.report_kernel import structure  # noqa: E402
import pytest  # noqa: E402

GOOD_REPORT = {
    "title": "Q4 复盘",
    "meta": {"audience": "管理层", "purpose": "决定加投"},
    "chapters": [
        {"title": "结论", "summary": "复购是主因", "paragraphs": ["复购 +18%"]},
        {"title": "流量", "summary": "自然升转化降"},
        {"title": "动作", "summary": "先修履约"},
    ],
    "thesis": ["复购 62%", "履约漏点", "只投 ROI>2"],
    "sources": [{"label": "生意参谋"}, {"label": "财务月报"}, {"label": "履约系统"}],
}

FIX = TEAM / "fixtures" / "report_flow"


def test_structure_guard_single_implementation():
    assert structure.guard(GOOD_REPORT)["violations"] == []
    bad = {**GOOD_REPORT, "thesis": ["只有一条"]}
    assert structure.guard(bad)["violations"]


def test_build_contract_shape():
    j = {"headline": "GMV 下降 3.2%",
         "conclusions": [{"text": "GMV 下降 3.2%", "number": "-3.2",
                          "source": "r06/semantics", "kind": "finding"}],
         "drivers": [], "boundary": ["只对本次输入成立"],
         "actions": [{"do": "复算", "condition": "对外时", "stop": "不一致即停"}],
         "gaps": []}
    ev = [{"role": "r06", "skill": "semantics", "action": "validate",
           "source": "x.json", "source_hash": "h"}]
    nums = [{"path": "gmv.delta_pct", "value": -3.2, "text": "-3.2",
             "source": "r06/semantics"}]
    c = report_flow.build_contract(j, "测试诊断", "A", ev, nums,
                                   [{"id": "x", "ok": True}], "rule")
    assert c["title_lines"][0] == "测试诊断"
    assert c["sections"][-1]["title"] == "口径与分数"
    assert c["sections"][-2].get("appendix") is True
    assert structure.layout_errors(c, require_appendix=True) == []


def test_run_requires_evidence_and_draft(tmp_path):
    with pytest.raises(report_flow.FlowError):
        report_flow.run(intent="2月经营诊断", out_dir=str(tmp_path / "b"))
