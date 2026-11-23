# -*- coding: utf-8 -*-
"""test_mece_and_saturation —— MECE 互斥 + 拆卡饱和。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import card_upgrade as cu  # noqa: E402


def _cell(qid, dim, entity, measure="share", cell_id=None):
    return {"qid": qid, "dim": dim, "entity": entity, "measure": measure,
            "status": "open", "cell_id": cell_id or f"{qid}.{dim}.{entity}"}


# ---------------- B: 互斥 ----------------

def test_mutual_flags_top_plus_individual():
    cells = [_cell("Q1", "对象", "TOP5 品牌"), _cell("Q1", "对象", "飞鹤"),
             _cell("Q1", "对象", "君乐宝")]
    ms = cu._mece_mutual(cells)
    assert any(x["kind"] == "top_plus_individual" for x in ms)


def test_mutual_flags_duplicate_entity():
    cells = [_cell("Q1", "对象", "飞鹤"), _cell("Q1", "对象", "飞鹤")]
    ms = cu._mece_mutual(cells)
    assert any(x["kind"] == "duplicate" for x in ms)


def test_mutual_does_not_flag_white_label_total_plus_brands():
    # 白牌合计 + 品牌名 是互补关系，不是重叠——不应误报
    cells = [_cell("Q4", "对象", "白牌合计"), _cell("Q4", "对象", "Babycare"),
             _cell("Q4", "对象", "可优比")]
    assert cu._mece_mutual(cells) == []


def test_mece_check_ok_includes_mutual():
    cells = [_cell("Q1", "对象", "TOP5 品牌"), _cell("Q1", "对象", "飞鹤")]
    r = cu.mece_check(cells)
    assert r["ok"] is False
    assert r["mutual"]


# ---------------- C: 饱和 ----------------

def _full_grid(qid="Q1"):
    cells = []
    for dim in cu.DIMS:
        for i in range(2):
            cells.append(_cell(qid, dim, f"e{i}", measure=f"m_{dim}"))
    return cells


def test_saturation_reached_on_full_grid():
    r = cu.grid_saturation(_full_grid())
    assert r["ok"] is True
    assert r["strong_ok"] is True
    assert r["items"][0]["dims"] == 6


def test_saturation_not_reached_on_thin_grid():
    r = cu.grid_saturation([_cell("Q1", "对象", "a")])
    assert r["ok"] is False
    assert "未饱和" in r["items"][0]["why"]


def test_saturation_basic_without_strong():
    # 六维齐、组合够、格子够，但每维只有 1 格 → 基础饱和、非强饱和
    cells = [_cell("Q1", d, "e", measure=f"m_{d}") for d in cu.DIMS]
    cells += [_cell("Q1", "对象", f"e{i}") for i in range(12)]
    r = cu.grid_saturation(cells)
    assert r["ok"] is True
    assert r["strong_ok"] is False
