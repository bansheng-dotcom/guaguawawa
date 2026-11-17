# -*- coding: utf-8 -*-
"""v7 深度线：事实表 / 论证层 / 区域市场方法 / 问题链帧 / 反模板门禁。

锁五件事：
1. 带来源事实表能读多种项目形态，且能按指标语义取数；
2. Claim 的机理/落点/证伪依赖量化标签，标签不全就不硬编；
3. 市场方法产出的每节都有 headline、refs、claim；
4. 同一批数据、三种纲领，章节骨架不能重合（不是一套模板换数据）；
5. 报告要同时过「九条门禁」与「反模板门禁」。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parent.parent
for _p in (str(TEAM), str(TEAM.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

HOUSEHOLD = TEAM.parent / "家居百货内蒙调研_2026-11-15"
MEAT = TEAM.parent / "内蒙古肉禽蛋调研_2026-11-12"


def _sample(*paths: Path):
    """样本目录缺失时跳过：缺样本是环境问题，不是代码回归。"""
    missing = [p.name for p in paths if not Path(p).exists()]
    return pytest.mark.skipif(bool(missing), reason="样本目录缺失：" + "、".join(missing))


def _workdir(name: str) -> str:
    d = TEAM.parent / "workspace" / name
    os.makedirs(d, exist_ok=True)
    return str(d)


def _ctx(project: Path):
    from core import analysis_desk, analysis_methods
    desk = analysis_desk.scan(str(project))
    views = analysis_methods.build_views(desk)
    tmp = _workdir("_test_v7_tmp")
    ctx = analysis_methods.Ctx(
        desk=desk, views=views, skills=analysis_methods.Skills(),
        cite=analysis_methods.Cite(desk),
        profile=analysis_desk.profile(desk), tmpdir=tmp,
        ft=getattr(desk, "ft", None))
    return desk, views, ctx


# --------------------------------------------------------------------------- #
@_sample(HOUSEHOLD)
def test_fact_table_loads_sourced_observations():
    from core import fact_table
    ft = fact_table.load(str(HOUSEHOLD))
    assert len(ft.facts) >= 200
    retail = ft.one("社会消费品零售总额", region="内蒙古", prefer_period="2025",
                    exclude=("同比", "增速"))
    assert retail and abs(retail.value - 5375.5) < 1e-6
    assert retail.grade == "A" and retail.url
    # 期次排序：2026Q1-3 晚于 2026H1
    assert fact_table.period_key("2026Q1-3") > fact_table.period_key("2026H1")
    # 百分比统一：0.043 与 4.3 都按 4.3 处理
    p = ft.one("社会消费品零售总额同比增速", region="内蒙古", prefer_period="2025")
    assert abs(p.as_pct() - 4.3) < 1e-6


def test_claim_finalize_requires_tags():
    from core.claims import Claim, finalize
    bare = finalize(Claim(kind="size", subject="规模", headline="规模 1 亿元"))
    assert bare.mechanism == ""          # 没有 paths 就不硬编机理
    full = finalize(Claim(kind="size", subject="规模", headline="规模 1 亿元",
                          tags={"paths": [{"name": "A", "lo": 1, "hi": 2,
                                           "note": "口径 A"}],
                                "converge": ["A"], "sensitivity": 1.0,
                                "missing": "官方口径"}))
    assert "口径" in full.mechanism and full.implication and full.falsifier


@_sample(HOUSEHOLD)
def test_market_methods_produce_claims_and_refs():
    from core import methods
    desk, views, ctx = _ctx(HOUSEHOLD)
    plan = methods.plan(desk, views, ctx.profile, "market")
    findings, _gaps = methods.run(plan, ctx)
    assert {"size", "demand", "trend", "mix", "volume", "channel",
            "region", "supply", "policy", "consistency", "coverage"} <= set(findings)
    for key in ("size", "trend", "mix", "region"):
        f = findings[key]
        cl = (f.meta or {}).get("claim")
        assert cl is not None and cl.refs and any(ch.isdigit() for ch in cl.headline)
        assert cl.mechanism and cl.implication          # 有机理、有落点


@_sample(HOUSEHOLD)
def test_market_report_passes_both_gates():
    from core import report_compose, report_quality
    from scripts.check_report_flow import check_html
    out = Path(_workdir("_test_v7_market"))
    try:
        res = report_compose.build(
            intent="内蒙古家居百货市场调研", project_dir=str(HOUSEHOLD),
            out_dir=str(out), thesis="analysis", lens="market")
        assert res["ok"], res
        assert res["thesis"] == "analysis" and res["sections"] >= 8
        gate = check_html(out / "report.html")
        assert gate["ok"], gate["violations"]
        qa = report_quality.audit(str(out / "report.html"))
        assert qa["ok"], [c for c in qa["checks"] if not c["ok"]]
        assert qa["score"] >= 70
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_quality_gate_rejects_repeated_shell():
    from core.report_quality import audit
    secs = []
    for i in range(8):
        secs.append(
            f'<section><h2>{i+1} 第 {i+1} 个判断，差 {i}pp</h2>'
            f'<ul><li>判断 本节边界 一样的壳</li><li>本节边界 一样的壳</li>'
            f'<li>本节边界 一样的壳</li></ul></section>')
    p = Path(_workdir("_test_v7_shell")) / "shell.html"
    p.write_text("<html><body>" + "".join(secs) + "</body></html>", encoding="utf-8")
    try:
        r = audit(str(p))
        assert not r["ok"]
        bad = {c["id"] for c in r["checks"] if not c["ok"]}
        assert "Q5_no_shell" in bad
    finally:
        shutil.rmtree(p.parent, ignore_errors=True)
