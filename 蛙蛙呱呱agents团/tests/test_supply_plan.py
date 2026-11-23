# -*- coding: utf-8 -*-
"""test_supply_plan —— 数据供给方案（SUPPLY-SOP v7.0）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import collection_contract  # noqa: E402
from core import supply_plan as sup  # noqa: E402


def _doc(**kw):
    base = {
        "schema": sup.SCHEMA,
        "business": "测试业务",
        "sources": [
            {"layer": "A", "name": "统计局", "gives": ["规模"], "cost": 0},
            {"layer": "B", "name": "行业报告", "gives": ["结构"], "cost": 0},
        ],
        "levels": {"L1_possible": True, "L2_possible": False,
                   "L2_condition": "需采购第三方数据"},
        "reviewed_at": "2026-11-23",
    }
    base.update(kw)
    return base


# ---------------- validate ----------------

def test_valid_l1_plan():
    assert sup.validate(_doc()) == []


def test_missing_doc():
    assert sup.validate({})


def test_missing_business():
    assert any("business" in e for e in sup.validate(_doc(business="")))


def test_no_sources():
    assert any("sources" in e for e in sup.validate(_doc(sources=[])))


def test_bad_layer():
    d = _doc()
    d["sources"][0]["layer"] = "Z"
    assert any("layer" in e for e in sup.validate(d))


def test_l2_needs_condition():
    d = _doc(levels={"L1_possible": True, "L2_possible": False})
    assert any("L2_condition" in e for e in sup.validate(d))


def test_l2_requires_c_layer():
    """声称能做 L2 却没有 C 层源——自相矛盾。"""
    d = _doc(levels={"L1_possible": True, "L2_possible": True})
    assert any("C 层" in e for e in sup.validate(d))


def test_l2_with_c_layer_ok():
    d = _doc(sources=[
        {"layer": "A", "name": "a", "gives": ["x"]},
        {"layer": "C", "name": "c", "gives": ["y"]},
    ], levels={"L1_possible": True, "L2_possible": True})
    assert sup.validate(d) == []


def test_planned_rows_must_be_positive():
    d = _doc(levels={"L1_possible": True, "L2_possible": False,
                     "L2_condition": "x", "planned_rows": 0})
    assert any("planned_rows" in e for e in sup.validate(d))


# ---------------- planned ----------------

def test_planned_level_l2():
    d = _doc(sources=[{"layer": "C", "name": "c", "gives": ["y"]}],
             levels={"L1_possible": True, "L2_possible": True})
    assert sup.planned_level(d) == "L2"


def test_planned_level_l1():
    assert sup.planned_level(_doc()) == "L1"


def test_planned_level_l0():
    assert sup.planned_level({}) == "L0"


def test_planned_rows():
    d = _doc(levels={"L1_possible": True, "L2_possible": False,
                     "L2_condition": "x", "planned_rows": 144})
    assert sup.planned_rows(d) == 144


def test_planned_rows_absent():
    assert sup.planned_rows(_doc()) is None


# ---------------- actual / capability ----------------

def test_actual_level_l2_from_mart():
    assert sup.actual_level({"mart_rows": {"a": 72}}) == "L2"


def test_actual_level_l1_from_numbers():
    assert sup.actual_level({"numbers": [1, 2]}) == "L1"


def test_actual_level_l0():
    assert sup.actual_level({}) == "L0"


def test_capability_no_degrade_when_plan_is_l1():
    """计划就是 L1，交付 L1 → 正常交付，不叫降级。"""
    cap = sup.capability_of(_doc(), {"numbers": [1, 2]})
    assert cap["planned"] == "L1"
    assert cap["actual"] == "L1"
    assert cap["degraded"] is False
    assert "按计划交付" in cap["why"]


def test_capability_degrade_when_plan_l2_actual_l1():
    d = _doc(sources=[{"layer": "C", "name": "c", "gives": ["y"]}],
             levels={"L1_possible": True, "L2_possible": True,
                     "L2_condition": "需采购"})
    cap = sup.capability_of(d, {"numbers": [1]})
    assert cap["planned"] == "L2"
    assert cap["actual"] == "L1"
    assert cap["degraded"] is True
    assert cap["degraded_from"] == "L2"


def test_capability_gate_ok_when_on_plan():
    g = sup.gate(_doc(), {"numbers": [1]})
    assert g["ok"] is True
    assert g["id"] == "G-CAPABILITY"


def test_capability_gate_flags_missing_supply():
    g = sup.gate({}, {"numbers": [1]})
    assert g["ok"] is False


# ---------------- 契约接线：rows_expected 不再等于格子数 ----------------

def _grid(n=4):
    return {"cells": [
        {"cell_id": "c%d" % i, "measure": "asp", "grain": "G_brand_month",
         "entity": "e%d" % i} for i in range(n)
    ]}


def test_contract_rows_expected_uses_supply():
    """84 个格子 ≠ 84 行；行数由供给方案定。"""
    c = collection_contract.build(
        _grid(4), {"measures": [], "entities": []},
        supply=_doc(levels={"L1_possible": True, "L2_possible": False,
                            "L2_condition": "x", "planned_rows": 144}))
    assert c["rows_expected"] == 144
    assert c["rows_expected_source"] == "supply.yaml"


def test_contract_rows_expected_falls_back_to_cells():
    c = collection_contract.build(_grid(4), {"measures": [], "entities": []})
    assert c["rows_expected"] == 4
    assert c["rows_expected_source"] == "cell_count(fallback)"


def test_contract_carries_planned_level():
    c = collection_contract.build(_grid(3), {"measures": [], "entities": []},
                                  supply=_doc())
    assert c["acquisition"]["planned_level"] == "L1"
    assert "A" in c["acquisition"]["supply_layers"]


# ---------------- v7.1：供给方案是探测的产物 ----------------

def _probe_res():
    return {
        "cells": 84,
        "sources": ["manual_csv"],
        "business": "proj-x",
        "generated_at": "2026-11-23T17:00:00",
        "planned_rows": 144,
        "to_l2_condition": "需补 channel 字段",
        "supply_demands": [
            {"measure": "asp", "grain": ["brand", "month"], "cells": ["c1", "c2"],
             "cell_count": 2, "matched_source": "manual_csv",
             "matched_via": {"brand": "split:brands:,:0"},
             "level": "L1", "missing": [], "why": ""},
            {"measure": "channel_share", "grain": ["brand", "channel"],
             "cells": ["c3"], "cell_count": 1, "matched_source": "manual_csv",
             "matched_via": {}, "level": "L0",
             "missing": ["channel"], "why": "源里没有 channel"},
        ],
    }


def test_from_probe_generates_supply():
    doc = sup.from_probe(_probe_res())
    assert doc["generated"] is True
    assert doc["summary"]["demands"] == 2
    assert doc["summary"]["L1"] == 1
    assert doc["summary"]["L0"] == 1
    assert doc["summary"]["planned_level"] == "L1"
    assert doc["summary"]["planned_rows"] == 144
    assert doc["levels"]["L1_possible"] is True
    assert doc["levels"]["L2_possible"] is False


def test_from_probe_records_per_demand_source():
    doc = sup.from_probe(_probe_res())
    by = {d["measure"]: d for d in doc["demands"]}
    assert by["asp"]["matched_source"] == "manual_csv"
    assert by["asp"]["cell_count"] == 2
    assert by["channel_share"]["missing"] == ["channel"]


def test_from_probe_l2_when_any_full():
    pr = _probe_res()
    pr["supply_demands"][0]["level"] = "L2"
    doc = sup.from_probe(pr)
    assert doc["summary"]["L2"] == 1
    assert doc["levels"]["L2_possible"] is True


def test_load_or_generate_prefers_generated(tmp_path):
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "supply.json").write_text(
        json.dumps(sup.from_probe(_probe_res()), ensure_ascii=False),
        encoding="utf-8")
    (tmp_path / "supply.yaml").write_text(
        "schema: dsh.supply/v1\nbusiness: 手写\nsources: []\n", encoding="utf-8")
    d = sup.load_or_generate(tmp_path)
    assert d.get("generated") is True
    assert d["summary"]["demands"] == 2


def test_load_or_generate_falls_back_to_yaml(tmp_path):
    (tmp_path / "supply.yaml").write_text(
        "schema: dsh.supply/v1\nbusiness: 手写\nsources: []\n", encoding="utf-8")
    d = sup.load_or_generate(tmp_path)
    assert d.get("business") == "手写"


def test_load_or_generate_empty(tmp_path):
    assert sup.load_or_generate(tmp_path) == {}


def test_no_supply_does_not_pretend_a_plan():
    """没有供给方案时不许假装有计划：按实际级别回报，并注明。"""
    cap = sup.capability_of({}, {"numbers": [1, 2]})
    assert cap["planned"] == "L1"
    assert cap["actual"] == "L1"
    assert cap["degraded"] is False
    assert cap["no_supply"] is True
    assert "未声明供给方案" in cap["why"]


def test_probe_card_is_not_a_collection_card(tmp_path):
    """探源卡要写给探测层，且明确说「不是采集卡」。"""
    from core import card_issue
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "grid.json").write_text(json.dumps({
        "cells": [{"cell_id": "c1", "measure": "asp",
                   "grain": "G_brand_month", "dim": "对象", "entity": "A"}],
    }, ensure_ascii=False), encoding="utf-8")
    r = card_issue.prepare_probe_cards(tmp_path)
    assert r["ok"] is True
    task = (tmp_path / "cards" / "r18" / "TASK.md").read_text(encoding="utf-8")
    assert "探源卡" in task
    assert "不是采集卡" in task
    assert (tmp_path / "cards" / "r18" / "NEEDS.json").is_file()


def test_probe_card_requires_grid(tmp_path):
    from core import card_issue
    r = card_issue.prepare_probe_cards(tmp_path)
    assert r["ok"] is False


# ---------------- v7.2：探源交给 r18，产出数据目录 ----------------

def _entry(**kw):
    e = {"table": "tjb_car_parc", "layer": "A", "owner": "r18",
         "url": "https://www.stats.gov.cn/x",
         "fields": ["年份", "民用汽车保有量"],
         "access": "直接抓", "cost": 0, "freshness": "年更",
         "caliber": "全国/年末"}
    e.update(kw)
    return e


def test_from_catalog_basic():
    from core import source_profile as sp
    s = sp.from_catalog(_entry())
    assert s["id"] == "tjb_car_parc"
    assert s["owner"] == "r18"
    assert s["layer"] == "A"
    assert s["kind"] == "web_search"
    assert s["from_catalog"] is True
    assert sp.validate(s) == []


def test_from_catalog_monthly_is_historical():
    from core import source_profile as sp
    s = sp.from_catalog(_entry(freshness="月更"))
    assert s["history"] == "historical"


def test_from_catalog_yearly_is_snapshot_only():
    from core import source_profile as sp
    s = sp.from_catalog(_entry(freshness="年更"))
    assert s["history"] == "snapshot_only"


def test_from_catalog_requires_table():
    from core import source_profile as sp
    assert sp.from_catalog(_entry(table="")) == {}


def test_from_catalog_grain_falls_back_to_first_field():
    from core import source_profile as sp
    s = sp.from_catalog(_entry(atomic_grain=["nope"]))
    assert s["atomic_grain"] == ["年份"]


def test_load_catalog_reads_r18_file(tmp_path):
    from core import source_profile as sp
    d = tmp_path / "cards" / "r18"
    d.mkdir(parents=True)
    (d / "data_catalog.json").write_text(json.dumps({
        "catalog": [_entry(), _entry(table="tmall_sku", layer="C")],
    }, ensure_ascii=False), encoding="utf-8")
    got = sp.load_catalog(tmp_path)
    assert [s["id"] for s in got] == ["tjb_car_parc", "tmall_sku"]


def test_load_catalog_missing_returns_empty(tmp_path):
    from core import source_profile as sp
    assert sp.load_catalog(tmp_path) == []


def test_probe_uses_r18_catalog_as_sources(tmp_path):
    """探源产物优先于 configs/sources 兜底。"""
    from core import card_probe
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "grid.json").write_text(json.dumps({
        "cells": [{"cell_id": "c1", "measure": "asp",
                   "grain": "G_brand_month", "dim": "对象", "entity": "A"}],
    }, ensure_ascii=False), encoding="utf-8")
    d = tmp_path / "cards" / "r18"
    d.mkdir(parents=True)
    (d / "data_catalog.json").write_text(json.dumps({
        "catalog": [_entry(table="cat_src")],
    }, ensure_ascii=False), encoding="utf-8")
    srcs = card_probe._load_sources(tmp_path)
    assert [s["id"] for s in srcs] == ["cat_src"]


def test_probe_card_goes_to_r18(tmp_path):
    from core import card_issue
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "grid.json").write_text(json.dumps({
        "cells": [{"cell_id": "c1", "measure": "asp",
                   "grain": "G_brand_month", "dim": "对象", "entity": "A"}],
    }, ensure_ascii=False), encoding="utf-8")
    r = card_issue.prepare_probe_cards(tmp_path)
    assert r["role"] == "r18"
    task = (tmp_path / "cards" / "r18" / "TASK.md").read_text(encoding="utf-8")
    assert "r18" in task
    assert "owner" in task
    assert "data_catalog.json" in task
