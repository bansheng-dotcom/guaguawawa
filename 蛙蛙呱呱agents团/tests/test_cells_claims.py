# -*- coding: utf-8 -*-
"""cells → claims 的自测：自己出题，自己验。

场景：4 个 must 问、2 个角色、每问 6 格、每问填 4 格；
验：编译出 claims、节数对、collect 能收、缺口不编数。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import cells_claims, dispatch  # noqa: E402

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
    merged, problems = dispatch.collect(str(base), min_sources=0)
    assert not problems, problems
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
