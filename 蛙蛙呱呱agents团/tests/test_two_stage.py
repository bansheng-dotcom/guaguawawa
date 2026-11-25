# -*- coding: utf-8 -*-
"""P1-2 两段式接线：探源卡是 bundle；探测结论不被第二段拆卡冲掉。"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import card_issue, report_clarify  # noqa: E402

INTENT = "区域市场的品类规模、份额与价格趋势"
SEM = """schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [全国, 省]
- id: category
  type: hierarchy
  levels: [大类, 子类]
- id: period
  type: time
  grain: year
grain_declarations:
- id: G_region_year
  dims: [region, year]
measures:
- id: gmv
  type: simple
  agg: sum
  expr: gmv
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: gmv
  denominator: gmv@total
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 测试口径
  affects: [gmv]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def _project() -> Path:
    base = Path(tempfile.mkdtemp(prefix="guagua_two_stage_"))
    assert report_clarify.write(INTENT, str(base))["ok"]
    assert report_clarify.confirm(str(base),
                                  user_said="用户确认：按这个意图做，先出格子再探源")["ok"]
    (base / "semantic_layer.yaml").write_text(SEM, encoding="utf-8")
    return base


def test_probe_card_is_bundle_with_probe_task_type():
    base = _project()
    assert card_issue.prepare(base)["ok"]
    res = card_issue.prepare_probe_cards(base)
    assert res["ok"]
    bundle = json.loads((base / "cards" / "r18" / "bundle.json")
                        .read_text(encoding="utf-8"))
    assert bundle["brief"]["task_type"] == "探源型"
    assert bundle["card"]["owner"] == "r18"
    layers = {m["id"].split(".")[0] for m in bundle["brief"]["must_answer"]}
    assert {"L0", "L1", "L2"} <= layers and "L3" not in layers


def test_second_pass_keeps_probe_state_until_semantics_change():
    base = _project()
    assert card_issue.prepare(base)["ok"]
    gp = base / "plan" / "grid.json"
    grid = json.loads(gp.read_text(encoding="utf-8"))
    cid = grid["cells"][0]["cell_id"]
    grid["cells"][0]["collectable"] = "partial"
    grid["cells"][0]["availability"] = "available"
    gp.write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")

    assert card_issue.prepare(base)["ok"]
    again = json.loads(gp.read_text(encoding="utf-8"))
    got = next(c for c in again["cells"] if c["cell_id"] == cid)
    assert got.get("collectable") == "partial"
    assert again.get("merged_fields", 0) > 0

    # 语义层一变 → 指纹变 → 重建，旧状态不再保留
    sem = (base / "semantic_layer.yaml").read_text(encoding="utf-8")
    (base / "semantic_layer.yaml").write_text(sem.replace("测试口径", "改口径"),
                                              encoding="utf-8")
    assert card_issue.prepare(base)["ok"]
    rebuilt = json.loads(gp.read_text(encoding="utf-8"))
    got2 = next(c for c in rebuilt["cells"] if c["cell_id"] == cid)
    assert "collectable" not in got2
