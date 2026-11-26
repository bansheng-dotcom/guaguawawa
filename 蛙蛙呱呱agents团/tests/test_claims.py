# -*- coding: utf-8 -*-
"""claims 域测试（合并自 5 个文件）。

源文件：
    test_claim_card.py —— ClaimCard schema 的回归测试（升级 P1）。
    test_claim_contracts.py —— P8b 数据契约：计数 / 假设 / 公式。
    test_claim_gate.py —— P9：ClaimCard 头条门禁。
    test_cells_claims.py —— cells → claims 的自测：自己出题，自己验。
    test_cells_unified.py —— P5-5：三套读数统一 + 双写对账。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import importlib.util
import types
import json
import tempfile
from core.claims import cells_claims
from core.cards import dispatch
from core.claims import cells_claims, cells_unified

from core.claims import claims_v4 as c4


# ====================================================================
# 合并自 test_claim_contracts.py：P8b 数据契约：计数 / 假设 / 公式。
# ====================================================================
# -*- coding: utf-8 -*-


SKILLS = TEAM / "r01-waquanju-ceo" / "skills"
_pkg = types.ModuleType("skills")
_pkg.__path__ = [str(SKILLS)]  # type: ignore[attr-defined]
sys.modules.setdefault("skills", _pkg)
_SPEC = importlib.util.spec_from_file_location(
    "skills.s09_interpret", SKILLS / "s09_interpret.py")
s09 = importlib.util.module_from_spec(_SPEC)
sys.modules["skills.s09_interpret"] = s09
_SPEC.loader.exec_module(s09)  # type: ignore[union-attr]

PACK = {"numbers": [{"id": "A1", "name": "数值", "value": 1, "unit": "元",
                     "period": "2025", "source_file": "x.json"}]}


def _draft(reading: str, assumptions=None, records=None):
    return {"standfirst": "测试 1 元",
            "sections": [{"title": "测试：1 元", "question": "q", "refs": ["A1"],
                          "reading": [{"text": reading, "refs": ["A1"]},
                                      {"text": "口径说明", "refs": ["A1"]}],
                          "assumptions": assumptions or []}],
            "counts": {"n": 2},
            "assumption_records": records or []}


def _sections_check(draft):
    return next(x for x in s09._check_sections(draft, PACK)
                if x["id"] == "sections_valid")


def test_count_registry_allows_registered_only():
    ok = _sections_check(_draft("2 个"))
    assert ok["ok"] is True, ok
    bad = _sections_check(_draft("29 个"))
    assert bad["ok"] is False
    assert "29" in str(bad)


def test_assumption_requires_source():
    bad = _sections_check(_draft("7.7 元", assumptions=[7.7]))
    assert bad["ok"] is False
    good = _sections_check(
        _draft("7.7 元", assumptions=[7.7],
               records=[{"value": 7.7, "source": "method:economics"}]))
    assert good["ok"] is True, good


def test_no_arbitrary_ratio():
    refs = [{"value": 1}, {"value": 2}]
    assert s09._explainable(1.0, refs) is True
    assert s09._explainable(0.5, refs) is False       # 1/2 不再放行
    assert s09._explainable(3.0, refs) is True        # 1+2 仍允许


# ====================================================================
# 合并自 test_cells_claims.py：cells → claims 的自测：自己出题，自己验。
# ====================================================================
# -*- coding: utf-8 -*-


SEM = """schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [中国, 亚太]
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
- id: revenue
  type: simple
  agg: sum
  expr: revenue
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: revenue
  denominator: revenue@total
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 测试口径
  affects: [revenue]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def _project() -> Path:
    base = Path(tempfile.mkdtemp(prefix="guagua_cells_"))
    (base / "plan").mkdir()
    (base / "out").mkdir()
    (base / "out_v3").mkdir()
    asks = [{"id": f"Q{i}", "text": f"问题{i}的规模与结构如何", "type": "结构型",
             "must": True, "tier": "must"} for i in range(1, 5)]
    (base / "clarify.json").write_text(json.dumps(
        {"schema": "dsh.report.clarify/v1", "intent": "自测", "status": "confirmed",
         "asks": asks, "coverage": {"covered": {}, "missing": []}}, ensure_ascii=False),
        encoding="utf-8")
    (base / "semantic_layer.yaml").write_text(SEM, encoding="utf-8")

    cells, assign = [], []
    owners = {"Q1": "r05", "Q2": "r05", "Q3": "r06", "Q4": "r06"}
    for q in range(1, 5):
        qid = f"Q{q}"
        for j, dim in enumerate(("对象", "空间", "时间"), 1):
            for k in range(2):
                cid = f"{qid}.{dim}.{k}"
                cells.append({"cell_id": cid, "qid": qid, "dim": dim,
                              "entity": f"{dim}{k}", "measure": "revenue",
                              "measure_id": "revenue",
                              "grain": "G_region_year", "period": "2025",
                              "status": "open", "causal_level": "A",
                              "caliber": {"scope": "全渠道", "currency": "CNY",
                                          "price_basis": "零售价"},
                              "quality": {x: "ok" for x in (
                                  "completeness", "accuracy", "consistency",
                                  "timeliness", "uniqueness", "validity")}})
                assign.append({"cell_id": cid, "owner": owners[qid],
                               "why": "能力匹配", "match": "strong"})
    (base / "plan" / "grid.json").write_text(json.dumps(
        {"schema": "dsh.grid/v1", "cells": cells, "count": len(cells)}, ensure_ascii=False),
        encoding="utf-8")
    (base / "plan" / "dispatch.json").write_text(json.dumps({
        "assignments": assign,
        "contracts": [{"task_id": f"T-{r}", "owner": r, "cells": []}
                      for r in ("r05", "r06")],
    }, ensure_ascii=False), encoding="utf-8")

    # 来源账本（2 条）
    src = [{"file": "r05:S1", "kind": "web", "title": "来源一", "org": "机构一",
            "url": "https://example.com/a", "date": "2025-01-01", "grade": "A",
            "quote": "这是一条足够长的原文引文用于校验"},
           {"file": "r06:S2", "kind": "web", "title": "来源二", "org": "机构二",
            "url": "https://example.com/b", "date": "2025-01-01", "grade": "B",
            "quote": "这也是足够长的一段原文引文用于校验"}]
    (base / "out" / "claims_merged.json").write_text(json.dumps(
        {"numbers": [], "sources": src}, ensure_ascii=False), encoding="utf-8")

    # 每问填 4 格
    filled = []
    seen = {}
    for c in cells:
        seen[c["qid"]] = seen.get(c["qid"], 0) + 1
        if seen[c["qid"]] <= 4:
            filled.append({**c, "status": "filled", "value": 100 + seen[c["qid"]],
                           "unit": "亿元", "period": "2025",
                           "source_file": "r05:S1" if c["qid"] in ("Q1", "Q2") else "r06:S2",
                           "grade": "A"})
        else:
            filled.append({**c, "status": "unavailable", "tried": ["公开检索"],
                           "why": "无同口径数据"})
    (base / "out_v3" / "cells_filled.json").write_text(json.dumps(
        {"cells": filled}, ensure_ascii=False), encoding="utf-8")

    for r in ("r05", "r06"):
        (base / "cards" / r).mkdir(parents=True)
        (base / "cards" / r / "claims.template.json").write_text(json.dumps({
            "schema": "dsh.agent.claims/v1", "role": r,
            "dispatch": {"nonce": f"n-{r}", "role": r, "by": "", "questions": []},
            "meta": {"title": "自测", "intent": "自测", "doc_type": "调研报告",
                     "profile": "research"}}, ensure_ascii=False), encoding="utf-8")
    return base


