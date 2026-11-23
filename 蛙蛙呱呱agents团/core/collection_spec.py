# -*- coding: utf-8 -*-
"""core.collection_spec —— 采集规格（SYSTEM-UPGRADE-SOP v3.1 · S3）。

一份采集规格 = 一个源 + 一组 rollup + 一组 claim。
**业务词只出现在 query 参数里**，其余全是结构声明。

    id: auto_interior
    source: manual_csv
    query: {path: data/staging/x.csv}
    rollups:
      - id: brand_month
        grain: [brand, month]
        derive: {brand: "token:title:0", month: "substr:snapshot_date:0:7"}
        measures: {asp: {agg: mean, expr: price}}
    claims:
      - id: brand_gap
        dataset: brand_month
        query: {group_by: [brand], metrics: [asp]}
        min_rows: 5

用法：
    from core import collection_spec as cs
    spec = cs.load("configs/collections/auto_interior.yaml")
    errs = cs.validate(spec)        # 空 = 合法
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core import grain as g
from core import source_profile as sp

SCHEMA = "dsh.collection_spec/v1"
ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS_DIR = ROOT / "configs" / "collections"


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def load(spec_id: str, extra_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    p = Path(spec_id)
    if p.is_file():
        return _yaml(p)
    for d in ([COLLECTIONS_DIR] + [Path(x) for x in (extra_dirs or [])]):
        cand = Path(d) / (str(spec_id) + ".yaml")
        if cand.is_file():
            return _yaml(cand)
    return {}


def validate(spec: Dict[str, Any],
             source: Optional[Dict[str, Any]] = None) -> List[str]:
    """采集规格校验；空 = 合法。"""
    errs: List[str] = []
    if not isinstance(spec, dict):
        return ["采集规格必须是 dict"]
    if spec.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    if not spec.get("id"):
        errs.append("缺 id")
    src = source if source is not None else sp.load(str(spec.get("source") or ""))
    if not src:
        errs.append("源画像不存在: %r" % spec.get("source"))
        return errs
    for e in sp.validate(src):
        errs.append("[source] " + e)
    q = spec.get("query") or {}
    if not q:
        errs.append("缺 query（怎么采）")

    rollups = spec.get("rollups") or []
    if not rollups:
        errs.append("没有 rollup（原子粒度怎么滚到分析粒度）")
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in rollups:
        rid = str(r.get("id") or "")
        if not rid:
            errs.append("rollup 缺 id")
            continue
        if rid in by_id:
            errs.append("rollup id 重复: %s" % rid)
        by_id[rid] = r
        for e in g.check(src, r):
            errs.append("[rollup %s] %s" % (rid, e))

    claims = spec.get("claims") or []
    if not claims:
        errs.append("没有 claim（判断引用哪张 mart）")
    for c in claims:
        cid = str(c.get("id") or "")
        did = str(c.get("dataset") or "")
        if did not in by_id:
            errs.append("[claim %s] dataset 不在 rollups 里: %r" % (cid, did))
            continue
        for e in g.chain_check(src, by_id[did], c):
            errs.append("[claim %s] %s" % (cid, e))
        if int(c.get("min_rows") or 0) < 3:
            errs.append("[claim %s] min_rows 至少 3" % cid)
    return errs


def preview(spec: Dict[str, Any], n: int = 20,
            project_dir: str = "",
            source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """先看效果再定稿：跑采集 + 第一个 rollup，返回前 n 行。

    DERIVATION-SOP 第 5 步：`token:title:0` 这类规则对不对，看这 20 行就知道。
    """
    from core import collectors as _c
    from core import grain as _g
    from core import source_profile as _sp

    src = (source if source is not None
           else _sp.load(str(spec.get("source") or "")))
    col = _c.base.get(str(src.get("kind") or "")) if src else None
    if not col:
        return {"ok": False, "why": "没有可用采集器: %r" % src.get("kind")}
    try:
        staging = col().fetch(spec, project_dir=project_dir)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "why": "采集失败: %s" % exc}
    rollups = spec.get("rollups") or []
    if not rollups:
        return {"ok": False, "why": "没有 rollup"}
    r0 = rollups[0]
    rows = _g.rollup_rows(staging, r0)
    return {
        "ok": True,
        "staging_rows": len(staging),
        "rollup": str(r0.get("id") or ""),
        "grain": _g.analysis_of(r0),
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows[:max(1, int(n))],
        "total_rows": len(rows),
    }


def quality(spec: Dict[str, Any], project_dir: str = "",
            source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """量化 derive 质量：每个维度的空值率 / 不同值数 / top1 占比。

    DERIVATION-SOP 的硬指标：`empty_rate < 0.10`、`distinct >= 2`。
    """
    from core import collectors as _c
    from core import grain as _g
    from core import source_profile as _sp

    src = (source if source is not None
           else _sp.load(str(spec.get("source") or "")))
    col = _c.base.get(str(src.get("kind") or "")) if src else None
    if not col:
        return {"ok": False, "why": "没有可用采集器"}
    try:
        staging = col().fetch(spec, project_dir=project_dir)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "why": "采集失败: %s" % exc}

    out: Dict[str, Any] = {}
    bad: List[str] = []
    for r in spec.get("rollups") or []:
        rows = _g.rollup_rows(staging, r)
        for dim in _g.analysis_of(r):
            vals = [str(x.get(dim) or "").strip() for x in rows]
            n = len(vals) or 1
            empty = sum(1 for v in vals if not v) / n
            from collections import Counter
            cnt = Counter(v for v in vals if v)
            distinct = len(cnt)
            top1 = (max(cnt.values()) / n) if cnt else 0.0
            key = "%s.%s" % (r.get("id"), dim)
            rec = {"empty_rate": round(empty, 3),
                   "distinct": distinct,
                   "top1_share": round(top1, 3),
                   "sample": [v for v in vals[:5]]}
            out[key] = rec
            if empty > 0.10:
                bad.append("%s: 空值率 %.0f%% > 10%%" % (key, empty * 100))
            if distinct < 2:
                bad.append("%s: 只有 %d 个不同值" % (key, distinct))
    return {"ok": not bad, "dims": out, "problems": bad,
            "staging_rows": len(staging)}


def run(spec: Dict[str, Any], project_dir: str = "") -> Dict[str, Any]:
    """执行采集链：collector → staging → rollup → mart。"""
    from core import collectors as _c

    src = sp.load(str(spec.get("source") or ""))
    col = _c.base.get(str(src.get("kind") or "")) if src else None
    if not col:
        return {"ok": False, "stage": "collector",
                "error": "没有可用采集器: %r" % src.get("kind")}
    inst = col()
    try:
        staging = inst.fetch(spec, project_dir=project_dir)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "fetch", "error": str(exc)}

    marts: Dict[str, List[Dict[str, Any]]] = {}
    for r in spec.get("rollups") or []:
        marts[str(r.get("id"))] = g.rollup_rows(staging, r)
    return {
        "ok": True,
        "source": src.get("id"),
        "atomic_grain": g.atomic_of(src),
        "staging_rows": len(staging),
        "marts": {k: {"rows": len(v), "grain": v[0].keys() if v else []}
                  for k, v in marts.items()},
        "mart_rows": marts,
    }
