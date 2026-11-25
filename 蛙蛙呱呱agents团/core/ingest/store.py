# -*- coding: utf-8 -*-
"""Store 层：staging 落盘 + DQ 报告（可审计，P2-3 / P3-1）。

落点固定：`<PROJECT>/data/staging/<source>/<batch>/{rows.jsonl,_state.json,dq_report.json}`。
统一走 `core.paths.write_artifact`，写团内 / 写运行临时物直接抛 BoundaryError。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core import paths

UNIT_KEYS = ("unit", "单位")


def batch_id(when: Optional[float] = None) -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.localtime(when or time.time()))


def _col_stats(records: List[Dict[str, Any]], max_values: int = 12) -> Dict[str, Any]:
    n = len(records) or 1
    cols: List[str] = []
    for r in records[:200]:
        for k in r:
            if k not in cols:
                cols.append(str(k))
    out: Dict[str, Any] = {}
    for c in cols:
        vals = [str(r.get(c) if r.get(c) is not None else "").strip() for r in records]
        cnt: Dict[str, int] = {}
        for v in vals:
            cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        out[c] = {"empty_rate": round(sum(1 for v in vals if not v) / n, 4),
                  "distinct": len(cnt),
                  "top1_share": round((top[0][1] / n) if top else 0.0, 4),
                  "values": [k for k, _ in top[:max_values] if k]}
    return out


def _dup_rate(records: List[Dict[str, Any]]) -> float:
    if not records:
        return 0.0
    seen = set()
    dup = 0
    for r in records:
        key = json.dumps(r, ensure_ascii=False, sort_keys=True)
        if key in seen:
            dup += 1
        seen.add(key)
    return round(dup / len(records), 4)


def dq_report(records: List[Dict[str, Any]], rows_in: int = 0,
              dropped: Optional[Iterable[Dict[str, Any]]] = None,
              sources: Optional[Iterable[Dict[str, Any]]] = None,
              unit_unverified: int = 0) -> Dict[str, Any]:
    """一份可审计的 DQ 汇总：进了多少、出了多少、丢了什么、每列质量。"""
    drops = list(dropped or [])
    reasons: Dict[str, int] = {}
    for d in drops:
        k = str((d or {}).get("reason") or "unknown")
        reasons[k] = reasons.get(k, 0) + 1
    return {
        "schema": "dsh.dq/v1",
        "rows_in": rows_in or (len(records) + len(drops)),
        "rows_out": len(records),
        "dropped": {"total": len(drops), "reasons": reasons, "items": drops[:50]},
        "dup_rate": _dup_rate(records),
        "unit_unverified": int(unit_unverified),
        "columns": _col_stats(records),
        "sources": list(sources or []),
    }


def staging_dir(project_dir: str | Path, source_id: str,
                batch: str = "") -> Path:
    return (Path(project_dir) / "data" / "staging" / str(source_id)
            / (batch or batch_id()))


def write_staging(project_dir: str | Path, source_id: str,
                  records: List[Dict[str, Any]], batch: str = "",
                  dq: Optional[Dict[str, Any]] = None,
                  state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """写一批 staging；返回 {dir, rows, dq, state} 绝对路径。"""
    b = batch or batch_id()
    d = staging_dir(project_dir, source_id, b)
    rows_path = paths.write_artifact(d / "rows.jsonl", project=project_dir)
    with rows_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    dq_path = paths.write_artifact(d / "dq_report.json", project=project_dir)
    dq_path.write_text(json.dumps(dq or dq_report(records),
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    st = {"schema": "dsh.staging_state/v1", "source": str(source_id),
          "batch": b, "rows": len(records), "status": "complete",
          "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    st.update(state or {})
    state_path = paths.write_artifact(d / "_state.json", project=project_dir)
    state_path.write_text(json.dumps(st, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    return {"dir": str(d), "rows": str(rows_path), "dq": str(dq_path),
            "state": str(state_path), "count": len(records)}


def read_staging(project_dir: str | Path, source_id: str,
                 batch: str = "") -> List[Dict[str, Any]]:
    """读回 staging；batch 为空时取该源下最新一批。"""
    base = Path(project_dir) / "data" / "staging" / str(source_id)
    if not base.is_dir():
        return []
    if not batch:
        batches = sorted([p.name for p in base.iterdir() if p.is_dir()])
        if not batches:
            return []
        batch = batches[-1]
    p = base / batch / "rows.jsonl"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out
