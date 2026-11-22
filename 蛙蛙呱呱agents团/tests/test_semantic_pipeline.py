# -*- coding: utf-8 -*-
"""test_semantic_pipeline —— S5a 语义管道单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.semantic_pipeline import resolve, panel, apply_decisions  # noqa: E402


def _ir():
    return {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人"},
        "facts": [
            {"id": "F1", "metric": "电子配件", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "电子配件", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "s", "org": "o", "url": "u"}],
        "sections": [{
            "title": "电子配件两城差 8.1 万", "question": "两地价差多大",
            "outline": "两城对比",
            "chart": {"relation": "deviation", "chosen": "hbar",
                      "data_refs": ["F1", "F2"],
                      "dims": [{"name": "entity", "type": "categorical"}]},
        }],
    }


def test_resolve_valid():
    m = resolve(_ir())
    assert m["ok"] is True
    assert m["schema_errors"] == []


def test_resolve_keeps_chart_validation():
    m = resolve(_ir())
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert cv["ok"] is True


def test_resolve_fills_chosen_when_absent():
    ir = _ir()
    ir["sections"][0]["chart"].pop("chosen")
    m = resolve(ir)
    # deviation 关系下，无 period 维时 area 不可行，首位可读候选是 hbar
    assert m["sections"][0]["chart"]["chosen"] == "hbar"


def test_resolve_fills_relation_from_question():
    ir = _ir()
    ir["sections"][0]["chart"].pop("relation")
    m = resolve(ir)
    assert m["sections"][0]["chart"]["relation"] == "deviation"


def test_resolve_reports_schema_errors():
    ir = _ir()
    ir["facts"][0].pop("unit")
    m = resolve(ir)
    assert m["ok"] is False
    assert any("unit" in e for e in m["schema_errors"])


def test_resolve_author_override():
    ir = _ir()
    # 作者把关系改成 ranking + dumbbell（两值对比），覆盖推断的 deviation
    m = resolve(ir, {"0": {"relation": "ranking", "chosen": "dumbbell"}})
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert m["sections"][0]["chart"]["relation"] == "ranking"
    assert cv["ok"] is True


def _invalid_ir():
    ir = _ir()
    # hbar 不能表达 composition → 面板应列出这一节
    ir["sections"][0]["chart"]["relation"] = "composition"
    ir["sections"][0]["chart"]["chosen"] = "hbar"
    return ir


def test_panel_lists_invalid_only():
    m = resolve(_invalid_ir())
    p = panel(m)
    assert len(p) == 1
    assert p[0]["index"] == 0
    assert p[0]["reason"] is not None
    assert p[0]["candidates"]  # 给了候选


def test_apply_decisions_fixes_invalid():
    ir = _invalid_ir()
    m = apply_decisions(ir, [{"index": 0, "chosen": "treemap"}])
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert m["sections"][0]["chart"]["chosen"] == "treemap"
    assert cv["ok"] is True
