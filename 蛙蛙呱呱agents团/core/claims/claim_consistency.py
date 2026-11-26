# -*- coding: utf-8 -*-
"""core/claim_consistency —— 交叉质询：把「同一个数两个说法」逼出来（v12）。

这是 R04 蛙挑刺在报告产线里的可执行版本。它不评价文笔，只抓四类硬伤：

    C1 同一指标两个不同值（口径冲突没交代）  ← 本次调研真实发生：
       全国预制菜 2024 年，艾媒 4850 亿元，网经社 6831.6 亿元，差 40.9%；
       B 端占比，同一报告写 80%，但 4600/6831.6 只算得 67%。
       这种冲突**不是错误**，沉默才是错误。要么在 claims.conflicts 里解释口径差，
       要么不许进报告。
    C2 结论引用了 D 级来源（摘要页/无法取全文）——只能当线索，不能当结论。
    C3 头条（standfirst）里的数字没有任何 A/B 级来源支撑。
    C4 声明「已查」但 boundaries 为空——没写边界通常意味着没查缺口。

用法：
    python -m core.claims.claim_consistency claims.json
    from core.claims.claim_consistency import check; check(claims)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.claim_consistency/v1"
TOL = 0.02          # 相对差 2% 以内视为同一个值


def _norm_name(s: str) -> str:
    return re.sub(r"[\s_（）()：:·]", "", str(s or ""))


def _values(claims: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """按指标名归并数字（数字来自 numbers，兼容 derived 不计）。"""
    out: Dict[str, List[Dict[str, Any]]] = {}
    for n in claims.get("numbers") or []:
        try:
            v = float(n.get("value"))
        except (TypeError, ValueError):
            continue
        key = _norm_name(n.get("name") or "")
        if not key:
            continue
        out.setdefault(key, []).append({
            "id": n.get("id"), "value": v,
            "source": str(n.get("source_file") or ""),
            "period": str(n.get("period") or ""),
        })
    return out


def _close(a: float, b: float) -> bool:
    if b == 0:
        return abs(a) < 1e-9
    return abs(a - b) / abs(b) <= TOL


def check(claims: Dict[str, Any]) -> Dict[str, Any]:
    vals = _values(claims)
    declared = {_norm_name(c.get("name") or ""): c
                for c in (claims.get("conflicts") or [])}
    grade_of = {str(s.get("file")): str(s.get("grade") or "C").upper()
                for s in (claims.get("sources") or [])}

    conflicts: List[Dict[str, Any]] = []
    unexplained: List[Dict[str, Any]] = []
    for name, items in vals.items():
        # 同一指标、同一期次，才构成冲突；不同期次是两期数据，不算
        by_period: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            by_period.setdefault(it["period"], []).append(it)
        for period, group in by_period.items():
            if len(group) < 2:
                continue
            base = group[0]["value"]
            if all(_close(g["value"], base) for g in group[1:]):
                continue
            rec = {"name": name, "period": period,
                   "values": [{"id": g["id"], "value": g["value"],
                               "source": g["source"],
                               "grade": grade_of.get(g["source"], "?")}
                              for g in group]}
            d = declared.get(name)
            if d and str(d.get("reason") or "").strip():
                rec["resolved_by"] = str(d.get("reason"))
                conflicts.append(rec)
            else:
                rec["why_bad"] = ("同一指标同期出现不同值，且没有说明口径差；"
                                  "读者会认为其中一个是错的")
                unexplained.append(rec)

    # C2：结论只挂 D 级来源
    d_only: List[Dict[str, Any]] = []
    for n in claims.get("numbers") or []:
        src = str(n.get("source_file") or "")
        if grade_of.get(src) == "D":
            d_only.append({"id": n.get("id"), "name": n.get("name"),
                           "source": src})

    # C3：头条数字没有 A/B 级支撑
    stand = str(claims.get("standfirst") or "")
    ab_ids = {str(n.get("id")) for n in (claims.get("numbers") or [])
              if grade_of.get(str(n.get("source_file") or "")) in ("A", "B", "S")}
    nums_in_stand = set(re.findall(r"\d+(?:\.\d+)?", stand))
    headline_unbacked: List[str] = []
    if stand and nums_in_stand:
        cited = {str(r) for s in (claims.get("sections") or [])
                 for r in (s.get("refs") or [])}
        if not (cited & ab_ids):
            headline_unbacked.append("头条里的数字没有引用任何 A/B 级来源")

    # C4：没写边界
    bounds = [b for b in (claims.get("boundaries") or []) if str(b).strip()]

    issues = {
        "C1_unexplained_conflict": len(unexplained),
        "C2_d_only_numbers": len(d_only),
        "C3_headline_unbacked": len(headline_unbacked),
        "C4_no_boundary": 0 if bounds else 1,
    }
    blocking = (issues["C1_unexplained_conflict"] > 0
                or issues["C2_d_only_numbers"] > 0
                or issues["C3_headline_unbacked"] > 0
                or issues["C4_no_boundary"] > 0)
    return {
        "schema": SCHEMA,
        "ok": not blocking,
        "issues": issues,
        "conflicts_resolved": conflicts,
        "conflicts_unexplained": unexplained,
        "d_only_numbers": d_only,
        "headline_unbacked": headline_unbacked,
        "note": ("C1 不是「有冲突就错」：同一指标不同口径是常态，"
                 "在 claims.conflicts 里写清 reason 即放行；沉默才是错。"),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="claim_consistency",
                                 description="交叉质询：口径冲突与来源等级")
    ap.add_argument("claims")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    claims = json.loads(Path(a.claims).read_text(encoding="utf-8-sig"))
    res = check(claims)
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
