# -*- coding: utf-8 -*-
"""reportkit.extras —— 三个补强：affected / 分区缓存 / 分级阈值。

1. affected：改了一个数据源，精确列出受影响的章节、结论、批注。
2. 分区：按 month 缓存日度聚合片段，只重算变化的月份（backfill 用）。
3. 分级：B/C 级品类的观测阈值按证据级别下调，避免热力图永远红。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

# 章节 → 依赖的数据源 / 指标族
SECTION_DEPS = {
    "s2-1": {"sources": ["farm_daily"], "claims": ["C1", "C2"], "label": "2.1 全国日度"},
    "s2-2": {"sources": ["farm_weekly"], "claims": ["C3"], "label": "2.2 全国周度"},
    "s2-3": {"sources": ["nmg_monitor"], "claims": [], "label": "2.3 内蒙古零售"},
    "s2-4": {"sources": ["hh_fgw"], "claims": [], "label": "2.4 呼和浩特周度"},
    "s2-5": {"sources": ["futures"], "claims": ["C5"], "label": "2.5 期货主力"},
    "s2-6": {"sources": ["farm_daily", "nmg_monitor"], "claims": ["C4"], "label": "2.6 传导缺口"},
}

GRADE_CAP = {"A": 99, "B": 4, "C": 2}


def source_stats(conn) -> dict:
    out = {}
    for r in conn.execute("SELECT source, id, value FROM obs ORDER BY source, id"):
        out.setdefault(r["source"], []).append(f'{r["id"]}={r["value"]}')
    return {k: {"n": len(v), "hash": hashlib.sha256("|".join(v).encode()).hexdigest()[:12]}
            for k, v in out.items()}


def affected(conn, prev_stats: dict, anns: list[dict]) -> dict:
    cur = source_stats(conn)
    changed = [s for s in cur if prev_stats.get(s, {}).get("hash") != cur[s]["hash"]]
    sections = [{"id": sid, "label": meta["label"], "claims": meta["claims"]}
                for sid, meta in SECTION_DEPS.items() if set(meta["sources"]) & set(changed)]
    ann_hit = [a for a in anns if a["anchor"] in {s["id"] for s in sections}]
    return {"changed_sources": changed,
            "sections": sections,
            "claims": sorted({c for s in sections for c in s["claims"]}),
            "annotations": [{"anchor": a["anchor"], "status": a.get("status")} for a in ann_hit],
            "tables": len(sections)}


# ---------------------------------------------------------------- 分区缓存
def _period(d: str) -> str:
    return (d or "")[:7]


def _frag(conn, period: str) -> dict:
    frag = {}
    for r in conn.execute(
            "SELECT item, date, value FROM obs WHERE source='farm_daily' AND substr(date,1,7)=? ORDER BY item, date",
            (period,)):
        f = frag.setdefault(r["item"], {"n": 0, "sum": 0.0, "sumsq": 0.0, "min": 1e9, "max": -1e9,
                                        "first": None, "last": None, "up": 0, "down": 0, "_prev": None})
        v = r["value"]
        f["n"] += 1
        f["sum"] += v
        f["sumsq"] += v * v
        f["min"] = min(f["min"], v)
        f["max"] = max(f["max"], v)
        if f["first"] is None:
            f["first"] = v
        if f["_prev"] is not None:
            if v > f["_prev"]:
                f["up"] += 1
            elif v < f["_prev"]:
                f["down"] += 1
        f["_prev"] = v
        f["last"] = v
    for f in frag.values():
        f.pop("_prev", None)
    return frag


def cache_path(case_dir: Path) -> Path:
    return case_dir / "cache" / "daily_fragments.json"


def load_cache(case_dir: Path) -> dict:
    p = cache_path(case_dir)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"periods": {}}


def period_hashes(conn) -> dict:
    out = {}
    for r in conn.execute("SELECT DISTINCT substr(date,1,7) p FROM obs WHERE source='farm_daily' ORDER BY p"):
        rows = conn.execute(
            "SELECT id, value FROM obs WHERE source='farm_daily' AND substr(date,1,7)=? ORDER BY id",
            (r["p"],)).fetchall()
        payload = "|".join(f'{x["id"]}={x["value"]}' for x in rows)
        out[r["p"]] = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return out


def refresh_cache(conn, case_dir: Path) -> dict:
    """只重算 hash 变了的月份，返回 {recomputed, reused}。"""
    cache = load_cache(case_dir)
    cur = period_hashes(conn)
    periods = cache.setdefault("periods", {})
    recomputed, reused = [], []
    for p, h in cur.items():
        if periods.get(p, {}).get("hash") == h:
            reused.append(p)
            continue
        periods[p] = {"hash": h, "frag": _frag(conn, p)}
        recomputed.append(p)
    for p in list(periods):
        if p not in cur:
            periods.pop(p)
    p = cache_path(case_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"recomputed": sorted(recomputed), "reused": sorted(reused)}


def daily_from_cache(case_dir: Path, conn=None) -> dict:
    cache = load_cache(case_dir)
    merged: dict = {}
    for p in sorted(cache.get("periods", {})):
        for item, f in cache["periods"][p]["frag"].items():
            m = merged.setdefault(item, {"n": 0, "sum": 0.0, "sumsq": 0.0, "min": 1e9, "max": -1e9,
                                         "first": None, "last": None, "up": 0, "down": 0})
            if m["last"] is not None and f["first"] is not None:
                if f["first"] > m["last"]:
                    m["up"] += 1
                elif f["first"] < m["last"]:
                    m["down"] += 1
            m["n"] += f["n"]; m["sum"] += f["sum"]; m["sumsq"] += f["sumsq"]
            m["min"] = min(m["min"], f["min"]); m["max"] = max(m["max"], f["max"])
            if m["first"] is None:
                m["first"] = f["first"]
            m["last"] = f["last"]
            m["up"] += f["up"]; m["down"] += f["down"]
    out = {}
    for item, m in merged.items():
        mean = m["sum"] / m["n"]
        var = max(0.0, m["sumsq"] / m["n"] - mean * mean)
        out[item] = {"n": m["n"], "first": round(m["first"], 2), "last": round(m["last"], 2),
                     "change": round((m["last"] / m["first"] - 1) * 100, 2),
                     "min": round(m["min"], 2), "max": round(m["max"], 2), "mean": round(mean, 2),
                     "range": round((m["max"] - m["min"]) / mean * 100, 2),
                     "cv": round(var ** 0.5 / mean * 100, 2),
                     "up_days": m["up"], "down_days": m["down"]}
    if conn is not None:
        for item, d in out.items():
            rows = conn.execute("SELECT id FROM obs WHERE source='farm_daily' AND item=? ORDER BY date",
                                (item,)).fetchall()
            if rows:
                d["first_id"] = rows[0]["id"]
                d["last_id"] = rows[-1]["id"]
    return out


# ---------------------------------------------------------------- 分级阈值
def need_for(case: dict, cat: str, dim: dict) -> int:
    grade = (case.get("grades") or {}).get(cat, "A")
    return min(int(dim.get("min_obs", 1)), GRADE_CAP.get(grade, 99))
