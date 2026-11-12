# -*- coding: utf-8 -*-
"""报告链路归一 · 回归测试（2026-11-12）。

三件事被钉住，防止再次分叉：

1. 六条结构门禁只有一份实现（`core/report_kernel/structure.guard`），
   r08 的 `htmlreport plan` 必须走它；
2. 报告 JSON → 内核 contract → 唯一渲染器，产出的 HTML 必须同时过
   契约校验与版式四规则（R1–R4）；
3. `role_runtime.emit` 对「有 spec 的角色」必须选内核，且可被环境变量回滚。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
REPO = TEAM.parent
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from core import report_renderer  # noqa: E402
from core.report_kernel import structure  # noqa: E402

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

DATASET = [
    {"date": "2026-10-01", "item": "复购率", "value": 62.0, "unit": "%", "source": "生意参谋"},
    {"date": "2026-10-31", "item": "复购率", "value": 64.0, "unit": "%", "source": "生意参谋"},
]


def _violations(report) -> list:
    return structure.guard(report)["violations"]


def test_good_report_passes_all_six_rules():
    gate = structure.guard(GOOD_REPORT)
    assert gate["ok"], gate["checks"]
    assert gate["violations"] == []


@pytest.mark.parametrize("mutate,rule", [
    (lambda r: r.update(title="   "), "S1"),
    (lambda r: r["meta"].pop("purpose"), "S2"),
    (lambda r: r.update(chapters=r["chapters"][:2]), "S3"),
    (lambda r: r["chapters"][0].pop("summary"), "S4"),
    (lambda r: r.update(thesis=r["thesis"][:2]), "S5"),
    (lambda r: r.update(sources=r["sources"][:2]), "S6"),
])
def test_each_rule_blocks(mutate, rule):
    report = {**GOOD_REPORT, "meta": dict(GOOD_REPORT["meta"]),
              "chapters": [dict(c) for c in GOOD_REPORT["chapters"]]}
    mutate(report)
    assert rule in _violations(report)


def test_contract_from_report_passes_renderer_and_layout():
    contract = structure.to_contract(GOOD_REPORT)
    assert report_renderer.validate_contract(contract) == []
    assert structure.layout_errors(contract, require_appendix=False) == []
    html = report_renderer.render(contract)
    assert html.startswith("<!doctype html>")
    assert "http" not in html
    assert "@media print" in html


def test_contract_with_dataset_carries_fidelity_and_appendix():
    contract = structure.to_contract({**GOOD_REPORT, "dataset": DATASET,
                                      "claims": [{"text": "复购 62%", "obs_ids": ["复购率"]}]})
    fid = contract["fidelity"]
    assert fid["obs_total"] == 2 and fid["retention"] == 1.0
    titles = [s["title"] for s in contract["sections"]]
    assert titles[-1] == "口径与分数"
    assert any(s.get("appendix") for s in contract["sections"])
    assert structure.layout_errors(contract) == []


def test_engine_choice_is_kernel_for_spec_roles(monkeypatch):
    from agents.shared import role_runtime
    monkeypatch.delenv(role_runtime.ENGINE_ENV, raising=False)
    assert role_runtime._engine_choice("r02") == "kernel"
    monkeypatch.setenv(role_runtime.ENGINE_ENV, "legacy")
    assert role_runtime._engine_choice("r02") == "legacy"


def test_r08_htmlreport_plan_uses_kernel_structure():
    """r08 的 plan 结果必须带 S1–S6 规则号（说明走的是内核那份实现）。"""
    r08 = TEAM / "r08-wajiancheng-mvp"
    if not (r08 / "agent.py").exists():
        pytest.skip("r08 不在本仓库")
    import json
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "r.json"
        src.write_text(json.dumps(GOOD_REPORT, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                   PYTHONPATH=str(TEAM) + os.pathsep + str(REPO))
        p = subprocess.run([sys.executable, str(r08 / "agent.py"), "htmlreport", "plan",
                            "--input", str(src)], cwd=str(r08), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    line = next((l for l in (p.stdout or "").splitlines() if l.startswith("__AGENT_RESULT__")), "")
    assert line, (p.stdout, p.stderr)
    out = json.loads(line[len("__AGENT_RESULT__ "):])
    assert out["verdict"] == "PASS"
    assert {c.get("rule") for c in out["checks"]} == {"S1", "S2", "S3", "S4", "S5", "S6"}
