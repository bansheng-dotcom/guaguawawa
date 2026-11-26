# -*- coding: utf-8 -*-
"""core.data.dataset —— 数据集 schema（DATA-LAYER-SOP v2.0 · S0）。

为什么要有它：
    拆卡层原来把「分析单元」和「数据单元」压成同一个东西（格子=一个数），
    想画「脚垫各品牌价格趋势」就得开 360 个格子，数据层因此被压成事实清单。

    数据集层是中间那层：**一张表 = 一行一个观测**，可以几千行，一次采集。
    判断层只引用数据集 + 一个查询，不直接存数。

契约借鉴 ODCS（表级，不是列级）：
    id / source / grain / time_grain / columns / rows_expected / quality / sla

用法：
    from core.data import dataset
    ds = dataset.build(...)
    errs = dataset.validate(ds)          # 空 = 合法
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.dataset/v1"
TIME_GRAINS = ("year", "quarter", "month", "week", "day")
SEMANTICS = ("dimension", "measure")
SOURCE_KINDS = ("平台榜单", "行业报告", "统计局", "第三方数据",
                "店铺后台", "调研", "内部系统")


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(ds: Dict[str, Any]) -> str:
    """数据集指纹：只算口径相关字段（不含行数/质量，便于同口径跨期复用）。"""
    core = {k: ds.get(k) for k in ("id", "grain", "time_grain", "columns")}
    return "sha256:" + hashlib.sha256(canon(core).encode("utf-8")).hexdigest()


def build(dataset_id: str, *, title: str = "", source: Optional[Dict[str, Any]] = None,
          grain: str = "", time_grain: str = "year",
          columns: Optional[List[Dict[str, Any]]] = None,
          rows_expected: int = 0,
          quality: Optional[Dict[str, Any]] = None,
          sla: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """造一份数据集声明。"""
    cols = []
    for c in columns or []:
        col = {
            "name": str(c.get("name") or ""),
            "type": str(c.get("type") or "string"),
            "semantic": str(c.get("semantic") or "dimension"),
        }
        if c.get("unit"):
            col["unit"] = str(c["unit"])
        if c.get("agg"):
            col["agg"] = str(c["agg"])      # sum / mean / count（图从表现算时用）
        cols.append(col)
    return {
        "schema": SCHEMA,
        "id": str(dataset_id),
        "title": str(title or dataset_id),
        "source": dict(source or {}),
        "grain": str(grain),
        "time_grain": str(time_grain),
        "columns": cols,
        "rows_expected": int(rows_expected or 0),
        "quality": dict(quality or {}),
        "sla": dict(sla or {}),
    }


def validate(ds: Dict[str, Any]) -> List[str]:
    """表级校验；空列表 = 合法。"""
    errs: List[str] = []
    if not isinstance(ds, dict):
        return ["数据集必须是 dict"]
    if ds.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    if not ds.get("id"):
        errs.append("缺 id")
    # grain 是这张表最重要的一条：不声明 grain 就不知道一行是什么
    if not str(ds.get("grain") or "").strip():
        errs.append("缺 grain（一行是什么）")
    if str(ds.get("time_grain") or "") not in TIME_GRAINS:
        errs.append("time_grain 必须是 %s" % (TIME_GRAINS,))
    src = ds.get("source") or {}
    if not src.get("kind"):
        errs.append("缺 source.kind")
    elif str(src["kind"]) not in SOURCE_KINDS:
        errs.append("source.kind 非法: %r（可用 %s）" % (src["kind"], SOURCE_KINDS))
    cols = ds.get("columns") or []
    if not cols:
        errs.append("columns 为空")
    names = set()
    for i, c in enumerate(cols):
        n = str(c.get("name") or "")
        if not n:
            errs.append("columns[%d] 缺 name" % i)
            continue
        if n in names:
            errs.append("columns 重名: %s" % n)
        names.add(n)
        if c.get("semantic") not in SEMANTICS:
            errs.append("columns[%s].semantic 非法: %r" % (n, c.get("semantic")))
    if int(ds.get("rows_expected") or 0) <= 0:
        errs.append("rows_expected 必须是正整数（判断层要靠它算 min_rows）")
    return errs


def columns_of(ds: Dict[str, Any], semantic: str) -> List[str]:
    return [str(c.get("name")) for c in ds.get("columns") or []
            if c.get("semantic") == semantic]


def has_column(ds: Dict[str, Any], name: str) -> bool:
    return any(str(c.get("name")) == str(name) for c in ds.get("columns") or [])
