# -*- coding: utf-8 -*-
"""core.synthesis —— 论点（theses）、查询（query）与写作（writer）。

SOP v5：
    面板 → 论点（claim + support_rows + contradiction + decision）
         → SCQA + 五块正文
         → 图 = 查询结果的编码
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _rows_of(rows: List[Dict[str, Any]], metric_id: str) -> List[Dict[str, Any]]:
    return [r for r in rows if str(r.get("metric_id")) == metric_id]


def _num(r: Dict[str, Any]) -> float:
    """展示用数值：优先原值（带原单位），value_base 只用于跨单位比较。"""
    v = r.get("value")
    if v not in (None, ""):
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    try:
        return float(r.get("value_base") or 0)
    except (TypeError, ValueError):
        return 0.0


def theses(rows: List[Dict[str, Any]],
           panels: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """把行聚成论点：一个指标一条，选极值做 claim，差异做反例，排序按效应量。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows or []:
        groups.setdefault(str(r.get("metric_id")), []).append(r)
    out: List[Dict[str, Any]] = []
    for i, (mid, rs) in enumerate(groups.items(), 1):
        if len(rs) < 3:
            continue
        vals = sorted(rs, key=_num)
        lo, hi = vals[0], vals[-1]
        lo_v, hi_v = _num(lo), _num(hi)
        unit = str(hi.get("unit") or "")
        ratio = (hi_v / lo_v) if lo_v else 0
        claim = (f"{hi.get('entity')} {hi_v:g}{unit}，{lo.get('entity')} {lo_v:g}{unit}，"
                 f"相差 {ratio:.1f} 倍" if ratio else
                 f"{hi.get('entity')} {hi_v:g}{unit}")
        contradiction = ("主体间差距不足 1.2 倍，差异不显著，需换维度或补期次"
                         if 0 < ratio < 1.2 else
                         "若把口径换成平台/样本，排序可能反转；需一手核对")
        out.append({
            "id": f"T{i}", "metric_id": mid,
            "metric_name": str(hi.get("metric_name") or ""),
            "claim": claim,
            "support_rows": [r.get("row_id") for r in rs],
            "refs": [r.get("number_id") for r in rs if r.get("number_id")],
            "contradiction": contradiction,
            "decision": f"优先在高值主体投入；低值主体先验证 {lo.get('entity')} 的结构",
            "gaps": [],
            "effect": round(ratio, 3), "n": len(rs),
        })
    out.sort(key=lambda t: (-t["effect"], -t["n"]))
    for i, t in enumerate(out, 1):
        t["id"] = f"T{i}"
    return out


def query(rows: List[Dict[str, Any]], metric_id: str) -> Optional[Dict[str, Any]]:
    """面板查询 → 图规格。趋势 ≥3 期用线，否则排序用条。"""
    rs = _rows_of(rows, metric_id)
    if len(rs) < 2:
        return None
    periods = {str(r.get("period")) for r in rs}
    unit = str(rs[0].get("unit") or "")
    refs = [r.get("number_id") for r in rs if r.get("number_id")]
    if len(periods) >= 3:
        pts = {}
        for r in rs:
            pts.setdefault(str(r.get("period")), []).append(_num(r))
        points = [{"label": p, "value": round(sum(v) / len(v), 4)}
                  for p, v in sorted(pts.items())]
        return {"type": "line", "title": "", "unit_meta": unit,
                "points": points, "refs": refs}
    items = [{"label": str(r.get("entity")), "value": _num(r)} for r in rs]
    items.sort(key=lambda x: -x["value"])
    typ = "hbar" if len(items) >= 4 else "vbar"
    return {"type": typ, "title": "", "unit_meta": unit,
            "items": items, "refs": refs}


def sections(theses_list: List[Dict[str, Any]],
             rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """论点 → SCQA + 五块（现有渲染器认识的 sections）。"""
    out = []
    for t in theses_list:
        rs = [r for r in rows if r.get("row_id") in (t.get("support_rows") or [])]
        from core.charts import chart_query
        ch = (chart_query.build(rows, t["metric_id"], title=t.get("metric_name") or t["claim"])
              or query(rows, t["metric_id"]) or {})
        if ch:
            ch["source"] = "面板查询（raw）"
        refs = t.get("refs") or []
        facts = "；".join(f"{r.get('entity')} {r.get('period')} {_num(r):g}{r.get('unit')}"
                         for r in rs[:4])
        sec = {
            "title": t["claim"],
            "question": f"这一节回答：{t['metric_name']} 的主体差异",
            "refs": refs,
            "verdict": t["claim"],
            "fact": facts,
            "evidence": facts,
            "mechanism": "同一指标在主体间拉开差距，通常来自供给、渠道、价格三类约束。",
            "alternative": t["contradiction"],
            "signal": f"关注 {t['metric_name']} 的排序与差值是否扩大。",
            "discriminator": f"若 {t['metric_name']} 的排序反转，本节作废。",
            "implication": t["decision"],
            "action": t["decision"],
            "stop": "若新一期数据把排序反转，本节作废。",
            "reading": [
                {"strong": "事实　", "text": f"{facts}。", "refs": refs},
                {"strong": "机理　", "text": "同一指标在主体间拉开差距，通常来自供给、渠道、价格三类约束；需一手核对其中一条。", "refs": refs},
                {"strong": "反例　", "text": t["contradiction"], "refs": refs},
                {"strong": "信号　", "text": f"关注 {t['metric_name']} 的排序与差值是否扩大。", "refs": refs},
                {"strong": "所以　", "text": t["decision"], "refs": refs},
            ],
            "boundary": "口径见来源表；estimated 行需按公式回算。",
            "falsifier": "若新一期数据把排序反转，本节作废。",
            "chart": ch or None,
        }
        sec["prose_spec"] = {k: sec.get(k) for k in
                             ("fact", "evidence", "mechanism", "alternative",
                              "signal", "implication", "action", "stop", "boundary")}
        out.append(sec)
    return out
