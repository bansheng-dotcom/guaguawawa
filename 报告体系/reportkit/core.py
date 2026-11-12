# -*- coding: utf-8 -*-
"""reportkit.core —— 观测库 / 指标 / 快照 / 审计 / 差异

设计约束（对应 SOP）：
1. 所有数字来自 obs 表，报告里不出现手写数字；
2. 每次 build 记录 used_obs，用于算保留率；
3. seal 用内容哈希冻结，改数据不影响已 sealed 版本。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS obs(
  id TEXT PRIMARY KEY, source TEXT, market TEXT, item TEXT, date TEXT,
  value REAL, unit TEXT, spec TEXT, grade TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS claim(
  id TEXT PRIMARY KEY, section TEXT, text TEXT, kind TEXT, obs_ids TEXT
);
CREATE TABLE IF NOT EXISTS conflict(
  id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, a_source TEXT, a_value REAL,
  b_source TEXT, b_value REAL, delta_pct REAL, verdict TEXT
);
CREATE TABLE IF NOT EXISTS failed(
  id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, tried TEXT, reason TEXT, next_action TEXT
);
CREATE TABLE IF NOT EXISTS quarantine(
  id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT, reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_obs_item ON obs(item);
CREATE INDEX IF NOT EXISTS idx_obs_date ON obs(date);
"""


def db(case_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(case_dir / "store.sqlite")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def oid(source, market, item, date, spec) -> str:
    return f"{source}|{market}|{item}|{date}|{spec}"


def upsert_obs(conn, rows: list[dict]) -> tuple[int, int]:
    ok = bad = 0
    for r in rows:
        need = ("source", "market", "item", "date", "value", "unit", "spec", "grade")
        if any(r.get(k) in (None, "") for k in need):
            conn.execute("INSERT INTO quarantine(payload, reason) VALUES(?,?)",
                         (json.dumps(r, ensure_ascii=False), "missing required field"))
            bad += 1
            continue
        conn.execute(
            "INSERT INTO obs(id,source,market,item,date,value,unit,spec,grade,note) "
            "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value",
            (oid(r["source"], r["market"], r["item"], r["date"], r["spec"]),
             r["source"], r["market"], r["item"], r["date"], float(r["value"]),
             r["unit"], r["spec"], r["grade"], r.get("note", "")))
        ok += 1
    conn.commit()
    return ok, bad


def add_csv(conn, path: Path, source: str, market: str, unit: str, grade: str,
            spec: str, items: list[str], date_col: str = "date") -> tuple[int, int]:
    rows = []
    with path.open(encoding="utf-8-sig") as fh:
        for rec in csv.DictReader(fh):
            d = (rec.get(date_col) or "")[:10]
            for it in items:
                v = rec.get(it)
                if v in (None, ""):
                    continue
                rows.append({"source": source, "market": market, "item": it, "date": d,
                             "value": v, "unit": unit, "spec": spec, "grade": grade})
    return upsert_obs(conn, rows)


def query(conn, sql: str, args=()) -> list[sqlite3.Row]:
    return conn.execute(sql, args).fetchall()


# ---------------------------------------------------------------- metrics
def compute_metrics(conn) -> dict:
    m: dict = {"daily": {}, "weekly": {}, "retail": {}, "city": {}, "futures": {}}

    for it in [r["item"] for r in query(conn, "SELECT DISTINCT item FROM obs WHERE source='farm_daily' ORDER BY item")]:
        pts = query(conn, "SELECT date,value FROM obs WHERE source='farm_daily' AND item=? ORDER BY date", (it,))
        if not pts:
            continue
        vals = [p["value"] for p in pts]
        first, last = vals[0], vals[-1]
        mean = sum(vals) / len(vals)
        sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        m["daily"][it] = {
            "n": len(vals), "first": round(first, 2), "last": round(last, 2),
            "change": round((last / first - 1) * 100, 2),
            "min": round(min(vals), 2), "max": round(max(vals), 2), "mean": round(mean, 2),
            "range": round((max(vals) - min(vals)) / mean * 100, 2),
            "cv": round(sd / mean * 100, 2),
            "first_id": oid("farm_daily", "全国", it, pts[0]["date"], "批发均价"),
            "last_id": oid("farm_daily", "全国", it, pts[-1]["date"], "批发均价"),
            "up_days": sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1]),
            "down_days": sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1]),
        }

    for it in [r["item"] for r in query(conn, "SELECT DISTINCT item FROM obs WHERE source='farm_weekly' ORDER BY item")]:
        cur = query(conn, "SELECT date,value FROM obs WHERE source='farm_weekly' AND item=? AND spec='本周' ORDER BY date", (it,))
        yoy = query(conn, "SELECT value FROM obs WHERE source='farm_weekly' AND item=? AND spec='同比' ORDER BY date DESC LIMIT 1", (it,))
        if cur:
            m["weekly"][it] = {"first": round(cur[0]["value"], 2), "last": round(cur[-1]["value"], 2),
                               "change": round((cur[-1]["value"] / cur[0]["value"] - 1) * 100, 2),
                               "yoy": round(yoy[0]["value"], 1) if yoy else None}

    for it in [r["item"] for r in query(conn, "SELECT DISTINCT item FROM obs WHERE source='nmg_monitor' ORDER BY item")]:
        pts = query(conn, "SELECT date,value FROM obs WHERE source='nmg_monitor' AND item=? ORDER BY date", (it,))
        if len(pts) >= 2:
            m["retail"][it] = {"first": pts[0]["value"], "last": pts[-1]["value"],
                               "change": round((pts[-1]["value"] / pts[0]["value"] - 1) * 100, 2)}

    for row in query(conn, "SELECT market,item,date,value FROM obs WHERE source='hh_fgw' ORDER BY date"):
        m["city"].setdefault(row["item"], {})[row["date"]] = row["value"]

    for it in [r["item"] for r in query(conn, "SELECT DISTINCT item FROM obs WHERE source='futures' AND spec='close' ORDER BY item")]:
        pts = query(conn, "SELECT date,value FROM obs WHERE source='futures' AND item=? AND spec='close' ORDER BY date", (it,))
        if pts:
            m["futures"][it] = {"first": pts[0]["value"], "last": pts[-1]["value"],
                                "change": round((pts[-1]["value"] / pts[0]["value"] - 1) * 100, 2)}

    # 传导缺口：全国鸡蛋 vs 内蒙鸡蛋
    nat = m["daily"].get("鸡蛋", {}).get("change")
    nm = m["retail"].get("鸡蛋", {}).get("change")
    if nat is not None and nm is not None:
        m["gap_egg"] = round(nm - nat, 2)
    return m


