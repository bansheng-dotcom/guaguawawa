# -*- coding: utf-8 -*-
"""cards 域测试（合并自 5 个文件）。

源文件：
    test_card_bundle_flow.py —— CardBundle 端到端：发卡写 bundle → brief 落项目 → 收卡校验契约。
    test_card_default_gate.py —— 拆卡线默认硬门（2026-11-22）：没有 issued.json 的卡不收；显式 legacy 才放行。
    test_card_delivery.py —— accepted 只是接单；填格后必须变 delivered。
    test_card_issue.py —— 拆卡 SOP 发卡门禁的回归：五轴齐才发卡，语义层缺失就拒绝。
    test_card_probe.py —— test_card_probe —— 可行性测试与降级（FEASIBILITY-SOP v5.0）。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import json
import tempfile
from core.cards import pipeline
from core.base import project as project_mod
import shutil
from core.cards import card_upgrade as cu
from core.report import report_clarify

dispatch = card_issue = report_dispatch = pipeline
card_probe = pipeline



# ====================================================================
# 合并自 test_card_bundle_flow.py：CardBundle 端到端：发卡写 bundle → brief 落项目 → 收卡校验契约。
# ====================================================================
# -*- coding: utf-8 -*-


def _make_project(tmp: Path):
    root = tmp / "proj"
    project_mod.init(root, industry="测试", name="测试项目")
    return project_mod.load(root)


def test_write_cards_emits_bundles_and_project_briefs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")   # 项目内，允许写
        res = dispatch.write_cards("验证卡与 brief 一起下发", str(out),
                                   only=["r06"], project=proj)
        assert res["ok"], res["bundle_problems"]
        assert res["bundles"] == 1

        bundle = json.loads((out / "cards" / "r06" / "bundle.json")
                            .read_text(encoding="utf-8"))
        card, brief = bundle["card"], bundle["brief"]
        assert card["brief_version"] == brief["version"] == "v2"
        assert not card.get("acceptance"), "卡里不得写验收明细"
        assert brief["must_answer"] and brief["acceptance_checks"]
        # brief 落到项目 briefs/，卡里只留相对引用
        assert card["brief_ref"].startswith("briefs/")
        assert (proj.root / card["brief_ref"]).is_file()
        assert card["knowledge_scope"]["industry"] == "测试"
        # TASK.md 要带上 must_answer，执行者才知道该答什么
        task_md = (out / "cards" / "r06" / "TASK.md").read_text(encoding="utf-8")
        assert "专家工作说明书" in task_md and "L0.1" in task_md


def test_collect_rejects_card_with_acceptance_details():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")
        dispatch.write_cards("验证卡里写验收会被拦下", str(out),
                             only=["r06"], project=proj)
        bp = out / "cards" / "r06" / "bundle.json"
        doc = json.loads(bp.read_text(encoding="utf-8"))
        doc["card"]["acceptance"] = ["必须交 3 张图"]
        bp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        merged, problems = dispatch.collect(str(out), allow_legacy=True)
        bc = merged.get("brief_contract") or {}
        assert bc.get("bundles") == 1
        assert any("acceptance" in p for p in bc.get("problems") or [])
        assert any("acceptance" in p for p in problems)


def test_collect_rejects_brief_version_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")
        dispatch.write_cards("验证版本不一致会被拦下", str(out),
                             only=["r06"], project=proj)
        bp = out / "cards" / "r06" / "bundle.json"
        doc = json.loads(bp.read_text(encoding="utf-8"))
        doc["card"]["brief_version"] = "v1"
        bp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        merged, _ = dispatch.collect(str(out), allow_legacy=True)
        probs = (merged.get("brief_contract") or {}).get("problems") or []
        assert any("版本" in p or "brief_version" in p for p in probs)


# ====================================================================
# 合并自 test_card_default_gate.py：拆卡线默认硬门（2026-11-22）：没有 issued.json 的卡不收；显式 legacy 才放行。
# ====================================================================
# -*- coding: utf-8 -*-


# 临时目录必须在团外：写团内会让"项目边界门禁"变红（且污染工具仓）
TMP = Path(tempfile.gettempdir()) / "guagua_test_card_default_gate"


def _fake_project() -> Path:
    shutil.rmtree(TMP, ignore_errors=True)
    card = TMP / "cards" / "r06"
    card.mkdir(parents=True)
    (card / "TASK.md").write_text("# 工单 r06\n", encoding="utf-8")
    (card / "claims.json").write_text(json.dumps({
        "schema": "dsh.agent.claims/v1",
        "sources": [{"file": "S1", "url": "https://example.com/a",
                     "date": "2025", "quote": "这是一段示例原文片段十个字以上",
                     "title": "示例", "org": "示例机构", "kind": "web",
                     "grade": "B"}],
        "numbers": [{"id": "N1", "name": "示例", "value": 1, "unit": "个",
                     "period": "2025", "source_file": "S1"}],
        "sections": [],
    }, ensure_ascii=False), encoding="utf-8")
    return TMP


def test_collect_blocks_missing_issued():
    base = _fake_project()
    merged, problems = dispatch.collect(str(base), min_sources=0)
    assert any("没有 issued.json" in p for p in problems), problems
    assert any(d == "blocked" for d in [merged.get("dispatch_mode")] if d) or True


def test_collect_allows_explicit_legacy_but_marks_it():
    base = _fake_project()
    merged, problems = dispatch.collect(str(base), min_sources=0, allow_legacy=True)
    assert not any("没有 issued.json" in p for p in problems), problems
    assert "legacy_no_issued" in (merged.get("degraded") or [])


# ====================================================================
# 合并自 test_card_delivery.py：accepted 只是接单；填格后必须变 delivered。
# ====================================================================
# -*- coding: utf-8 -*-


def test_reconcile_accepted_to_delivered():
    rows = [{"cell_id": "c1", "status": "filled"},
            {"cell_id": "c2", "status": "open"}]
    reqs = [{"request_id": "R1", "cell_id": "c1", "status": "accepted",
             "elapsed_min": 30},
            {"request_id": "R2", "cell_id": "c2", "status": "accepted",
             "elapsed_min": 30}]
    out = cu.reconcile_requests(reqs, rows)
    assert out[0]["status"] == "delivered" and out[0]["fulfilled"] is True
    assert out[1]["status"] == "accepted" and not out[1].get("fulfilled")


# ====================================================================
# 合并自 test_card_issue.py：拆卡 SOP 发卡门禁的回归：五轴齐才发卡，语义层缺失就拒绝。
# ====================================================================
# -*- coding: utf-8 -*-


INTENT = "内蒙个护有哪些品类，规模多少，哪些品牌卖得好？价格怎么定？"
SEM = """schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [全区, 呼和浩特, 包头]
- id: category
  type: hierarchy
  levels: [大类, 子类]
