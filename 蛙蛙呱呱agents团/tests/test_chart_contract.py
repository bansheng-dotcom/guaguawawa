# -*- coding: utf-8 -*-
"""test_chart_contract —— S3 统一契约 v2 的归一化（三条线）单测。"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import chart_contract as cc  # noqa: E402


def _load_chart_contract_sections():
    p = Path(r"D:\蛙蛙呱呱\呼包鄂蔬菜价格分析_2026-11-22\report\contract.json")
    return json.loads(p.read_text(encoding="utf-8"))["sections"]


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
