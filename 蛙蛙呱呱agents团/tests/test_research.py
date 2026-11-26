# -*- coding: utf-8 -*-
"""research 域测试（合并自 7 个文件）。

源文件：
    test_research_intake.py —— 数据 intake（quote 门禁）的回归测试（升级 P3）。
    test_research_protocol.py —— v12：调研交付契约（不含行业清单）。
    test_quote_fixtures.py —— Quote 正/负样本 fixture：strict 必须放行/拦截。
    test_quote_gate.py —— P3-4：可达性预检（research_intake）与 quote 判据（source_verify）分离。
    test_evidence_and_critic.py —— 证据图 / 论证规划 / 盲评的硬规则。
    test_mece_and_saturation.py —— test_mece_and_saturation —— MECE 互斥 + 拆卡饱和。
    test_outcome_ledger.py —— 结果台账（P6）回归测试。
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
import pytest
from core import report_flow, research_intake as ri
from core import claim_consistency as CC
from core import research_protocol as RP
import shutil
from core import research_intake
from core import card_upgrade as cu
from core import outcome_ledger as ol



# ====================================================================
# 合并自 test_research_intake.py：数据 intake（quote 门禁）的回归测试（升级 P3）。
# ====================================================================
# -*- coding: utf-8 -*-


def _project(tmp_path, quote: str = ""):
    d = tmp_path / "data"
    d.mkdir()
    (d / "sources.json").write_text(json.dumps({
        "sources": [{"id": "S01", "title": "测试来源", "type": "government",
                     "grade": "A", "url": "http://example.invalid",
                     "date": "2025-01-15", "quote": quote}]
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_collect_refs_nested():
    draft = {"sections": [{"refs": ["S01#a", "S02"]}],
             "chart": {"refs": ["S03"]}}
    assert ri.collect_refs(draft) == ["S01", "S02", "S03"]


def test_collect_refs_resolves_derived_to_source():
    draft = {"sections": [{"refs": ["D_common6_hohhot_mean", "S03"]}]}
    pack = {"numbers": [{"id": "D_common6_hohhot_mean", "source_ref": "S01"}]}
    assert ri.collect_refs(draft, pack) == ["S01", "S03"]


def test_gate_off_skips():
    out = ri.quote_gate("/nonexistent", refs=["S01"], mode="off")
    assert out["ok"] is True
    assert out["verdict"] == "SKIP"


def test_gate_no_sources_skips(tmp_path):
    out = ri.quote_gate(str(tmp_path), refs=["S01"], mode="warn")
    assert out["ok"] is True
    assert out["status"] == "no_sources"


def test_gate_warn_marks_unverified_without_quote(tmp_path):
    p = _project(tmp_path, quote="")
    out = ri.quote_gate(str(p), refs=["S01"], mode="warn")
    assert out["ok"] is False
    assert out["used_unverified"] == ["S01"]
    assert out["unverified"] == 1
    assert out["checked"] == 0


def test_gate_strict_raises_on_unverified(tmp_path):
    p = _project(tmp_path, quote="")
    with pytest.raises(report_flow.FlowError):
        ri.quote_gate(str(p), refs=["S01"], mode="strict")


def test_verify_skips_unused_sources(tmp_path):
    p = _project(tmp_path, quote="")
    q = ri.verify(str(p), only_ids=["S99"])
    assert q["schema"] == "dsh.reachability/v1"
    assert q["skipped"] == 1
    assert q["reachable"] == 0


# ====================================================================
# 合并自 test_research_protocol.py：v12：调研交付契约（不含行业清单）。
# ====================================================================
# -*- coding: utf-8 -*-


def test_plan_has_no_module_list():
    """不许再有研究模块清单：这是本版的核心约束。"""
    p = RP.plan("内蒙古调味料市场调研")
    assert "modules" not in p, "研究模块清单已删除，不许恢复"
    assert p["what_to_research"].startswith("由执行者")


def test_claim_contract_is_complete():
    p = RP.plan("任意业务线")
    fields = [c["field"] for c in p["claim_contract"]]
    for must in ("claim", "value", "quote", "url", "grade", "falsifier",
                 "boundary"):
        assert must in fields, f"结论契约缺 {must}"


def test_report_shape_serves_four_readers():
    """一人公司：老板/团队/客户/自己 四类用途必须同时被覆盖。"""
    p = RP.plan("任意业务线")
    parts = {s["part"] for s in p["report_shape"]}
    assert {"决策页", "判断", "执行清单", "证据", "边界"} <= parts


def test_review_rules_cover_conflict_and_grade():
    p = RP.plan("任意业务线")
    ids = {r["id"] for r in p["review_rules"]}
    assert {"C1", "C2", "C3", "C4"} == ids


def test_lane_switches_when_data_given():
    assert RP.plan("x").get("data_lane") == "web"
    assert RP.plan("x", project_dir=".")["data_lane"] == "given"
    assert "清洗" in RP.plan("x", project_dir=".")["lane_note"]


def test_markdown_contains_contract_not_industries():
    md = RP.to_markdown(RP.plan("内蒙古预制菜"))
    assert "一条结论必须长这样" in md
    assert "盘子多大" not in md, "方法论清单不该再出现在任务书里"


def _claims(**kw):
    base = {
        "numbers": [
            {"id": "N1", "name": "全国规模", "value": 4850, "period": "2024",
             "source_file": "S1"},
        ],
        "sources": [{"file": "S1", "grade": "B"}],
        "standfirst": "规模 4850 亿元。",
        "sections": [{"refs": ["N1"]}],
        "boundaries": ["没有省级实测值"],
    }
    base.update(kw)
    return base


def test_consistency_passes_on_clean_claims():
    res = CC.check(_claims())
    assert res["ok"] is True


def test_consistency_blocks_unexplained_conflict():
    """同一指标同期两个值，不解释口径差就不许过。"""
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    res = CC.check(c)
    assert res["ok"] is False
    assert res["issues"]["C1_unexplained_conflict"] == 1


def test_consistency_allows_explained_conflict():
    c = _claims()
    c["numbers"].append({"id": "N2", "name": "全国规模", "value": 6831.6,
                         "period": "2024", "source_file": "S1"})
    c["conflicts"] = [{"name": "全国规模", "reason": "艾媒 vs 网经社，口径不同"}]
    res = CC.check(c)
    assert res["ok"] is True
    assert res["conflicts_resolved"]


def test_consistency_blocks_missing_boundary():
    res = CC.check(_claims(boundaries=[]))
    assert res["issues"]["C4_no_boundary"] == 1


def test_consistency_different_period_is_not_conflict():
    c = _claims()
    c["numbers"].append({"id": "N3", "name": "全国规模", "value": 3626,
                         "period": "2023", "source_file": "S1"})
    assert CC.check(c)["issues"]["C1_unexplained_conflict"] == 0


# ====================================================================
# 合并自 test_quote_fixtures.py：Quote 正/负样本 fixture：strict 必须放行/拦截。
# ====================================================================
# -*- coding: utf-8 -*-


FIX = Path(__file__).resolve().parent / "fixtures"


def _copy(tmp_path, name):
    dst = tmp_path / name
    shutil.copytree(FIX / name, dst)
    return dst


def test_quote_ok_fixture_strict_passes(tmp_path):
    p = _copy(tmp_path, "quote_ok_project")
    out = ri.quote_gate(str(p), refs=["S01", "S02"], mode="strict")
    assert out["ok"] is True
    assert out["used_unverified"] == []
    assert out["ok_count"] == 2


def test_quote_gap_fixture_strict_blocks(tmp_path):
    p = _copy(tmp_path, "quote_gap_project")
    with pytest.raises(report_flow.FlowError):
        ri.quote_gate(str(p), refs=["S01", "S02"], mode="strict")


# ====================================================================
# 合并自 test_quote_gate.py：P3-4：可达性预检（research_intake）与 quote 判据（source_verify）分离。
# ====================================================================
# -*- coding: utf-8 -*-


PAGE = "本报告显示 2025 年样本规模同比增长 12.3%，其中头部主体占比 48%。"
SOURCES = {"sources": [
    {"id": "S1", "file": "s1.html", "url": "https://example.invalid/a",
     "date": "2025-11-20", "quote": "样本规模同比增长 12.3%", "grade": "A"},
    {"id": "S2", "file": "s2.html", "url": "https://example.invalid/b",
     "date": "2025-11-20", "quote": "这句话在页面里根本不存在", "grade": "B"},
]}


def _proj(tmp_path: Path) -> Path:
    d = tmp_path / "proj"
    (d / "data").mkdir(parents=True)
    (d / "data" / "sources.json").write_text(
        json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    return d


def test_verify_only_checks_reachability(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))
    out = research_intake.verify(str(p))
    assert out["schema"] == "dsh.reachability/v1"
    assert out["reachable"] == 2 and out["unreachable"] == 0
    assert "ok" not in out and "mismatch" not in out   # 不再给 quote 结论
    assert (p / "data" / "reachability.json").is_file()


def test_quote_gate_delegates_to_source_verify(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))
    g = research_intake.quote_gate(str(p), mode="warn", fetch=lambda url: PAGE)
    assert g["ok"] is False
    assert g["ok_count"] == 1 and g["mismatch"] == 1
    assert set(g["used_unverified"]) == {"S2"}
    items = {r["id"]: r for r in g["items"]}
    assert items["S1"]["status"] == "verified"
    assert items["S2"]["status"] == "quote_not_found"
    saved = json.loads((p / "data" / "quote_check.json").read_text(encoding="utf-8"))
    assert saved["schema"] == "dsh.quote_check/v1"


def test_quote_gate_marks_unreachable(tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setattr(research_intake, "_fetch", lambda url: (PAGE, ""))

    def boom(url):
        raise TimeoutError("timed out")

    g = research_intake.quote_gate(str(p), mode="warn", fetch=boom)
    assert g["ok"] is False and g["unreachable"] == 2


def test_quote_gate_skip_when_no_sources(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    g = research_intake.quote_gate(str(d), mode="warn")
    assert g["ok"] is True and g["status"] == "no_sources"


# ====================================================================
# 合并自 test_mece_and_saturation.py：test_mece_and_saturation —— MECE 互斥 + 拆卡饱和。
# ====================================================================
# -*- coding: utf-8 -*-


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


# ====================================================================
# 合并自 test_outcome_ledger.py：结果台账（P6）回归测试。
# ====================================================================
# -*- coding: utf-8 -*-


def test_add_list_review_summary(tmp_path):
    p = tmp_path / "ledger.json"
    e = ol.add("RPT-1", "structure", "6 涨 6 跌", "哪些品类继续做",
               "2026-12-31", path=p)
    assert e["status"] == "open"
    assert len(ol.list_entries(path=p)) == 1

    # 同一 report/claim 的 open 不重复登记
    e2 = ol.add("RPT-1", "structure", "6 涨 6 跌", "哪些品类继续做",
                "2026-12-31", path=p)
    assert e2["id"] == e["id"]
    assert len(ol.list_entries(path=p)) == 1

    ol.review(e["id"], "hit", "复盘：方向一致", path=p)
    assert ol.list_entries(path=p)[0]["status"] == "hit"
    s = ol.summary(path=p, today="2026-12-01")
    assert s["total"] == 1 and s["hit"] == 1 and s["hit_rate"] == 1.0


def test_overdue_and_due_soon(tmp_path):
    p = tmp_path / "ledger.json"
    ol.add("RPT-1", "a", "A", "D", "2026-11-01", path=p)
    ol.add("RPT-1", "b", "B", "D", "2026-12-10", path=p)
    s = ol.summary(path=p, today="2026-12-01")
    assert s["overdue"] == 1
    assert s["due_soon"] == 1


def test_seed_from_trace(tmp_path):
    p = tmp_path / "ledger.json"
    trace = {"findings": [{"key": "structure", "title": "结构判断"},
                          {"key": "economics", "title": "单位经济"}]}
    seeded = ol.seed_from_trace("RPT-1", "经营分析", trace,
                                deadline="2026-12-31", path=p)
    assert len(seeded) == 2
    assert len(ol.list_entries(path=p)) == 2


def test_review_requires_result(tmp_path):
    p = tmp_path / "ledger.json"
    e = ol.add("RPT-1", "a", "A", "D", "2026-12-31", path=p)
    try:
        ol.review(e["id"], "hit", "", path=p)
    except ValueError as exc:
        assert "result" in str(exc)
    else:
        raise AssertionError("空 result 应报错")


def test_hit_rate_with_hit_miss_void(tmp_path):
    """不等 2027：合成 hit/miss/void，验证命中率分母排除 void。"""
    p = tmp_path / "ledger.json"
    a = ol.add("RPT-1", "a", "A", "D", "2026-12-31", path=p)
    b = ol.add("RPT-1", "b", "B", "D", "2026-12-31", path=p)
    c = ol.add("RPT-1", "c", "C", "D", "2026-12-31", path=p)
    ol.review(a["id"], "hit", "方向一致", path=p)
    ol.review(b["id"], "miss", "方向反了", path=p)
    ol.review(c["id"], "void", "口径变了", path=p)
    s = ol.summary(path=p, today="2026-12-01")
    assert s["hit"] == 1 and s["miss"] == 1 and s["void"] == 1
    assert s["hit_rate"] == 0.5


def test_calibration_no_data_then_calibrated(tmp_path):
    p = tmp_path / "ledger.json"
    e = ol.add("RPT-1", "a", "A", "D", "2026-12-31", path=p)
    cal = ol.calibrate(path=p, month="2026-11")
    assert cal["verdict"] == "NO_DUE_DATA"
    assert cal["summary"]["hit_rate"] is None
    ol.review(e["id"], "hit", "方向一致", path=p)
    cal2 = ol.calibrate(path=p, month="2026-11")
    assert cal2["verdict"] == "CALIBRATED"
    assert cal2["summary"]["hit_rate"] == 1.0
