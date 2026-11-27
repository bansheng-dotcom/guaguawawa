# -*- coding: utf-8 -*-
"""pipeline 六合一后的直接回归（2026-11-27）。

原先 card_plan / card_bundle / card_probe / card_issue / report_dispatch / dispatch
各自有测试；合并后这里对单模块的公开行为做一层直接覆盖，防止“合并把入口弄丢”。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core.cards import pipeline
from core.claims import cells_unified as cu


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="guagua_pipeline_"))


# --------------------------------------------------------------------------- #
# 分卡
# --------------------------------------------------------------------------- #
def test_pipeline_exposes_single_entry_symbols():
    for name in ("cluster", "assign", "apply_to_cells", "issue_bundle", "probe",
                 "prepare", "bootstrap", "prepare_probe_cards", "write_plan",
                 "issue", "load_issued", "verify_claims", "write_cards", "collect"):
        assert callable(getattr(pipeline, name))


def test_cluster_groups_by_qid():
    cells = [{"cell_id": "1", "qid": "Q1"}, {"cell_id": "2", "qid": "Q1"},
             {"cell_id": "3", "qid": "Q2"}]
    cl = pipeline.cluster(cells)
    assert {c["card_id"] for c in cl} == {"Q1", "Q2"}
    assert all(c["split"] is False for c in cl)


def test_cluster_splits_over_cap():
    cells = [{"cell_id": str(i), "qid": "Q1", "dim": "A"} for i in range(5)]
    cl = pipeline.cluster(cells, cap=2)
    assert len(cl) == 3
    assert all(c["split"] for c in cl)


def test_assign_marks_owner():
    cl, _ = pipeline.assign(pipeline.cluster([{"cell_id": "1", "qid": "Q1"}]),
                            {"r05": {}, "r06": {}})
    assert cl[0]["owner"] in ("r05", "r06")
    assert cl[0]["match"] in ("strong", "weak")


def test_assign_reports_gap_when_no_cards():
    cl, gaps = pipeline.assign(pipeline.cluster([{"cell_id": "1", "qid": "Q1"}]), {})
    assert cl[0]["owner"] == ""
    assert gaps


def test_apply_to_cells_marks_gap_without_owner():
    cells = [{"cell_id": "1"}]
    out = pipeline.apply_to_cells([{"cells": cells, "owner": ""}], cells)
    assert out[0]["match"] == "gap"


# --------------------------------------------------------------------------- #
# 卡信封
# --------------------------------------------------------------------------- #
def test_issue_bundle_returns_card_and_brief():
    r = pipeline.issue_bundle(_tmp(), "r06", "t1", "测试问题")
    assert set(r["bundle"]) >= {"card", "brief"}


def test_issue_bundle_card_has_brief_ref():
    r = pipeline.issue_bundle(_tmp(), "r06", "t1", "测试问题")
    assert r["bundle"]["card"]["brief_ref"]


# --------------------------------------------------------------------------- #
# 发卡 / 验卡 / 收卡
# --------------------------------------------------------------------------- #
def test_load_issued_missing_returns_none():
    assert pipeline.load_issued(str(_tmp())) is None


def test_issue_without_plan_fails():
    r = pipeline.issue(str(_tmp()))
    assert r["ok"] is False and "plan.json" in r["error"]


def test_write_plan_requires_confirmed_clarify():
    from core.report import report_clarify
    p = _tmp()
    assert report_clarify.write("内蒙个护有哪些品类，规模多少", str(p))["ok"]
    r = pipeline.write_plan(str(p))
    assert r["ok"] is False and "确认" in r["error"]


def test_collect_empty_dir_returns_merged():
    merged, problems = pipeline.collect(str(_tmp()))
    assert isinstance(merged, dict)
    assert isinstance(problems, list)


def test_probe_without_grid_returns_false():
    assert pipeline.probe(str(_tmp()))["ok"] is False


def test_degraded_cells_empty():
    assert pipeline.degraded_cells(str(_tmp())) == []


def test_prepare_probe_cards_without_grid():
    assert pipeline.prepare_probe_cards(_tmp())["ok"] is False


def test_prepare_without_confirmed_clarify_fails():
    r = pipeline.prepare(_tmp())
    assert r["ok"] is False


def test_validate_claims_cells_flags_missing_fields():
    miss = pipeline.validate_claims_cells({"cells": [{"cell_id": "c1", "value": 1}]})
    assert any("缺" in m for m in miss)


def test_render_plan_md_contains_roles():
    md = pipeline.render_plan_md({
        "intent": "测试",
        "mapping": [{"qid": "Q1", "question": "问", "type": "规模",
                     "must": True, "primary": "r06", "support": [], "why": "能力"}],
        "cards": [{"role": "r06", "name": "蛙德清", "questions": ["Q1"],
                   "must_not": []}],
    })
    assert "r06" in md and "Q1" in md


# --------------------------------------------------------------------------- #
# cells 统一读数
# --------------------------------------------------------------------------- #
def test_key_of_is_stable():
    assert cu.key_of("m", "e", "p") == cu.key_of("m", "e", "p")


def test_obs_skips_non_numeric():
    assert cu.obs("m", "e", "p", "abc") is None


def test_index_first_wins():
    a, b = cu.obs("m", "e", "p", 1), cu.obs("m", "e", "p", 2)
    assert cu.index([a, b])[a["key"]]["value"] == 1


def test_duplicates_same_value_harmless():
    a, b = cu.obs("m", "e", "p", 1), cu.obs("m", "e", "p", 1)
    assert cu.duplicates([a, b]) == []


def test_duplicates_conflict_reported():
    a, b = cu.obs("m", "e", "p", 1), cu.obs("m", "e", "p", 2)
    assert cu.duplicates([a, b])[0]["key"] == a["key"]


def test_observations_prefers_raw():
    p = _tmp()
    (p / "out").mkdir()
    (p / "out" / "raw.json").write_text(json.dumps({"rows": [
        {"metric_id": "m", "entity": "e", "period": "p", "value": 3,
         "unit": "u", "source_id": "s"}]}), encoding="utf-8")
    rows = cu.observations(p)
    assert rows and rows[0]["path"] == "raw"


def test_compare_writes_diff_file():
    p = _tmp()
    (p / "out").mkdir()
    (p / "out" / "raw.json").write_text(json.dumps({"rows": [
        {"metric_id": "m", "entity": "e", "period": "p", "value": 3}]}),
        encoding="utf-8")
    (p / "out_v3").mkdir()
    (p / "out_v3" / "cells_filled.json").write_text(json.dumps({"cells": [
        {"measure_id": "m", "entity": "e", "period": "p", "value": 4,
         "status": "filled"}]}), encoding="utf-8")
    res = cu.compare(p)
    assert (p / "out" / "cells_claims_diff.json").is_file()
    assert res["diffs"]


def test_apply_to_cells_overrides_value_and_flags_human():
    p = _tmp()
    (p / "out").mkdir()
    (p / "out" / "raw.json").write_text(json.dumps({"rows": [
        {"metric_id": "m", "entity": "e", "period": "p", "value": 5}]}),
        encoding="utf-8")
    cells = [{"measure_id": "m", "entity": "e", "period": "p", "value": 4}]
    res = cu.apply_to_cells(p, cells)
    assert cells[0]["value"] == 5
    assert cells[0]["value_from"] == "observation"
    assert cells[0].get("needs_human") is True
    assert res["mismatched"]


def test_apply_to_cells_keeps_cell_value_without_observation():
    p = _tmp()
    cells = [{"measure_id": "m", "entity": "e", "period": "p", "value": 4}]
    cu.apply_to_cells(p, cells)
    assert cells[0]["value_from"] == "cell"
