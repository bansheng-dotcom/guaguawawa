# -*- coding: utf-8 -*-
"""拆卡 SOP 发卡门禁的回归：五轴齐才发卡，语义层缺失就拒绝。"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import card_issue, report_clarify, report_dispatch  # noqa: E402

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
    assert report_clarify.confirm(str(base))["ok"]
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
