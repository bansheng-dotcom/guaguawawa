# -*- coding: utf-8 -*-
"""收卡期图表契约（core.dispatch._chart_contract）回归。

守四条：
1. 图上的点必须有登记数字或显式 derived；
2. chart.refs 必须指向本卡数字；
3. 构成图合计偏离 100% 超过容差 → 报；
4. 显式 partial: true 的构成图放行（半成品要留痕，不是静默放过）。
"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core.cards import pipeline as dispatch  # noqa: E402


def _claims(chart, numbers=None):
    return {
        "schema": "dsh.claims/v2",
        "numbers": numbers if numbers is not None else [
            {"id": "N1", "value": 48.2, "source_file": "S1"},
            {"id": "N2", "value": 27, "source_file": "S1"},
        ],
        "sources": [{"file": "S1", "url": "https://a.gov.cn/x",
                     "date": "2025-01", "quote": "这是一段足够长的原文引用内容"}],
        "sections": [{
            "title": "测试节",
            "refs": ["N1", "N2"],
            "reading": [{"text": "事实：A", "refs": ["N1"]},
                        {"text": "机理：B", "refs": ["N2"]}],
            "falsifier": "若跌破 40% 则作废",
            "chart": chart,
        }],
    }


BASE = {"type": "hbar", "title": "占比 48.2%", "source": "S1",
        "refs": ["N1", "N2"], "relation": "ranking",
        "items": [{"label": "企业", "value": 48.2}, {"label": "合作社", "value": 27}]}


def test_valid_chart_passes():
    assert dispatch._need(_claims(BASE)) == []


def test_unregistered_point_blocked():
    ch = dict(BASE, items=BASE["items"] + [{"label": "其他", "value": 7.3}])
    miss = dispatch._need(_claims(ch))
    assert any("图数据点无出处" in m for m in miss)


def test_derived_point_allowed():
    claims = _claims(dict(BASE, items=BASE["items"] + [
        {"label": "其他", "value": 7.3, "derived": True}]))
    assert dispatch._need(claims) == []


def test_chart_refs_must_be_local():
    ch = dict(BASE, refs=["N1", "N9"])
    miss = dispatch._need(_claims(ch))
    assert any("chart.refs 找不到本卡数字" in m for m in miss)


def test_composition_sum_checked():
    ch = {"type": "donut", "title": "构成 90%", "source": "S1",
          "refs": ["N1", "N2"], "relation": "composition",
          "items": [{"label": "企业", "value": 48.2}, {"label": "合作社", "value": 27}]}
    miss = dispatch._need(_claims(ch))
    assert any("不等于 100%" in m for m in miss)
    ok = dispatch._need(_claims(dict(ch, partial=True)))
    assert ok == []