# ---------------------------------------------------------------- snapshot
def snapshot(conn, m: dict) -> dict:
    rows = query(conn, "SELECT COUNT(*) c FROM obs")[0]["c"]
    payload = json.dumps({"rows": rows, "metrics": m}, ensure_ascii=False, sort_keys=True)
    return {"id": "snap-" + hashlib.sha256(payload.encode()).hexdigest()[:12],
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rows": rows,
            "metrics_hash": hashlib.sha256(payload.encode()).hexdigest()[:16]}


# ---------------------------------------------------------------- audit
def audit(conn, case: dict, used_ids: set[str], gaps: list[dict]) -> dict:
    total = query(conn, "SELECT COUNT(*) c FROM obs")[0]["c"]
    used = len(used_ids)
    claims = query(conn, "SELECT id,obs_ids FROM claim")
    traced = sum(1 for c in claims if (c["obs_ids"] or "").strip())
    cells = []
    aliases = case.get("aliases") or {}
    for cat in case["categories"]:
        items = [cat] + list(aliases.get(cat, []))
        ph = ",".join("?" * len(items))
        for dim in case["dimensions"]:
            if dim["id"] == "regional":
                n = query(conn, f"SELECT COUNT(*) c FROM obs WHERE item IN ({ph}) AND market IN ('呼和浩特','乌兰察布','全区')", items)[0]["c"]
            elif dim["id"] == "upstream":
                n = query(conn, f"SELECT COUNT(*) c FROM obs WHERE item IN ({ph}) AND source IN ('origin','futures')", items)[0]["c"]
            elif dim["id"] == "spec_risk":
                n = query(conn, f"SELECT COUNT(*) c FROM obs WHERE item IN ({ph}) AND spec IN ('零售采价','批发均价')", items)[0]["c"]
            else:
                n = query(conn, f"SELECT COUNT(*) c FROM obs WHERE item IN ({ph})", items)[0]["c"]
            from reportkit.extras import need_for
            need = need_for(case, cat, dim)
            cells.append({"cat": cat, "dim": dim["id"], "name": dim["name"],
                          "have": n, "need": need,
                          "status": "ok" if n >= need else ("partial" if n > 0 else "empty")})
    ok = sum(1 for c in cells if c["status"] == "ok")
    return {
        "obs_total": total,
        "obs_used": used,
        "retention": round(used / total, 4) if total else 0,
        "trace_rate": round(traced / len(claims), 4) if claims else 0,
        "discard": round((total - used) / total, 4) if total else 0,
        "cells": cells,
        "coverage": round(ok / len(cells), 4) if cells else 0,
        "gaps": gaps,
        "verdict": "PASS" if (used / total >= 0.95 and traced == len(claims) and ok / max(1, len(cells)) >= 0.6) else "PASS_WITH_GAPS",
    }