def test_build_cells_to_claims():
    base = _project()
    res = cells_claims.build(base)
    assert res["ok"], res
    roles = {x["role"]: x for x in res["roles"]}
    assert set(roles) == {"r05", "r06"}
    assert roles["r05"]["sections"] == 2
    assert roles["r06"]["sections"] == 2
    d = json.loads((base / "cards" / "r05" / "claims.json").read_text(encoding="utf-8"))
    assert d["dispatch"]["by"] == "dsh-subagent-r05"
    assert len(d["sections"]) == 2
    for s in d["sections"]:
        assert s["refs"] and s["chart"]["items"] and s["falsifier"]
        assert len(s["reading"]) >= 4


def test_collect_accepts_compiled_claims():
    base = _project()
    assert cells_claims.build(base)["ok"]
    # 夹具没有 coverage/issued.json，属于老卡：走显式降级通道（新契约默认拒收）
    merged, problems = dispatch.collect(str(base), min_sources=0, allow_legacy=True)
    assert not problems, problems
    assert merged["dispatch"]["mode"] == "legacy"
    assert "legacy_no_issued" in merged["degraded"]
    assert merged["evidence"]["sections"] == 4
    assert merged["evidence"]["numbers"] >= 12


def test_missing_source_is_rejected():
    base = _project()
    p = base / "out_v3" / "cells_filled.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["cells"][0]["source_file"] = "rXX:S9"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    res = cells_claims.build(base)
    assert res["ok"] is False and res["stage"] == "sources"