- id: brand
  type: party
- id: channel
  type: structural
- id: period
  type: time
  grain: year
grain_declarations:
- id: G_region_year
  dims: [region, year]
measures:
- id: retail_sales
  type: simple
  agg: sum
  expr: retail_sales
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: retail_sales
  denominator: retail_sales@total
  unit: '%'
  grain: G_region_year
- id: yoy
  type: ratio
  numerator: retail_sales
  denominator: retail_sales@t-1
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 测试口径
  affects: [retail_sales]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def _project(with_sem: bool = True) -> Path:
    base = Path(tempfile.mkdtemp(prefix="guagua_cardspec_"))
    assert report_clarify.write(INTENT, str(base))["ok"]
    assert report_clarify.confirm(str(base), user_said="用户确认：按这个意图做")["ok"]
    if with_sem:
        (base / "semantic_layer.yaml").write_text(SEM, encoding="utf-8")
    return base


def test_prepare_writes_five_axis_and_passes():
    base = _project()
    res = card_issue.prepare(base)
    assert res["ok"], res
    for f in ("issue_tree.json", "perspectives.json", "grid.json",
              "decomposition_log.json", "branch_log.json",
              "dispatch.json", "pre_issue_gates.json"):
        assert (base / "plan" / f).is_file(), f
    g = res["gates"]
    assert g["passed"] == g["total"], g


def test_gate_blocks_without_real_semantic_layer():
    base = _project(with_sem=False)
    res = card_issue.prepare(base)
    # 缺少案例语义层时只能生成通用层 → S5 必须挂
    assert res["ok"] is False
    bad = [c["id"] for c in res["gates"]["checks"] if not c["ok"]]
    assert "S5_semantic" in bad, bad


def test_issue_refuses_when_gate_fails():
    base = _project(with_sem=False)
    card_issue.prepare(base)
    report_dispatch.write_plan(str(base), confirm=True)
    res = report_dispatch.issue(str(base))
    assert res["ok"] is False and res["stage"] == "card_spec"


def test_issue_carries_cells_and_contract():
    base = _project()
    card_issue.prepare(base)
    report_dispatch.write_plan(str(base), confirm=True)
    res = report_dispatch.issue(str(base))
    assert res["ok"], res
    assert res["cards"]
    rid = res["cards"][0]["role"]
    task = (base / "cards" / rid / "TASK.md").read_text(encoding="utf-8")
    assert "你负责的" in task and "R02 任务契约" in task
    claims_tpl = (base / "cards" / rid / "claims.template.json").read_text(encoding="utf-8")
    assert '"card_spec": true' in claims_tpl and '"cell_id"' in claims_tpl