# ---------------------------------------------------------------- diff
def diff(prev: dict | None, cur: dict) -> dict:
    if not prev:
        return {"new": True, "changes": []}
    out = []
    for key, cur_v in cur.get("metrics", {}).get("daily", {}).items():
        prev_v = prev.get("metrics", {}).get("daily", {}).get(key)
        if prev_v and abs(prev_v["change"] - cur_v["change"]) >= 0.01:
            out.append({"kind": "metric", "key": f"daily.{key}.change",
                        "from": prev_v["change"], "to": cur_v["change"]})
    for key, cur_v in cur.get("metrics", {}).get("weekly", {}).items():
        prev_v = prev.get("metrics", {}).get("weekly", {}).get(key)
        if prev_v and cur_v.get("yoy") is not None and prev_v.get("yoy") is not None \
                and abs(cur_v["yoy"] - prev_v["yoy"]) >= 0.1:
            out.append({"kind": "metric", "key": f"weekly.{key}.yoy",
                        "from": prev_v["yoy"], "to": cur_v["yoy"]})
    rows_delta = cur["snapshot"]["rows"] - prev["snapshot"]["rows"]
    return {"new": False, "rows_delta": rows_delta, "changes": out,
            "from": prev["build_id"], "to": cur["build_id"]}

# ---------------------------------------------------------------- 批注层
ANCHORS = {
    "s2-1": lambda m: m.get("daily", {}),
    "s2-2": lambda m: m.get("weekly", {}),
    "s2-3": lambda m: m.get("retail", {}),
    "s2-4": lambda m: m.get("city", {}),
    "s2-5": lambda m: m.get("futures", {}),
    "s2-6": lambda m: {k: v for k, v in m.items() if k == "gap_egg"} | {"egg": m.get("retail", {}).get("鸡蛋")},
}


def anchor_hash(m: dict, anchor: str) -> str:
    sel = ANCHORS.get(anchor)
    payload = json.dumps(sel(m) if sel else {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


def parse_annotations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    blocks, cur = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            if cur:
                blocks.append(cur)
            cur = {"anchor": line[3:].strip(), "lines": []}
        elif cur is not None:
            cur["lines"].append(line)
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks:
        body = "\n".join(b["lines"])
        m = re.search(r"<!--\s*hash:\s*([0-9a-f]{8})\s*-->", body)
        body = re.sub(r"<!--\s*hash:\s*[0-9a-f]{8}\s*-->", "", body).strip()
        out.append({"anchor": b["anchor"], "text": body, "hash": m.group(1) if m else None})
    return out