# -*- coding: utf-8 -*-
"""R06 深度报告回归测试：验证「厚度 + 深度」不会再退化回三段文字。

守住的四条底线（任一破线即视为报告变薄，测试直接失败）：
    1. REP-001 五段式规格必须通过 `validate_spec` 门禁；
    2. 图表数 ≥ 3（趋势折线 + 归因瀑布 + 帕累托），且 HTML 里真的有 <svg>；
    3. 分析小节 ≥ 5（不是只有一个技能的单点结论）；
    4. 附录必须存在（质量六维原始读数要能审计），且产物字节数达标。
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE = os.path.dirname(HERE)
AGENTS = os.path.dirname(ROLE)
REPO = os.path.dirname(AGENTS)
for _p in (ROLE, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import deep_report  # noqa: E402
from agents.shared.report_generator import generate_professional_report, validate_spec  # noqa: E402

WS = os.path.join(ROLE, "workspace")
SERIES_CSV = os.path.join(WS, "parking_profit_12m.csv")
CROSS_CSV = os.path.join(WS, "parking_profit.csv")


def _build(out_dir):
    spec = deep_report.build(
        SERIES_CSV, "profit", "month", "zone", "month", "2025-09", "2025-10",
        "深度报告回归测试", None, decompose_input=CROSS_CSV)
    files = generate_professional_report(out_dir=out_dir, report_slug="deep_report",
                                         **spec)
    return spec, files


def test_deep_spec_passes_rep001(tmp_path):
    spec, _ = _build(str(tmp_path))
    violations = validate_spec(
        spec["report_title"], spec["executive_summary"], spec["decision_directive"],
        spec["kpi_metrics"], spec["analysis_sections"], spec["guardrails"],
        spec["rollout_plan"], spec["next_steps"], spec["rca"])
    assert not violations, f"REP-001 门禁未过: {violations}"


def test_figures_and_sections_have_depth(tmp_path):
    spec, files = _build(str(tmp_path))
    assert len(spec["figures"]) >= 3, "图表少于 3 张说明厚度不足"
    assert len(spec["analysis_sections"]) >= 5, "分析小节少于 5 节说明深度不足"
    assert spec["appendix"], "缺附录：原始明细无法审计"

    html = open(files["html"], encoding="utf-8").read()
    md = open(files["md"], encoding="utf-8").read()
    assert html.count("<svg") >= 3, "HTML 必须内嵌至少 3 张 SVG 图"
    for anchor in ("核心结论", "三级归因", "量化图谱", "护栏熔断",
                   "阶梯灰度", "附录"):
        assert anchor in html, f"HTML 缺板块：{anchor}"
    assert len(md.encode("utf-8")) > 6000, "Markdown 快读版过薄"
    assert "\ufffd" not in html and "\ufffd" not in md, "出现乱码"


def test_agent_py_deep_cli(tmp_path):
    """验证通过 agent.py 顶层 CLI 即可直接出具咨询级深度报告。"""
    import subprocess
    cmd = [
        sys.executable, "agent.py", "deep",
        "--series", SERIES_CSV,
        "--cross", CROSS_CSV,
        "--before", "2025-09",
        "--after", "2025-10",
        "--intent", "CLI出具深度报告自动化测试",
        "--out-dir", str(tmp_path)
    ]
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(cmd, cwd=ROLE, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert os.path.exists(os.path.join(tmp_path, "consulting_report.html"))
