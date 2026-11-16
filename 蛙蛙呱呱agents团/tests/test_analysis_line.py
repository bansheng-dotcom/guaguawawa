# -*- coding: utf-8 -*-
"""v4 分析产线：数据台 / 方法库 / 纲领 / 成稿 的回归测试。

这三个模块是一条线：
    analysis_desk.scan → analysis_methods.collect → report_thesis.resolve → report_compose.build

测试只锁三件事，不锁文案：
1. 价格口径归一正确（元/公斤 → 元/斤），否则后面全错；
2. 单位经济必须能复现参考报告的关键数字（白条鸡 +2.68、牛肉 −0.18、鸡蛋 −0.09）；
3. 端到端成稿必须过九条门禁，且技能覆盖 ≥5 / 角色 ≥3。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
for _p in (str(TEAM), str(TEAM.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import analysis_desk, analysis_methods, report_thesis  # noqa: E402

PROJECT = TEAM.parent / "内蒙古肉禽蛋调研_2026-11-12"


def _workdir(name: str) -> str:
    """沙箱里 tempfile.mkdtemp 会挂（0o700 切断继承 ACL），用仓库根 workspace 下的普通目录。"""
    d = TEAM.parent / "workspace" / name
    os.makedirs(d, exist_ok=True)
    return str(d)


def _ctx(tmp: str):
    desk = analysis_desk.scan(str(PROJECT))
    views = analysis_methods.build_views(desk)
    ctx = analysis_methods.Ctx(
        desk=desk, views=views, skills=analysis_methods.Skills(),
        cite=analysis_methods.Cite(desk),
        profile=analysis_desk.profile(desk), tmpdir=tmp)
    return desk, views, ctx


def test_scan_normalizes_price_units():
    desk = analysis_desk.scan(str(PROJECT))
    views = analysis_methods.build_views(desk)
    # 全区采价是 元/500克，批发市场报价是 元/公斤；两者都必须落到元/斤
    assert abs(views.snapshot["牛"][0] - 37.28) < 1e-6
    assert abs(views.wholesale["牛"][0] - 36.0) < 1e-6
    assert abs(views.wholesale["白条鸡"][0] - 8.5) < 1e-6
    assert views.series["鸡蛋"][0][1] > 0


def test_unit_economics_reproduces_reference_numbers():
    tmp = _workdir("_test_v4_eco")
    try:
        _desk, _views, ctx = _ctx(tmp)
        f = analysis_methods.m_economics(ctx)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rows = {r["key"]: r for r in f.meta["rows"]}
    assert abs(rows["白条鸡"]["net"].value - 2.68) < 0.01
    assert abs(rows["牛"]["net"].value + 0.18) < 0.01
    assert abs(rows["鸡蛋"]["net"].value + 0.09) < 0.01
    # 白条鸡净利率 22.4%（参考报告口径）
    assert abs(rows["白条鸡"]["margin"].value * 100 - 22.39) < 0.1


def test_transmission_excludes_non_comparable_live_cattle():
    tmp = _workdir("_test_v4_trans")
    try:
        _desk, _views, ctx = _ctx(tmp)
        f = analysis_methods.m_transmission(ctx)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    cats = {r["key"] for r in f.meta["rows"]}
    # 活牛/育肥牛与白条批发不是同一交易环节，不能算进产地→批发价差
    assert "牛" not in cats and "羊" not in cats
    assert "白条鸡" in cats


def test_thesis_inference():
    assert report_thesis.infer("牛肉与鸡蛋负毛利整改方案", {}) == "remediation"
    assert report_thesis.infer("内蒙古肉禽蛋经营诊断", {}) == "operations"
    assert report_thesis.infer("链路优化：六个断点", {}) == "chain"
    assert report_thesis.infer("2027 年一季度趋势预测", {}) == "forecast"
    assert report_thesis.infer("内蒙古肉禽蛋市场调研", {}) == "research"


def test_end_to_end_passes_gate():
    from core import report_compose
    from scripts.check_report_flow import check_html

    out = Path(_workdir("_test_v4_report"))
    try:
        res = report_compose.build(
            intent="内蒙古肉禽蛋市场调研", project_dir=str(PROJECT),
            out_dir=str(out), thesis="research")
        assert res["ok"], res
        assert res["sections"] >= 7
        # 图表绘制已内建到 core/report_renderer，不再走 r06 的 viz 技能，
        # 因此外部技能调用固定为 4 个（r06 explore/describe、r05 research、r04 artifact）
        assert res["covered"]["skills"] >= 4
        assert res["covered"]["roles"] >= 3
        gate = check_html(out / "report.html")
        assert gate["ok"], gate["violations"]
        assert gate["stats"]["density"] >= 25
        assert gate["stats"]["duplicate_rate"] <= 0.10
    finally:
        shutil.rmtree(out, ignore_errors=True)


# --------------------------------------------------------------------------- #
# v6：新业务研究（facts 驱动 + quote 校验 + 台账）
# --------------------------------------------------------------------------- #
NEW_BIZ = TEAM.parent / "新业务_内蒙古特色奶酪零食_2026-11-15"


def test_market_entry_plan_mounts_research_methods():
    from core import analysis_desk, analysis_methods, methods
    desk = analysis_desk.scan(str(NEW_BIZ))
    assert len(desk.facts) >= 30 and len(desk.assumptions) >= 5
    views = analysis_methods.build_views(desk)
    prof = analysis_desk.profile(desk)
    plan = methods.plan(desk, views, prof, "market_entry")
    mounted = {m["key"] for m in plan["mounted"]}
    assert {"sizing_multi", "growth", "concentration", "unit_econ",
            "entry_gate"} <= mounted
    # 价格类方法不应挂到研究项目上
    assert "economics" in {s["key"] for s in plan["skipped"]}


def test_market_entry_report_and_ledger():
    from core import report_compose, research_intake
    from scripts.check_report_flow import check_html

    out = Path(_workdir("_test_v6_entry"))
    try:
        led = research_intake.ledger(str(NEW_BIZ))
        assert led["verdict"] == "PASS", led
        assert led["coverage_rate"] == 1.0
        res = report_compose.build(
            intent="内蒙古特色奶酪零食新业务可行性", project_dir=str(NEW_BIZ),
            out_dir=str(out), thesis="market_entry")
        assert res["ok"], res
        assert {"sizing_multi", "unit_econ", "entry_gate"} <= set(res["findings"])
        gate = check_html(out / "report.html")
        assert gate["ok"], gate["violations"]
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_quote_normalization():
    from core.research_intake import _norm
    a = _norm("<p>2025年，我国奶酪需求量达42万吨，同比增长16.7%</p>")
    b = _norm("2025 年，我国奶酪需求量达 42 万吨，同比增长 16.7%")
    assert a == b
OLIST = TEAM.parent / "workspace" / "olist_v4_demo"


def test_method_registry_declares_capabilities():
    from core import methods
    cat = methods.catalog()
    assert len(cat) >= 20
    keys = {c["key"] for c in cat}
    assert {"structure", "economics", "funnel", "retention", "reviews",
            "sla", "roi", "priority", "incidents"} <= keys
    # 每个方法都必须声明「需要什么」，否则无法自动挂载
    assert all(c["needs"] for c in cat if c["key"] != "ledger")


def test_plan_mounts_by_data_shape():
    from core import analysis_desk, analysis_methods, methods
    desk = analysis_desk.scan(str(OLIST))
    views = analysis_methods.build_views(desk)
    prof = analysis_desk.profile(desk)
    plan = methods.plan(desk, views, prof, "growth")
    mounted = {m["key"] for m in plan["mounted"]}
    assert {"funnel", "retention", "rfm", "reviews", "sla", "payment_mix"} <= mounted
    # 没有价格数据，价格类方法必须被跳过（而不是产出一个空节）
    assert "economics" not in mounted
    assert "economics" in {s["key"] for s in plan["skipped"]}


def test_role_adapter_covers_20_roles():
    from core import report_roles
    cat = report_roles.classify()
    assert cat["counts"]["roles"] == 20
    assert cat["counts"]["skills"] >= 190
    assert cat["counts"]["eligible_skills"] >= 80
    assert all(i["category"] for i in cat["items"])
    # 未归类的技能必须显式排除，不能静默进报告
    assert all(not i["eligible"] for i in cat["items"] if i["category"] == "general")
    bad = [i for i in cat["items"] if i["category"] == "mutate"]
    assert bad and all(not i["eligible"] for i in bad)


def test_thesis_inference_cross_domain():
    from core import report_thesis
    assert report_thesis.infer("Olist 增长诊断", {}) == "growth"
    assert report_thesis.infer("客服履约复盘", {}) == "support"
    assert report_thesis.infer("招聘与人效", {}) == "people"
    assert report_thesis.infer("SLO 稳定性复盘", {}) == "sre"
    assert report_thesis.infer("商品结构诊断", {}) == "sku"
    assert report_thesis.infer("单店模型测算", {}) == "store"
    assert {"product", "growth", "support", "people", "sre",
            "marketing", "sku", "store"} <= set(report_thesis.THESES)


def test_growth_report_passes_gate():
    from core import report_compose
    from scripts.check_report_flow import check_html

    out = Path(_workdir("_test_v5_growth"))
    try:
        res = report_compose.build(
            intent="Olist 增长诊断", project_dir=str(OLIST),
            out_dir=str(out), thesis="growth")
        assert res["ok"], res
        assert res["thesis"] == "growth"
        assert {"funnel", "retention"} <= set(res["findings"])
        gate = check_html(out / "report.html")
        assert gate["ok"], gate["violations"]
    finally:
        shutil.rmtree(out, ignore_errors=True)
