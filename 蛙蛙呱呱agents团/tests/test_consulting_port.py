# -*- coding: utf-8 -*-
"""consulting 主题移植的回归测试：13 型图表 + A/B 页式 + renderer 出口。"""
from __future__ import annotations

from core.charts import consulting as cc
from core.report_renderer import render
from core.report_theme.pages import render_contract


def _contract() -> dict:
    return {
        "doc_type": "研究报告",
        "title_lines": ["测试标题：一个判断", "副标题"],
        "standfirst": "导语：先给结论，再给数字。",
        "metric_strip": [
            {"label": "指标 A", "value": "10.6", "note": "元/公斤"},
            {"label": "指标 B", "value": "5.35", "note": "元/公斤"},
            {"label": "指标 C", "value": "1.98×", "note": "倍"},
            {"label": "指标 D", "value": "8.0%", "note": "差"},
        ],
        "summary": [
            {"text": "第一句判断，带数字 10.6。"},
            {"text": "第二句判断，带数字 5.35。"},
        ],
        "sections": [
            {
                "index": 1, "kicker": "价差",
                "title": "批发价差 1.98 倍，零售只剩 8.0%",
                "question": "跨城能不能赚价差？",
                "verdict": "跨城套利不成立。",
                "reading": [
                    {"text": "呼市 10.60，赤峰 5.35，前者是后者的 1.98 倍。", "strong": ""},
                    {"text": "零售只差 8.0%，价差没有传下去。", "strong": ""},
                    {"text": "呼市精品、赤峰统货，不能直接相减。", "strong": "本节边界　"},
                ],
                "chart": {
                    "type": "hbar", "title": "同品篮子", "unit_meta": "元/公斤",
                    "source": "测试来源",
                    "bars": [{"label": "呼市", "value": 10.6}, {"label": "赤峰", "value": 5.35}],
                },
                "rail": {"items": [["10.60", "呼市", "元/公斤"], ["5.35", "赤峰", "元/公斤"],
                                   ["1.98×", "倍数", "倍"], ["8.0%", "零售差", ""]],
                         "line": "先对齐口径，再谈调拨。"},
                "notes": ["证据：2 条可寻址数字。"],
            },
            {
                "index": 2, "kicker": "标准",
                "title": "水分 48%、蛋白 30%",
                "question": "卡哪些指标？",
                "reading": [
                    {"text": "水分不超过 48%，蛋白不低于 30%。", "strong": ""},
                    {"text": "任一项越线整批不出厂。", "strong": ""},
                ],
                "table": {"caption": "理化限值", "columns": [{"text": "指标"}, {"text": "值"}],
                          "rows": [[{"text": "水分"}, {"text": "48%"}]]},
                "notes": ["证据：1 条。"],
            },
        ],
        "sources": [{"id": "S1", "title": "测试来源", "date": "2026-11-19"}],
        "notes": {"summary": "口径", "items": []},
        "footer": "",
        "short_title": "测试报告",
    }


def test_13_chart_functions_render_svg():
    cases = {
        "hbar": {"bars": [{"label": "A", "value": 3}, {"label": "B", "value": 5}]},
        "grouped_bar": {"groups": [["G1", [3, 5]], ["G2", [4, 6]]], "series": ["A", "B"]},
        "dumbbell": {"rows": [{"label": "X", "a": 3, "b": 5}]},
        "slope": {"rows": [{"label": "X", "a": 3, "b": 5}]},
        "range": {"rows": [{"label": "X", "low": 3, "high": 5}]},
        "share": {"segments": [{"label": "A", "value": 60}, {"label": "B", "value": 40}]},
        "waterfall": {"steps": [{"label": "起", "value": 10, "kind": "base"},
                                {"label": "增", "value": 2, "kind": "delta"},
                                {"label": "终", "value": 12, "kind": "total"}]},
        "bubble": {"points": [{"x": 1, "y": 2, "size": 3, "label": "A"}]},
        "coverage": {"rows": [{"label": "A", "values": [1, 0]}], "columns": ["有", "缺"]},
        "yoy": {"items": [{"label": "A", "value": -2}, {"label": "B", "value": 3}]},
        "fan": {"series": [{"name": "基准", "values": [6.6, 6.8]}], "xlabels": ["11/16", "01/16"]},
        "path_matrix": {"points": [{"x": 1, "y": 2, "label": "A"}]},
        "gantt": {"tasks": [{"label": "A1", "start": 1, "end": 2}], "weeks": 4},
        "pareto": {"items": [{"label": "A", "value": 18}, {"label": "B", "value": 16.4},
                             {"label": "C", "value": 1.58}]},
    }
    assert len(cc.RENDERERS) >= 13
    for name, payload in cases.items():
        payload["type"] = name
        svg = cc.render(payload)
        assert svg.startswith("<svg"), name
        assert "</svg>" in svg, name
        assert "viewBox" in svg, name


