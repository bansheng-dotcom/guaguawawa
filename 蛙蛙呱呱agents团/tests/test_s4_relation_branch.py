# -*- coding: utf-8 -*-
"""test_s4_relation_branch —— 验证 S4 在 report_flow 里的关系选型分支端到端生效。

覆盖：
  - 卡片声明 relation → 走关系选型，产出 chart_validation；
  - 合法选择（dumbbell+ranking）ok=True；
  - 非法选择（line+ranking）ok=False，并给出 suggest。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.report_flow import build_sections_contract  # noqa: E402


def _draft(chart_type, relation):
    return {
        "standfirst": "三地价差 1.5 倍",
        "sections": [{
            "title": "三地价差 1.5 倍",
            "question": "两地价差有多大",
            "relation": relation,
            "reading": [{"strong": "事实　", "text": "包头 2 元，呼市 3 元。",
                         "refs": ["N1", "N2"]}],
            "refs": ["N1", "N2"],
            "falsifier": "价差收敛到 1.2 倍以下即作废",
            "boundary": "同口径批发价",
            "chart": {
                "type": chart_type,
                "relation": relation,
                "intent": "排序",
                "why_this_chart": "哑铃图直接编码同一品类两地价差",
                "refs": ["N1", "N2"],
                "bars": [{"label": "包头", "value": 2.0},
                         {"label": "呼和浩特", "value": 3.0}],
            },
        }],
    }


def _pack():
    return {"numbers": [
        {"id": "N1", "name": "包头批发价", "value": 2.0, "unit": "元/公斤",
         "entity": "包头", "period": ""},
        {"id": "N2", "name": "呼市批发价", "value": 3.0, "unit": "元/公斤",
         "entity": "呼和浩特", "period": ""},
    ]}


def test_relation_branch_valid_dumbbell():
    secs = build_sections_contract(_draft("dumbbell", "ranking"), _pack())
    ch = secs["sections"][0]["chart"]
    assert ch.get("relation") == "ranking"
    assert ch.get("chart_validation", {}).get("ok") is True


def test_relation_branch_invalid_line():
    # line 不能表达 ranking → 应 ok=False 并给 suggest
    secs = build_sections_contract(_draft("line", "ranking"), _pack())
    ch = secs["sections"][0]["chart"]
    val = ch.get("chart_validation", {})
    assert val.get("ok") is False
    assert val.get("suggest")
