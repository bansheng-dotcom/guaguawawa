# -*- coding: utf-8 -*-
"""charts 域测试（合并自 7 个文件）。

源文件：
    test_chart_candidates.py —— test_chart_candidates —— S4 候选面板与校验单测。
    test_chart_contract.py —— test_chart_contract —— S3 统一契约 v2 的归一化（三条线）单测。
    test_chart_echarts.py —— P5-4：ECharts 交互后端（可选），静态 SVG 仍是兜底。
    test_chart_fit.py —— P4：数据画像 → 候选图型；图型契约同源审计。
    test_chart_layout.py —— P4-3：Layout 层在 70 型渲染前统一接管空态/值域/刻度/精度。
    test_chart_payload.py —— test_chart_payload —— payload 构建器单测。
    test_theme_tokens.py —— P5：设计 token 默认值 = 现状；表格降级可访问。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


from core.charts import chart_candidates as cc_cand
import importlib.util
import json
from core.charts import chart_contract as cc
import os
from core.report_theme.charts_pro import interactive, layout
from core.charts import chart_field_contract as chart_contract
from core.data import data_standard as ds
from core.report_theme.charts_pro import layout, spec
from core.charts.chart_payload import build_payload
from core.data import data_standard as ds
from core.report_theme import tokens

from core.charts import chart_query as cq



# ====================================================================
# 合并自 test_chart_candidates.py：test_chart_candidates —— S4 候选面板与校验单测。
# ====================================================================
# -*- coding: utf-8 -*-


def test_candidates_ranking_needs_entity():
    cands = cc_cand.candidates({"relation": "ranking", "dims": [{"name": "entity"}]})
    types = {c["type"] for c in cands}
    assert types, "ranking 应有候选"
    assert "scatter" not in types  # 二维类不该出现在只有 entity 的 ranking 候选里


def test_validate_line_change_over_time():
    r = cc_cand.validate({"relation": "change_over_time", "chosen": "line",
                     "dims": [{"name": "period"}]})
    assert r["ok"] is True


def test_validate_hbar_not_change():
    r = cc_cand.validate({"relation": "change_over_time", "chosen": "hbar", "dims": []})
    assert r["ok"] is False
    assert "hbar" not in r["allowed"]


def test_validate_scatter_needs_entity():
    r = cc_cand.validate({"relation": "correlation", "chosen": "scatter", "dims": []})
    assert r["ok"] is False


# ====================================================================
# 合并自 test_chart_contract.py：test_chart_contract —— S3 统一契约 v2 的归一化（三条线）单测。
# ====================================================================
# -*- coding: utf-8 -*-


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chart_contract_sections.json"


def _load_chart_contract_sections():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["sections"]


def test_relation_from_comparison_kind():
    # A 线：comparison.kind 优先映射
    n = cc.normalize({"type": "hbar"},
                     {"comparison": {"kind": "compare_two_points"}}, {})
    assert n["relation"] == "ranking"


def test_relation_from_type_fallback():
    # 无 comparison/relation 时由 type 反查
    n = cc.normalize({"type": "dumbbell"}, {}, {})
    assert n["relation"] == "ranking"


def test_dims_from_entity_and_period():
    n = cc.normalize({"type": "hbar", "refs": ["N1", "N2"]}, {},
                     {"N1": {"entity": "包头"}, "N2": {"entity": "包头", "period": "2026-11"}})
    names = {d["name"] for d in n["dims"]}
    assert names == {"entity", "period"}


def test_claims_line_all_sections_normalize():
    for s in _load_chart_contract_sections():
        if not s.get("chart"):
            continue
        n = cc.normalize(s["chart"], s, {})
        assert n["chosen"] == s["chart"].get("type")
        assert n["relation"] in cc.INTENT_LABEL


# ====================================================================
# 合并自 test_chart_echarts.py：P5-4：ECharts 交互后端（可选），静态 SVG 仍是兜底。
# ====================================================================
# -*- coding: utf-8 -*-


def _prep(chart):
    from core.report_theme.charts_pro import compat
    s = compat.to_spec(chart)
    assert s
    return layout.prepare(s)


def test_hbar_option_keeps_values_and_unit():
    opt = interactive.to_option(_prep({
        "type": "hbar", "title": "t", "unit_meta": "件",
        "bars": [{"label": "甲", "value": 12}, {"label": "乙", "value": 7}]}))
    assert opt and opt["series"][0]["type"] == "bar"
    vals = [d["value"] for d in opt["series"][0]["data"]]
    assert vals == [12.0, 7.0]
    assert "件" in opt["tooltip"]["valueFormatter"]


def test_line_option_has_series_and_axis():
    opt = interactive.to_option(_prep({
        "type": "line", "xlabels": ["p1", "p2", "p3"],
        "series": [{"name": "甲", "values": [1, 2, 3]}]}))
    assert opt["xAxis"]["data"] == ["p1", "p2", "p3"]
    assert opt["series"][0]["data"] == [1.0, 2.0, 3.0]


def test_pie_and_heatmap_options():
    pie = interactive.to_option(_prep({
        "type": "donut", "bars": [{"label": "a", "value": 3},
                                  {"label": "b", "value": 5}]}))
    assert pie["series"][0]["type"] == "pie"
    hm = interactive.to_option(_prep({
        "type": "heatmap", "rows": ["r1", "r2"], "cols": ["c1", "c2"],
        "matrix": [[1, -2], [3, 4]]}))
    assert hm["series"][0]["type"] == "heatmap"
    assert [d[2] for d in hm["series"][0]["data"]] == [1.0, -2.0, 3.0, 4.0]


def test_unsupported_type_returns_none():
    assert interactive.supported("network") is False
    assert interactive.to_option({"type": "network", "_layout": {"decimals": 1}}) is None
    assert interactive.render_chart({"type": "network"}) is None


def test_render_html_contains_cdn_init_and_svg_fallback():
    html = interactive.render_chart({
        "type": "hbar", "title": "t", "unit_meta": "件",
        "bars": [{"label": "甲", "value": 12}]})
    assert html and "echarts.min.js" in html and "echarts.init" in html
    assert "echart-fallback" in html and "<svg" in html
    assert "12" in html


def test_render_spec_accepts_canonical_chart_spec():
    html = interactive.render_spec({
        "type": "hbar", "unit_meta": "件",
        "items": [{"label": "甲", "value": 3}, {"label": "乙", "value": 5}]})
    assert html and "echarts.init" in html and "echart-fallback" in html
    assert "5" in html


def test_pages_backend_switch(monkeypatch):
    from core.report_theme import pages
    monkeypatch.setenv("GUAGUA_CHART_BACKEND", "echarts")
    body, engine = pages._render_svg({
        "type": "hbar", "title": "t", "bars": [{"label": "甲", "value": 1}]})
    assert engine == "echarts" and "echarts.init" in body
    monkeypatch.delenv("GUAGUA_CHART_BACKEND", raising=False)
    body2, engine2 = pages._render_svg({
        "type": "hbar", "title": "t", "bars": [{"label": "甲", "value": 1}]})
    assert engine2 in ("pro", "legacy") and "<svg" in body2


# ====================================================================
# 合并自 test_chart_fit.py：P4：数据画像 → 候选图型；图型契约同源审计。
# ====================================================================
# -*- coding: utf-8 -*-


def _ds(pairs, unit="元"):
    obs = [ds.Observation(metric_id="m", entity=e, period=p, value=v, unit=unit)
           for e, p, v in pairs]
    d = ds.Dataset(name="demo", grain=["entity", "period"], observations=obs)
    d.profile = ds.profile_observations(obs)
    return d




def test_required_of_resolves_alias():
    assert chart_contract.required_of("share") == chart_contract.required_of("share_bar")


def test_contract_audit_detects_missing_field():
    bad = {"hbar": {"type": "hbar"}}
    a = chart_contract.contract_audit(bad)
    assert not a["ok"] and a["mismatch"][0]["missing_in_sample"] == ["items"]


def test_build_spec_does_not_embed_numbers():
    d = _ds([("甲", "2025-01", 1.0), ("乙", "2025-02", 2.0)])
    cs = chart_contract.build_spec(d, "line", title="趋势")
    assert cs.chart_type == "line"
    assert cs.data_ref["dataset"] == "demo"
    assert "values" not in cs.to_dict()
    assert ds.validate_chart_spec(cs) == []


def test_real_samples_match_contract_if_available():
    try:
        from samples import samples  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return
    a = chart_contract.contract_audit(samples.SAMPLE)
    assert a["ok"], a["mismatch"][:3]


# ====================================================================
# 合并自 test_chart_layout.py：P4-3：Layout 层在 70 型渲染前统一接管空态/值域/刻度/精度。
# ====================================================================
# -*- coding: utf-8 -*-


try:
    from samples import samples  # noqa: PLC0415
except Exception:  # noqa: BLE001
    samples = None

KINDS = spec.kinds()
NUMERIC_REQ = {"start", "low", "high", "value", "target"}


def test_every_kind_gets_layout():
    if samples is None:
        return
    for t in KINDS:
        prepared = layout.prepare(dict(samples.SAMPLE[t], type=t))
        lay = prepared[layout.LAYOUT_KEY]
        assert lay["type"] == t
        assert isinstance(lay["decimals"], int)
        assert lay["domain"][0] <= 0 <= lay["domain"][1]
        assert lay["tick"] > 0
        assert prepared["decimals"] == lay["decimals"]
        assert "required" in lay and lay["required"] == list(spec.REQUIRED[t])


def test_every_kind_renders_through_layout():
    if samples is None:
        return
    for t in KINDS:
        svg = spec.render(dict(samples.SAMPLE[t], type=t))
        assert "<svg" in svg and "</svg>" in svg, t


def test_empty_state_is_uniform_across_kinds():
    checked = 0
    for t in KINDS:
        req = list(spec.REQUIRED[t])
        if any(k in NUMERIC_REQ for k in req):
            continue          # 数值必填型（gauge 等）不适用「空列表」语义
        empty = {k: ([] if req else None) for k in req}
        out = spec.render({"type": t, **empty})
        assert "<svg" in out and "无数据" in out, t
        checked += 1
    assert checked >= 60      # 绝大多数图型都应走统一空态


def test_negative_domain_is_injected():
    p = layout.prepare({"type": "hbar",
                        "items": [{"label": "a", "value": -5},
                                  {"label": "b", "value": 3}]})
    lay = p[layout.LAYOUT_KEY]
    assert lay["negative"] is True
    assert lay["domain"][0] < 0 <= lay["domain"][1]
    assert p["domain"] == tuple(lay["domain"])


def test_flat_values_flagged():
    p = layout.prepare({"type": "line",
                        "points": [{"label": "a", "value": 2},
                                   {"label": "b", "value": 2}]})
    assert p[layout.LAYOUT_KEY]["flat"] is True


def test_alias_gets_layout_for_real_type():
    p = layout.prepare({"type": "share", "items": [{"label": "a", "value": 1}]})
    assert p["type"] == "share_bar"
    assert p[layout.LAYOUT_KEY]["type"] == "share_bar"


# ====================================================================
# 合并自 test_chart_payload.py：test_chart_payload —— payload 构建器单测。
# ====================================================================
# -*- coding: utf-8 -*-


FACTS = [
    {"id": "F1", "metric": "采购价", "entity": "大白菜", "value": 1.2, "unit": "元"},
    {"id": "F2", "metric": "运费", "entity": "大白菜", "value": 0.3, "unit": "元"},
    {"id": "F3", "metric": "采购价", "entity": "土豆", "value": 1.0, "unit": "元"},
    {"id": "F4", "metric": "运费", "entity": "土豆", "value": 0.4, "unit": "元"},
]


def test_items_payload():
    p = build_payload("treemap", FACTS)
    assert len(p["items"]) == 4
    assert p["items"][0] == {"label": "大白菜", "value": 1.2}


def test_histogram_payload():
    p = build_payload("histogram", FACTS)
    assert p["values"] == [1.2, 0.3, 1.0, 0.4]


def test_box_groups_by_entity():
    p = build_payload("box", FACTS)
    labels = {g["label"] for g in p["groups"]}
    assert labels == {"大白菜", "土豆"}
    for g in p["groups"]:
        assert len(g["values"]) == 2


def test_stacked_categories_series():
    p = build_payload("stacked", FACTS)
    assert set(p["categories"]) == {"大白菜", "土豆"}
    assert {s["name"] for s in p["series"]} == {"采购价", "运费"}
    # 每系列值数与 categories 对齐
    for s in p["series"]:
        assert len(s["values"]) == len(p["categories"])


def test_line_payload():
    p = build_payload("line", FACTS)
    assert len(p["points"]) == 4


def test_unknown_type_empty():
    assert build_payload("nonsense", FACTS) == {}


# ====================================================================
# 合并自 test_theme_tokens.py：P5：设计 token 默认值 = 现状；表格降级可访问。
# ====================================================================
# -*- coding: utf-8 -*-


def _dataset():
    obs = [ds.Observation(metric_id="m", entity=e, period="2025", value=v, unit="元")
           for e, v in (("甲", 1.0), ("乙", 2.0))]
    d = ds.Dataset(name="示例", grain=["entity", "period"], observations=obs)
    d.profile = ds.profile_observations(obs)
    return d


def test_default_tokens_match_renderer():
    assert tokens.verify_defaults_match_renderer() == []


def test_load_theme_overrides_color(tmp_path):
    p = tmp_path / "theme.yaml"
    p.write_text("color:\n  accent: '#0055AA'\n", encoding="utf-8")
    tk = tokens.load(p)
    assert tk["color"]["accent"] == "#0055AA"
    assert tk["color"]["ink"] == tokens.DEFAULT_TOKENS["color"]["ink"]


def test_css_vars_contains_tokens():
    css = tokens.css_vars()
    assert "--chart-ink:" in css and css.startswith(":root{")


# 2026-11-26：table_backend 删除（无任何产线引用；表格渲染由 report_flow._table 承担）


# ====================================================================
# 合并自 test_chart_query.py（原为无 pytest 的脚本式自测，2026-11-25 转正）
# ====================================================================
def _cq_row(i, mid, entity, period, value, segment="", unit="亿元"):
    return {"row_id": f"R{i}", "number_id": f"r05:N{i}", "metric_id": mid,
            "metric_name": "某品类规模", "entity": entity, "period": period,
            "value": value, "segment": segment, "unit": unit}


def test_chart_query_matrix():
    rs, n = [], 0
    for e in ("朝阳", "海淀", "丰台", "通州", "昌平", "大兴", "顺义", "石景山"):
        for s in ("主粮", "零食", "用品"):
            n += 1
            rs.append(_cq_row(n, "m1", e, "2025", 10 + n, s))
    ch = cq.build(rs, "m1")
    assert ch["type"] == "heatmap"
    assert len(ch["rows"]) == 8 and len(ch["cols"]) == 3
    assert sum(1 for r in ch["matrix"] for x in r if x is not None) == 24
    assert any(c.isdigit() for c in ch["title"])
    assert cq.plan(rs, "m1")["kind"] == "matrix"


def test_chart_query_trend_and_composition():
    tr = [_cq_row(i, "m2", "朝阳", f"2025-{i:02d}", 100 + i) for i in range(1, 13)]
    ch = cq.build(tr, "m2")
    assert ch["type"] == "line" and len(ch["points"]) == 12
    comp = [_cq_row(i, "m3", x, "2025", v) for i, (x, v) in
            enumerate([("主粮", 40), ("零食", 25), ("用品", 20), ("医疗", 10), ("服务", 5)], 1)]
    ch = cq.build(comp, "m3")
    assert ch["type"] == "share_bar" and len(ch["items"]) == 5


def test_chart_query_rank_and_empty():
    rank = [_cq_row(i, "m4", f"区{i}", "2025", i * 3) for i in range(1, 17)]
    ch = cq.build(rank, "m4")
    assert ch["type"] == "hbar" and len(ch["items"]) == 10
    assert "仅列前 10" in ch.get("accent_note", "")
    assert any(c.isdigit() for c in ch["title"])
    assert cq.build([], "m1") is None