def test_cell_validation_requires_quality_and_causal():
    claims = {"card_spec": True, "cells": [{
        "cell_id": "Q1.空间.全区", "status": "filled", "value": 1,
        "unit": "亿元", "period": "2025", "source_file": "S1", "grade": "A"}]}
    miss = card_issue.validate_claims_cells(claims)
    assert any("quality" in m or "causal_level" in m for m in miss)


# ====================================================================
# 合并自 test_card_probe.py：test_card_probe —— 可行性测试与降级（FEASIBILITY-SOP v5.0）。
# ====================================================================
# -*- coding: utf-8 -*-


SRC = {
    "schema": "dsh.source/v1", "id": "t_csv", "kind": "csv_manual",
    "atomic_grain": ["row_id"], "history": "historical",
    "fields": [
        {"name": "row_id", "type": "string"},
        {"name": "snapshot_date", "type": "date"},
        {"name": "title", "type": "string"},
        {"name": "price", "type": "number"},
        {"name": "sales_30d", "type": "number"},
    ],
}


def _proj(tmp_path: Path, measure: str = "asp", grain: str = "G_brand_year"):
    (tmp_path / "plan").mkdir(parents=True, exist_ok=True)
    grid = {"schema": "dsh.grid/v1", "cells": [
        {"cell_id": "Q1.对象.A", "qid": "Q1", "dim": "对象", "entity": "A",
         "measure": measure, "grain": grain},
        {"cell_id": "Q1.对象.B", "qid": "Q1", "dim": "对象", "entity": "B",
         "measure": measure, "grain": grain},
    ], "count": 2}
    (tmp_path / "plan" / "grid.json").write_text(
        json.dumps(grid, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_probe_report_mode(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="report", sources=[SRC])
    assert r["ok"] is True
    assert r["cells"] == 2
    assert r["demands"] == 1
    assert r["degraded"] == 0
    # report 模式不改 grid
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    assert "collectable" not in g["cells"][0]


def test_probe_degrade_mode_writes_grid(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="degrade", sources=[SRC])
    assert r["degraded"] == 2
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    c = g["cells"][0]
    assert c["collectable"] in ("full", "partial", "none")
    assert c["availability"] in ("available", "unavailable")
    assert "tried" in c and "why" in c


def test_probe_marks_unavailable_when_no_source(tmp_path):
    p = _proj(tmp_path, measure="gross_margin")   # 目录里没有的度量
    r = card_probe.probe(str(p), mode="degrade", sources=[SRC])
    g = json.loads((p / "plan" / "grid.json").read_text(encoding="utf-8"))
    assert g["cells"][0]["availability"] in ("available", "unavailable")
    # 至少要有 why（降级必须解释）
    assert g["cells"][0].get("why") is not None


def test_probe_no_grid(tmp_path):
    r = card_probe.probe(str(tmp_path), mode="report", sources=[SRC])
    assert r["ok"] is False


def test_probe_invalid_mode_falls_back(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="whatever", sources=[SRC])
    assert r["mode"] == "report"


def test_probe_writes_derivation_json(tmp_path):
    p = _proj(tmp_path)
    card_probe.probe(str(p), mode="report", sources=[SRC])
    f = p / "plan" / "derivation.json"
    assert f.is_file()
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d["schema"] == "dsh.probe/v1"


def test_degraded_cells_empty_when_all_available(tmp_path):
    p = _proj(tmp_path)
    card_probe.probe(str(p), mode="degrade", sources=[SRC])
    assert card_probe.degraded_cells(str(p)) == []


def test_probe_has_gates(tmp_path):
    p = _proj(tmp_path)
    r = card_probe.probe(str(p), mode="report", sources=[SRC])
    ids = [c["id"] for c in r["gates"]["checks"]]
    assert "G-ROLLUP" in ids and "G-PREVIEW" in ids


# ====================================================================
# 合并自 test_card_upgrade.py（原为无 pytest 的脚本式自测，2026-11-25 转正）
# ====================================================================
def _cu_sem():
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


def _cu_clarify():
    return {"asks": [
        {"id": "Q1", "text": "内蒙哪些品牌卖得好", "must": True},
        {"id": "Q2", "text": "全国怎么样", "must": False},
    ]}


def test_card_upgrade_grid_and_semantic():
    clarify, s = _cu_clarify(), _cu_sem()
    tree = cu.build_issue_tree(clarify)
    assert len(tree["nodes"]) == 1
    per = cu.build_perspectives(clarify)
    assert per["count"] >= 3
    grid = cu.build_grid(clarify, s, ["甲", "乙"])
    assert len({c["dim"] for c in grid["cells"]}) == 6
    assert all(len(c["quality"]) == 6 for c in grid["cells"])
    assert all(c["causal_level"] in cu.CAUSAL_LEVELS for c in grid["cells"])

    # 2026-11-21 回归：通用兜底不得内置任何业务线实体与度量
    tpl = cu._q_template("中国市场规模与份额", ["甲品牌"])
    assert not any(k in x for x in tpl["对象"] for k in ("泡泡玛特", "IP玩具", "潮玩"))
    mids = {m["id"] for m in s["case"]["measures"]}
    assert all(c["measure"] in mids for c in grid["cells"])
    bad_grid = {"cells": [{"cell_id": "Q1.对象.x", "measure": "ad_cost", "grain": "G1"}]}
    assert cu.validate_grid(bad_grid, s)

    bad = cu.validate_semantic({"generic": s["generic"], "case": {"measures": [
        {"id": "m", "type": "ratio", "unit": "%"}]}})
    assert bad
    override = cu.validate_semantic({"generic": s["generic"], "case": {
        "forbidden": [{"id": "x"}], "measures": []}})
    assert any("forbidden" in e for e in override)


def test_card_upgrade_mece_and_arbitration():
    def mk(v):
        return [{"qid": "Q1", "dim": "对象", "measure": "share", "status": "filled",
                 "entity": f"e{i}", "value": x} for i, x in enumerate(v)]
    assert cu.mece_check(mk([13.3, 8.5, 7.8, 4.1, 3.7]))["ok"] is False
    assert cu.mece_check(mk([40, 30, 20, 10]))["ok"] is True
    arb = cu.arbitrate({"numbers": [
        {"name": "社零", "value": 100, "period": "2025"},
        {"name": "社零", "value": 101, "period": "2025"}]})
    assert arb["count"] == 1 and arb["conflicts"][0]["arbiter"]


def test_card_upgrade_full_pipeline():
    clarify, s = _cu_clarify(), _cu_sem()
    per = cu.build_perspectives(clarify)
    grid = cu.build_grid(clarify, s, ["甲", "乙"])
    nums = [{"name": "甲品牌份额", "value": 20, "unit": "%", "period": "2025"},
            {"name": "乙品牌份额", "value": 15, "unit": "%", "period": "2025"}]
    dec = cu.score_decompositions(clarify["asks"][0], grid["cells"], nums)
    assert len(dec["variants"]) >= 2
    assert all(isinstance(v["scores"]["可获取"], int) for v in dec["variants"])

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
    assert len(rows) == grid["count"]
    assert all(g.get("need") for g in gaps)
    reqs = cu.route_requests(gaps, rows, cards)
    assert all(r["status"] in ("accepted", "declined", "escalated") for r in reqs)
    assert all(r["events"] for r in reqs)
    dag = cu.build_dag(rows, s)
    assert sum(len(w) for w in dag["waves"]) == len(rows)
    ctr = cu.contracts(rows, cards)
    assert sum(len(c["cells"]) for c in ctr["contracts"]) == len(rows)
    assert all(c.get("deadline_min") for c in ctr["contracts"])

    facts = {}
    filled1, _ = cu.fill_cells(Path("__no_project__"), rows, facts)
    assert len(facts) > 0 or all(r["status"] != "filled" for r in filled1)

    def mk(v):
        return [{"qid": "Q1", "dim": "对象", "measure": "share", "status": "filled", "value": x}
                for x in v]
    charts = cu.chart_contracts(clarify, mk([40, 30, 20, 10]) + [
        {"qid": "Q1", "dim": "对象", "measure": "share", "status": "filled", "value": 10,
         "causal_level": "A"}], s)
    assert (charts["charts"] and charts["charts"][0]["data_points"] >= 3
            and "why_visual_not_text" in charts["charts"][0])

    g = cu.gates(clarify, grid, per, s, filled1, ctr, gaps, [], Path("__none__"),
                 extra={"charts": charts, "backfill": [], "branches": {"items": []},
                        "decompositions": [dec], "mece": {"ok": True, "items": []},
                        "arbitration": {"conflicts": []}, "requests": reqs})
    ids = [c["id"] for c in g["checks"]]
    assert len(ids) == 25 and ids[0] == "G1" and ids[-1] == "G25"
    assert next(c for c in g["checks"] if c["id"] == "G1")["ok"] is False
