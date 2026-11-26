# -*- coding: utf-8 -*-
"""core.claims.cell_claim —— 判断格 schema（DATA-LAYER-SOP v2.0 · S1）。

v1 的格子是一个数（cell.value），撑不起趋势/分布/对比。
v2 的格子是一个**判断 + 它依赖的数据集查询**：

    {
      "claim_id": "C-脚垫-价格带上移",
      "claim": "脚垫主流价格带在 2026 已上移到 59–99 元",
      "dataset": "DS-脚垫-品牌月度",
      "query": {"filters": {...}, "group_by": [...], "metrics": [...]},
      "min_rows": 24,
      "chart": {...},
      "causal_level": "A",
      "falsifier": "..."
    }

判断层只引用数据集 + 查询，不存数。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.data import dataset as _ds

SCHEMA = "dsh.cell_claim/v1"
CAUSAL_LEVELS = ("A", "I", "C")
# 一张图至少 3 个点才画（与 chart_units 的门槛一致）
MIN_POINTS = 3


def build(claim_id: str, claim: str, *, qid: str = "", dataset: str = "",
          query: Optional[Dict[str, Any]] = None, min_rows: int = 0,
          chart: Optional[Dict[str, Any]] = None, causal_level: str = "A",
          falsifier: str = "", boundary: str = "",
          replaces: Optional[List[str]] = None) -> Dict[str, Any]:
    q = dict(query or {})
    return {
        "schema": SCHEMA,
        "claim_id": str(claim_id),
        "qid": str(qid),
        "claim": str(claim),
        "dataset": str(dataset),
        "query": {
            "filters": dict(q.get("filters") or {}),
            "group_by": list(q.get("group_by") or []),
            "metrics": list(q.get("metrics") or []),
        },
        "min_rows": int(min_rows or 0),
        "chart": dict(chart or {}),
        "causal_level": str(causal_level),
        "falsifier": str(falsifier),
        "boundary": str(boundary),
        # v1 格子迁移而来时记下原 cell_id，方便回溯
        "replaces": list(replaces or []),
    }


def validate(cc: Dict[str, Any],
             datasets: Optional[Dict[str, Dict[str, Any]]] = None) -> List[str]:
    """判断格校验；传 datasets 时连「查询能不能在这张表上执行」一起查。"""
    errs: List[str] = []
    if not isinstance(cc, dict):
        return ["判断格必须是 dict"]
    if cc.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    if not str(cc.get("claim_id") or "").strip():
        errs.append("缺 claim_id")
    if not str(cc.get("claim") or "").strip():
        errs.append("缺 claim（判断文本）")
    if str(cc.get("causal_level") or "") not in CAUSAL_LEVELS:
        errs.append("causal_level 必须是 %s" % (CAUSAL_LEVELS,))
    if int(cc.get("min_rows") or 0) < MIN_POINTS:
        errs.append("min_rows 至少 %d（单点/两点不构成判断）" % MIN_POINTS)

    if datasets is None:
        return errs
    ds = datasets.get(str(cc.get("dataset") or ""))
    if not ds:
        errs.append("引用的数据集不在册: %r" % cc.get("dataset"))
        return errs
    ds_errs = _ds.validate(ds)
    if ds_errs:
        errs.append("数据集本身不合法: " + "；".join(ds_errs[:3]))
        return errs
    q = cc.get("query") or {}
    # filter 的键必须是表里的列
    bad_f = [k for k in (q.get("filters") or {}) if not _ds.has_column(ds, k)]
    if bad_f:
        errs.append("filters 用了表里没有的列: %s" % bad_f)
    # group_by 必须是维度列
    dims = set(_ds.columns_of(ds, "dimension"))
    bad_g = [k for k in (q.get("group_by") or []) if k not in dims]
    if bad_g:
        errs.append("group_by 必须是维度列: 非法 %s" % bad_g)
    # metrics 必须是度量列
    measures = set(_ds.columns_of(ds, "measure"))
    bad_m = [k for k in (q.get("metrics") or []) if k not in measures]
    if bad_m:
        errs.append("metrics 必须是度量列: 非法 %s" % bad_m)
    if not (q.get("metrics") or []):
        errs.append("query.metrics 为空（判断要算哪个度量）")
    # grain 校验（照 GROUND）：group_by 必须落在表声明的 grain 内
    grain_parts = {p.strip() for p in str(ds.get("grain") or "").split("×") if p.strip()}
    if grain_parts:
        unknown = [g for g in (q.get("group_by") or []) if g not in grain_parts]
        if unknown:
            errs.append("group_by 超出数据集 grain（%s）: %s"
                        % (ds.get("grain"), unknown))
    # 图形可行性：图需要的维度都要在 group_by 里
    chart = cc.get("chart") or {}
    for key in ("x", "series", "color"):
        v = chart.get(key)
        if v and v not in (q.get("group_by") or []):
            errs.append("chart.%s=%r 不在 group_by 里" % (key, v))
    return errs


def from_cell(cell: Dict[str, Any], dataset: str = "",
              claim: str = "", group_by: Optional[List[str]] = None,
              metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """把 v1 的标量格子迁移成 v2 判断格（尽力而为）。

    v1 格子没有表、没有查询，只能给出「这个判断大概要看哪张表的哪几列」；
    真实的 dataset/query 要由拆卡钻取段（S2）产出。
    """
    ent = str(cell.get("entity") or "")
    meas = str(cell.get("measure") or "")
    text = claim or "%s 的 %s（%s）" % (ent, meas, cell.get("period") or "")
    return build(
        claim_id="C-" + str(cell.get("cell_id") or ent),
        claim=text,
        qid=str(cell.get("qid") or ""),
        dataset=dataset,
        query={"filters": {str(cell.get("dim") or ""): ent} if ent else {},
               "group_by": list(group_by or []),
               "metrics": list(metrics or ([meas] if meas else []))},
        min_rows=MIN_POINTS,
        causal_level=str(cell.get("causal_level") or "A"),
        replaces=[str(cell.get("cell_id"))] if cell.get("cell_id") else [],
    )
