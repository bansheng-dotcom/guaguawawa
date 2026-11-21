# -*- coding: utf-8 -*-
"""card_upgrade 自测：24 门禁 + 协作八组件（无 pytest，直接运行）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import card_upgrade as cu  # noqa: E402

OK, FAIL = [], []


def check(name, cond, msg=""):
    (OK if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {msg}" if msg and not cond else ""))


def sem():
    case = {
        "entities": [{"id": "region", "type": "spatial"},
                     {"id": "brand", "type": "party"},
                     {"id": "period", "type": "time"}],
        "grain_declarations": [{"id": "G1", "dims": ["region", "year"]}],
        "measures": [
            {"id": "retail_sales", "type": "simple", "expr": "x", "unit": "亿元", "grain": "G1"},
            {"id": "share", "type": "ratio", "numerator": "a", "denominator": "b",
             "unit": "%", "grain": "G1"},
        ],
    }
    generic = {"metric_types": {"simple": {"required": ["agg", "expr"]},
                                "ratio": {"required": ["numerator", "denominator"]}}}
    return {"generic": generic, "case": case, "generated": False}


def main() -> int:
    clarify = {"asks": [
        {"id": "Q1", "text": "内蒙哪些品牌卖得好", "must": True},
        {"id": "Q2", "text": "全国怎么样", "must": False},
    ]}
    s = sem()

    tree = cu.build_issue_tree(clarify)
    check("issue_tree_only_must", len(tree["nodes"]) == 1)
    per = cu.build_perspectives(clarify)
    check("perspectives_ge3", per["count"] >= 3)

    grid = cu.build_grid(clarify, s, ["甲", "乙"])
    check("grid_six_dims", len({c["dim"] for c in grid["cells"]}) == 6)
    check("grid_has_quality", all(len(c["quality"]) == 6 for c in grid["cells"]))
    check("grid_has_causal", all(c["causal_level"] in cu.CAUSAL_LEVELS for c in grid["cells"]))

    # 2026-11-21 回归：通用兜底不得内置任何业务线（潮玩）实体与度量
    tpl = cu._q_template("中国市场规模与份额", ["甲品牌"])
    check("template_no_foreign_entity",
          not any(k in x for x in tpl["对象"] for k in ("泡泡玛特", "IP玩具", "潮玩")), tpl)
    mids = {m["id"] for m in s["case"]["measures"]}
    check("grid_measures_registered",
          all(c["measure"] in mids for c in grid["cells"]),
          [c["measure"] for c in grid["cells"] if c["measure"] not in mids])
    bad_grid = {"cells": [{"cell_id": "Q1.对象.x", "measure": "ad_cost", "grain": "G1"}]}
    check("validate_grid_catches_unregistered", bool(cu.validate_grid(bad_grid, s)))

    # 语义层校验
    bad = cu.validate_semantic({"generic": s["generic"], "case": {"measures": [
        {"id": "m", "type": "ratio", "unit": "%"}]}})
    check("semantic_catches_missing_denominator", bool(bad), bad)
    override = cu.validate_semantic({"generic": s["generic"], "case": {
        "forbidden": [{"id": "x"}], "measures": []}})
    check("semantic_rejects_override", any("forbidden" in e for e in override), override)

    # 候选拆解：分数是算出来的，且两组
    nums = [{"name": "甲品牌份额", "value": 20, "unit": "%", "period": "2025"},
            {"name": "乙品牌份额", "value": 15, "unit": "%", "period": "2025"}]
    dec = cu.score_decompositions(clarify["asks"][0], grid["cells"], nums)
    check("decomposition_two_variants", len(dec["variants"]) >= 2)
    check("decomposition_scores_numeric",
          all(isinstance(v["scores"]["可获取"], int) for v in dec["variants"]))

    cards = {
        "r05": {"role": "r05", "capabilities": ["研究", "行业"], "skills": [],
                "entitlements": {"public": True, "platform": False, "primary": False},
                "sla": {"ack_min": 30, "deliver_min": 120}},
        "r06": {"role": "r06", "capabilities": ["数据", "指标"], "skills": [],
                "entitlements": {"public": True, "platform": True, "primary": False},
                "sla": {"ack_min": 30, "deliver_min": 120}},
        "r15": {"role": "r15", "capabilities": ["供应链"], "skills": [],
                "entitlements": {"public": True, "platform": False, "primary": True},
                "sla": {"ack_min": 60, "deliver_min": 480}},
    }
    rows, gaps = cu.assign(grid["cells"], cards)
    check("every_cell_has_owner", len(rows) == grid["count"])
    check("gaps_have_need", all(g.get("need") for g in gaps))

    reqs = cu.route_requests(gaps, rows, cards)
    check("requests_terminal", all(r["status"] in ("accepted", "declined", "escalated")
                                   for r in reqs))
    check("requests_have_events", all(r["events"] for r in reqs))

    dag = cu.build_dag(rows, s)
    check("dag_covers_all", sum(len(w) for w in dag["waves"]) == len(rows))

    ctr = cu.contracts(rows, cards)
    check("contracts_cover_all", sum(len(c["cells"]) for c in ctr["contracts"]) == len(rows))
    check("contracts_have_sla", all(c.get("deadline_min") for c in ctr["contracts"]))

    # 指纹复用：同一事实第二次直接复用
    facts = {}
    fake = Path("__no_project__")
    filled1, meta1 = cu.fill_cells(fake, rows, facts)
    filled2, meta2 = cu.fill_cells(fake, rows, facts)
    check("facts_written", len(facts) > 0 or all(r["status"] != "filled" for r in filled1))

    # MECE：37.4 不过，100 过
    def mk(v):
        return [{"qid": "Q1", "measure": "share", "status": "filled", "value": x} for x in v]
    check("mece_flags_incomplete", cu.mece_check(mk([13.3, 8.5, 7.8, 4.1, 3.7]))["ok"] is False)
    check("mece_accepts_full", cu.mece_check(mk([40, 30, 20, 10]))["ok"] is True)

    # 仲裁：同名同期不同值必须被记录
    arb = cu.arbitrate({"numbers": [
        {"name": "社零", "value": 100, "period": "2025"},
        {"name": "社零", "value": 101, "period": "2025"}]})
    check("arbitration_detects", arb["count"] == 1 and arb["conflicts"][0]["arbiter"])

    # 图合同
    charts = cu.chart_contracts(clarify, mk([40, 30, 20, 10]) + [
        {"qid": "Q1", "measure": "share", "status": "filled", "value": 10,
         "causal_level": "A", "dim": "对象"}], s)
    check("chart_contract_fields",
          charts["charts"] and charts["charts"][0]["data_points"] >= 3
          and "why_visual_not_text" in charts["charts"][0])

    # 24 门禁齐全
    g = cu.gates(clarify, grid, per, s, filled1, ctr, gaps, [], Path("__none__"),
                 extra={"charts": charts, "backfill": [], "branches": {"items": []},
                        "decompositions": [dec], "mece": {"ok": True, "items": []},
                        "arbitration": {"conflicts": []}, "requests": reqs})
    ids = [c["id"] for c in g["checks"]]
    check("gates_25", len(ids) == 25 and ids[0] == "G1" and ids[-1] == "G25", ids)
    check("gate_g1_fails_on_zero",
          next(c for c in g["checks"] if c["id"] == "G1")["ok"] is False)

    print(f"\n{len(OK)}/{len(OK)+len(FAIL)} passed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
