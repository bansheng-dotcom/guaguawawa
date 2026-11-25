# -*- coding: utf-8 -*-
"""P5-5：三套读数统一 + 双写对账。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))
if str(TEAM / "tests") not in sys.path:
    sys.path.insert(0, str(TEAM / "tests"))

from core import cells_claims, cells_unified  # noqa: E402
from test_cells_claims import _project  # noqa: E402


def _filled(base: Path):
    doc = json.loads((base / "out_v3" / "cells_filled.json")
                     .read_text(encoding="utf-8"))
    return doc, [c for c in doc["cells"] if c["status"] == "filled"]


def test_compare_finds_diff_and_missing(tmp_path):
    base = _project()
    whole, filled = _filled(base)
    a, b, c = filled[0], filled[1], filled[2]
    (base / "out" / "raw.json").write_text(json.dumps({"rows": [
        {"metric_id": a["measure_id"], "metric_name": "revenue",
         "entity": a["entity"], "period": a["period"], "value": a["value"],
         "unit": "亿元", "source_id": "S1"},
        {"metric_id": b["measure_id"], "metric_name": "revenue",
         "entity": b["entity"], "period": b["period"], "value": 999,
         "unit": "亿元", "source_id": "S1"},
    ]}, ensure_ascii=False), encoding="utf-8")
    d = cells_unified.compare(base)
    assert d["matched"] == 2 and len(d["diffs"]) == 1
    assert d["diffs"][0]["unified_value"] == 999.0
    assert any(k.endswith("|" + c["entity"] + "|" + c["period"])
               for k in d["missing_in_unified"])
    assert (base / "out" / "cells_claims_diff.json").is_file()


def test_build_uses_unified_observation_and_flags_mismatch():
    base = _project()
    _, filled = _filled(base)
    a, b = filled[0], filled[1]
    (base / "out" / "raw.json").write_text(json.dumps({"rows": [
        {"metric_id": a["measure_id"], "metric_name": "revenue",
         "entity": a["entity"], "period": a["period"], "value": 777,
         "unit": "亿元", "source_id": "S1"},
        {"metric_id": b["measure_id"], "metric_name": "revenue",
         "entity": b["entity"], "period": b["period"], "value": b["value"],
         "unit": "亿元", "source_id": "S1"},
    ]}, ensure_ascii=False), encoding="utf-8")
    res = cells_claims.build(base)
    assert res["ok"], res
    assert res["unified"]["value_from_observation"] >= 2
    assert res["unified"]["diff_count"] == 1
    assert res["unified"]["needs_human"] >= 1
    claims = json.loads((base / "cards" / "r05" / "claims.json")
                        .read_text(encoding="utf-8"))
    nums = {(n["name"], n["value"]) for n in claims["numbers"]}
    assert any(v == 777.0 for _, v in nums)
    assert any(n.get("needs_human") for n in claims["numbers"])


def test_build_without_raw_keeps_cell_values():
    base = _project()
    res = cells_claims.build(base)
    assert res["ok"] and res["unified"]["value_from_observation"] == 0
    assert res["unified"]["diff_ok"] is True


def test_mart_rows_are_read_as_observations(tmp_path):
    base = tmp_path / "m"
    (base / "plan").mkdir(parents=True)
    (base / "collection.yaml").write_text(
        "schema: dsh.collection_spec/v1\nid: x\nsource: s\n"
        "query: {path: data.csv}\n"
        "rollups:\n- id: by_brand\n  grain: [brand, month]\n"
        "  derive: {brand: field:brand, month: field:month}\n"
        "  measures: {asp: {agg: sum, expr: price}}\n", encoding="utf-8")
    (base / "plan" / "mart.json").write_text(json.dumps({
        "by_brand": [{"brand": "甲", "month": "2025-01", "asp": 12.5},
                     {"brand": "乙", "month": "2025-01", "asp": 9.0}]},
        ensure_ascii=False), encoding="utf-8")
    rows = cells_unified.observations(base)
    assert {r["entity"] for r in rows} == {"甲", "乙"}
    assert all(r["period"] == "2025-01" for r in rows)
