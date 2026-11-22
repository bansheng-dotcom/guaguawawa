# -*- coding: utf-8 -*-
"""test_chart_candidates —— S4 候选面板与校验单测。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import chart_candidates as cc  # noqa: E402


def test_candidates_ranking_needs_entity():
    cands = cc.candidates({"relation": "ranking", "dims": [{"name": "entity"}]})
    types = {c["type"] for c in cands}
    assert types, "ranking 应有候选"
    assert "scatter" not in types  # 二维类不该出现在只有 entity 的 ranking 候选里


def test_validate_line_change_over_time():
    r = cc.validate({"relation": "change_over_time", "chosen": "line",
                     "dims": [{"name": "period"}]})
    assert r["ok"] is True


def test_validate_hbar_not_change():
    r = cc.validate({"relation": "change_over_time", "chosen": "hbar", "dims": []})
    assert r["ok"] is False
    assert "hbar" not in r["allowed"]


def test_validate_scatter_needs_entity():
    r = cc.validate({"relation": "correlation", "chosen": "scatter", "dims": []})
    assert r["ok"] is False
