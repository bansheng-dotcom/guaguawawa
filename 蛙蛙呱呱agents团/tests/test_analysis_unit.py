# -*- coding: utf-8 -*-
"""core.analysis_unit 单测（DATA-LAYER-SOP v3.0 · S0）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import analysis_unit as au  # noqa: E402


def _sem(**over):
    base = {
        "entities": [
            {"id": "region", "type": "spatial", "levels": ["山东", "河北", "河南"]},
            {"id": "category", "type": "hierarchy", "levels": ["叶菜类", "茄果类"]},
            {"id": "period", "type": "time", "grain": "year"},
        ],
        "grain_declarations": [
            {"id": "G_region_category_month", "dims": ["region", "category", "month"]},
            {"id": "G_region_year", "dims": ["region", "year"]},
            {"id": "G_ghost", "dims": ["region", "brand"]},
        ],
        "measures": [
            {"id": "asp", "agg": "avg", "unit": "元/公斤", "grain": "G_region_category_month"},
            {"id": "size", "agg": "sum", "unit": "万吨", "grain": "G_region_year"},
            {"id": "bad", "agg": "sum", "unit": "元", "grain": "G_ghost"},
            {"id": "noenum", "agg": "sum", "unit": "元", "grain": "G_region_category_month"},
        ],
    }
    base.update(over)
    # 走 load 的统一结构
    return {
        "entities": au._index(base["entities"]),
        "grain_declarations": au._index(base["grain_declarations"]),
        "measures": au._index(base["measures"]),
    }


def test_unit_dims_and_time_grain():
    u = au.from_measure("asp", _sem())
    assert u["dims"] == ["region", "category"]
    assert u["time_grain"] == "month"          # 取自 grain 声明，不是全局 period.grain
    assert u["unit"] == "元/公斤"


def test_rows_expected_is_cardinality_times_periods():
    sem = _sem()
    u = au.from_measure("size", sem)           # region 3 × year 3
    assert au.rows_expected(u, sem) == 3 * 3
    u2 = au.from_measure("asp", sem)           # region 3 × category 2 × month 36
    assert au.rows_expected(u2, sem) == 3 * 2 * 36


def test_missing_entity_raises_not_defaults():
    """维度不在 sem 里 → 抛错；绝不能像 v2 那样套品牌模板。"""
    with pytest.raises(KeyError) as e:
        au.from_measure("bad", _sem())
    assert "MISSING_ENTITY" in str(e.value)


def test_no_enumeration_raises():
    sem = _sem()
    sem["entities"]["category"] = {"id": "category", "type": "hierarchy"}   # 无 levels
    u = au.from_measure("noenum", sem)
    with pytest.raises(KeyError) as e:
        au.rows_expected(u, sem)
    assert "NO_CARDINALITY" in str(e.value)


def test_missing_section_raises(tmp_path):
    p = tmp_path / "sem.yaml"
    p.write_text("schema: dsh.semantic/v3\nentities: []\n", encoding="utf-8")
    with pytest.raises(KeyError) as e:
        au.load(p)
    assert "SEM_MISSING" in str(e.value)


def test_plan_units_keeps_errors_visible():
    units = au.plan_units(_sem())
    errs = [u for u in units if "error" in u]
    assert any("MISSING_ENTITY" in u["error"] for u in errs)
    ok = [u for u in units if "error" not in u]
    assert ok and all("dataset_id" in u for u in ok)


def test_dataset_id_has_no_business_word():
    u = au.from_measure("asp", _sem())
    did = au.dataset_id(u)
    assert did == "DS-asp-region-category-month"
    for bad in ("品牌", "gmv", "价格带", "长尾"):
        assert bad not in did