def test_contract_renders_a_and_b_pages():
    html = render_contract(_contract())
    assert html.count('class="page') == 7  # cover/summary/toc/2 sections/appendix/back
    assert 'class="page sec rail-layout"' in html
    assert 'class="page sec"' in html
    assert "rail-float" in html and "pblocks" in html
    assert "10.60" in html and "水分不超过 48%" in html


def test_renderer_consulting_dispatch():
    c = _contract()
    c["theme"] = "consulting"
    html = render(c)
    assert 'class="page cover"' in html
    assert "rail-float" in html


def test_renderer_flow_still_works():
    c = _contract()
    c["layout"] = "flow"
    html = render(c)
    assert "flow-paper" in html


def test_editorial_enrich_and_gate():
    from core.report_editorial import enrich, check_contract
    c = {
        "doc_type": "调研报告", "title_lines": ["自动汇编报告", "7 节 · 智能体调研稿"],
        "standfirst": "准入：300 平方米以下只能做奶豆腐。",
        "summary": [{"text": "第一句判断。"}],
        "sections": [{
            "index": 1, "title": "准入：300 平方米以下只能做奶豆腐，奶贝必须持证",
            "reading": [
                {"text": "小作坊面积上限 300 平方米，超过就要生产许可。", "strong": "观察　"},
                {"text": "允许品种有明确清单，奶贝在禁止目录里，作坊不论面积多小都不能做。", "strong": "观察　"},
                {"text": "罚则先算清：货值不足一万元时罚 5000 至 20000 元，一次抽检不合格就可能吃掉全部利润。", "strong": "对照　"},
                {"text": "所以：先按 300 平方米以内登记，把奶豆腐与奶皮子跑通。", "strong": "落点　"},
            ],
            "falsifier": "若目录把奶豆腐列入禁产，本节作废。",
            "chart": {"type": "hbar", "title": "同品", "source": "S1", "unit_meta": "平方米",
                      "bars": [{"label": "面积", "value": 300}, {"label": "罚款", "value": 5000},
                               {"label": "备案", "value": 30}]},
        }],
    }
    out = enrich(c)
    s = out["sections"][0]
    assert s["kicker"] == "准入"
    assert "300" in s["verdict"]
    assert len(s["rail"]["items"]) >= 3
    assert out["actions"][0]["id"] == "A1"
    assert out["title_lines"][1] != "7 节 · 智能体调研稿"
    assert check_contract(out)["ok"]
    bad = {"sections": [{"index": 1, "title": "没有数字的标题", "reading": [{"text": "短"}]}]}
    assert not check_contract(bad)["ok"]


def test_quality_gate_contract_layer():
    from core.report_editorial import enrich
    from core.quality_gate import check
    c = {"doc_type": "报告", "title_lines": ["自动汇编报告", ""],
         "standfirst": "准入：300 平方米以下只能做奶豆腐。", "summary": [{"text": "判断。"}],
         "sections": [{"index": 1, "title": "准入：300 平方米以下只能做奶豆腐",
                       "reading": [{"text": "小作坊面积上限 300 平方米，超过就要生产许可。" * 6,
                                    "strong": "观察　"}],
                       "chart": {"type": "hbar", "title": "同品", "source": "S1",
                                 "unit_meta": "平方米",
                                 "bars": [{"label": "面积", "value": 300},
                                          {"label": "罚款", "value": 5000},
                                          {"label": "备案", "value": 30}]}}]}
    out = enrich(c)
    r = check(contract=out)
    assert r["ok"] and r["layers"][0]["layer"] == "contract"


def test_require_shape_blocks_bad_chart():
    import pytest
    from core.report_theme.pages import render_contract
    c = _contract()
    c["require_shape"] = True
    c["sections"][0]["shape"] = "scalar"  # hbar is allowed for scalar
    assert render_contract(c)
    c["sections"][0]["shape"] = "pair"  # hbar not allowed for pair
    with pytest.raises(ValueError):
        render_contract(c)