def test_no_cells_is_rejected():
    base = _project()
    (base / "out_v3" / "cells_filled.json").write_text("{}", encoding="utf-8")
    res = cells_claims.build(base)
    assert res["ok"] is False and res["stage"] == "cells"


# ---------------- DoD #2：collect 读卡前的自动编译桥 ----------------

def test_bridge_compiles_roles_without_claims():
    base = _project()
    assert not (base / "cards" / "r05" / "claims.json").exists()
    res = dispatch._bridge_cells_to_claims(str(base))
    assert res.get("bridged_roles") == ["r05", "r06"], res
    assert (base / "cards" / "r05" / "claims.json").is_file()
    assert (base / "cards" / "r06" / "claims.json").is_file()


def test_bridge_skips_when_all_roles_have_claims():
    base = _project()
    assert cells_claims.build(base)["ok"]
    res = dispatch._bridge_cells_to_claims(str(base))
    assert res.get("skipped") is True


def test_bridge_skips_without_grid():
    import tempfile
    empty = Path(tempfile.mkdtemp(prefix="guagua_nogrid_"))
    res = dispatch._bridge_cells_to_claims(str(empty))
    assert res.get("skipped") is True


def test_collect_uses_bridge_output():
    """不预先编译 claims，collect 也能靠桥把格子变成收得进来的判断。"""
    base = _project()
    merged, problems = dispatch.collect(str(base), min_sources=0, allow_legacy=True)
    assert not problems, problems
    assert merged["cells_bridge"].get("bridged_roles") == ["r05", "r06"]
    assert merged["evidence"]["sections"] == 4


# ====================================================================
# 合并自 test_cells_unified.py：P5-5：三套读数统一 + 双写对账。
# ====================================================================
# -*- coding: utf-8 -*-


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


# ====================================================================
# 合并自 test_claims_v4.py（原为无 pytest 的脚本式自测，2026-11-25 转正）
# ====================================================================
def _c4_claim():
    rows = [{"label": "社区自雇", "value": 5.85}, {"label": "社区雇人", "value": 8.97},
            {"label": "前置仓", "value": 46.81}, {"label": "商场店", "value": 26.81}]
    fs = c4.detect(rows, " 万元")
    return {"id": "C1", "claim": "10 万预算只有社区自雇店能打平",
            "decision_rank": 1,
            "headline": "社区自雇 5.85 万元/月",
            "table": {"columns": ["形态", "平衡点"], "rows": [["社区自雇", 5.85]]},
            "action": "先做社区自雇店，不做前置仓",
            "falsifier": "若平衡点超过 8 万元/月则本节作废",
            "rows": rows, "encoding": {"mark": "bar", "y": "label"},
            "unit": "万元", "refs": ["N1", "N2", "N3", "N4"],
            "findings": fs, "warrant": "平衡点=固定成本÷(毛利率-变动费用率)",
            "tier": "main"}


def test_claims_v4_detect_encode_validate():
    claim = _c4_claim()
    types = {f["type"] for f in claim["findings"]}
    assert {"extreme", "gap", "concentration"} <= types
    ch = c4.encoding_to_chart(claim)
    assert ch["type"] == "hbar" and len(ch["items"]) == 4
    assert ch["unit_meta"] == "万元"
    assert ch["refs"] == ["N1", "N2", "N3", "N4"]
    assert c4.validate_v4([claim]) == []
    bad = dict(claim, findings=[], warrant="")
    errs = c4.validate_v4([bad])
    assert any("findings" in e for e in errs) and any("warrant" in e for e in errs)


def test_claims_v4_sections_and_appendix():
    claim = _c4_claim()
    sec = c4.claim_to_section(claim, 1)
    assert len(sec["reading"]) >= 2 and sec["chart"] and sec["boundary"] == ""
    assert sec["title"] == claim["claim"]
    sup = dict(claim, id="C2", tier="support")
    secs = c4.build_sections({"claims": [sup, claim]})
    assert secs[-1].get("appendix") is True and secs[0].get("appendix") is not True
