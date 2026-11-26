# -*- coding: utf-8 -*-
"""core.claims_v4 —— 数据→图→文 映射层（v4）。

链路：claim → slice → encoding（图）→ findings（发现）→ 五块渲染。
不限定主判断数量：由 tier（main/support）决定，support 进附录。
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

VALID_FINDINGS = ("extreme", "gap", "trend", "concentration", "crossover", "outlier")


def _vals(rows: List[Dict[str, Any]]) -> List[float]:
    out = []
    for r in rows:
        try:
            out.append(float(r.get("value")))
        except (TypeError, ValueError):
            continue
    return out


def detect(rows: List[Dict[str, Any]], unit: str = "") -> List[Dict[str, Any]]:
    """在 slice 上跑检测器：文字从发现来，不从灵感来。"""
    vals = _vals(rows)
    if len(vals) < 2:
        return []
    labels = [str(r.get("label") or "") for r in rows]
    hi, lo = max(vals), min(vals)
    hi_i, lo_i = vals.index(hi), vals.index(lo)
    out = [
        {"type": "extreme", "text": f"{labels[hi_i]}最高 {hi:g}{unit}，{labels[lo_i]}最低 {lo:g}{unit}"},
    ]
    if lo:
        out.append({"type": "gap", "text": f"最高与最低差 {hi - lo:g}{unit}（{hi / lo:.1f} 倍）"})
    top = sorted(vals, reverse=True)
    s = sum(top) or 1
    if len(vals) >= 4:
        out.append({"type": "concentration", "text": f"前三名合计占 {sum(top[:3]) / s:.0%}"})
    med = statistics.median(vals)
    mad = statistics.median([abs(v - med) for v in vals]) or 1
    for v, lab in zip(vals, labels):
        if abs(v - med) > 2.5 * mad:
            out.append({"type": "outlier", "text": f"{lab} 偏离中位数 {v - med:+.1f}{unit}"})
            break
    return out[:4]


def encoding_to_chart(claim: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Vega-Lite 子集 → 现有图表 spec。图是编码的产物，不是偏好。"""
    enc = claim.get("encoding") or {}
    rows = claim.get("rows") or []
    if len(rows) < 2:
        return None
    mark = str(enc.get("mark") or "bar")
    unit = str(claim.get("unit") or "—")
    src = str(claim.get("source") or "本节来源见附录")
    refs = list(claim.get("refs") or [])
    items = [{"label": str(r.get("label")), "value": float(r.get("value"))} for r in rows]
    if mark in ("bar", "column"):
        typ = "hbar" if str(enc.get("y") or "").lower() in ("label", "category", "nominal") else "vbar"
        return {"type": typ, "title": str(claim.get("claim") or ""), "unit_meta": unit,
                "source": src, "refs": refs, "items": items}
    if mark == "line":
        return {"type": "line", "title": str(claim.get("claim") or ""), "unit_meta": unit,
                "source": src, "refs": refs, "points": items}
    if mark == "arc":
        return {"type": "donut", "title": str(claim.get("claim") or ""), "unit_meta": unit,
                "source": src, "refs": refs, "items": items}
    if mark == "point":
        return {"type": "dot", "title": str(claim.get("claim") or ""), "unit_meta": unit,
                "source": src, "refs": refs, "points": items}
    return {"type": "hbar", "title": str(claim.get("claim") or ""), "unit_meta": unit,
            "source": src, "refs": refs, "items": items}


def validate_v4(claims: List[Dict[str, Any]]) -> List[str]:
    from core import report_contract
    errs: List[str] = []
    if not claims:
        return ["claims 为空"]
    main_n = sum(1 for c in claims if str(c.get("tier") or "main") == "main")
    cap = report_contract.main_claims_max()
    if cap > 0 and main_n > cap:
        errs.append(f"主判断 {main_n} 条 > 上限 {cap}；"
                    f"第 {cap + 1} 条起标 tier=support 进附录")
    max_chars = report_contract.paragraph_hard_max()
    main_claims = [c for c in claims if str(c.get("tier") or "main") == "main"]
    ranks = []
    for c in main_claims:
        cid = c.get("id") or "?"
        if c.get("decision_rank") is None:
            errs.append(f"{cid} 主判断缺 decision_rank")
        else:
            ranks.append(int(c["decision_rank"]))
        if not str(c.get("headline") or "").strip() and not str(c.get("headline_ref") or "").strip():
            errs.append(f"{cid} 主判断缺 headline/headline_ref（决策数字必须作者给）")
    if len(ranks) != len(set(ranks)):
        errs.append("decision_rank 有重复")
    for c in claims:
        cid = c.get("id") or "?"
        rows = c.get("rows") or []
        if not c.get("claim"):
            errs.append(f"{cid} 缺 claim 句")
        if len(str(c.get("claim") or "")) > 80:
            errs.append(f"{cid} claim 超过 80 字")
        if len(rows) < 2:
            errs.append(f"{cid} slice 少于 2 行")
        # 同图同单位：rows 若带 unit，必须一致；否则用 claim.unit
        row_units = {str(r.get("unit")) for r in rows if r.get("unit")}
        if len(row_units) > 1:
            errs.append(f"{cid} slice 混单位：{sorted(row_units)[:3]}")
        if c.get("unit") and row_units and str(c["unit"]) not in row_units:
            errs.append(f"{cid} claim.unit 与 rows 单位不一致")
        chart = encoding_to_chart(c)
        if chart is None:
            errs.append(f"{cid} 无法从 encoding 出图")
        elif len(chart.get("items") or chart.get("points") or []) != len(rows):
            errs.append(f"{cid} 图的数据点与 slice 行数不一致")
        if not c.get("findings"):
            errs.append(f"{cid} 缺 findings（文字必须有发现来源）")
        bad = [f for f in c.get("findings") or [] if f.get("type") not in VALID_FINDINGS]
        if bad:
            errs.append(f"{cid} 发现类型非法：{bad[:2]}")
        if not str(c.get("warrant") or "").strip():
            errs.append(f"{cid} 缺 warrant（机理）")
        if str(c.get("tier") or "main") not in ("main", "support"):
            errs.append(f"{cid} tier 只能是 main/support")
        if str(c.get("tier") or "main") == "main":
            if not c.get("table"):
                errs.append(f"{cid} 主判断缺 table（1 图 + 1 表）")
            if not c.get("action"):
                errs.append(f"{cid} 主判断缺 action")
            if not c.get("falsifier"):
                errs.append(f"{cid} 主判断缺 falsifier（停止条件）")
        for r in rows:
            for k in ("label", "value"):
                if r.get(k) in (None, ""):
                    errs.append(f"{cid} row 缺 {k}")
    return errs


def claim_to_section(c: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """claim → 现有渲染器认识的一节（五块）。"""
    findings = c.get("findings") or []
    fact = "；".join(str(f.get("text") or "") for f in findings if f.get("text"))
    reading = [
        {"strong": "事实　", "text": fact, "refs": c.get("refs") or []},
        {"strong": "机理　", "text": str(c.get("warrant") or ""), "refs": c.get("refs") or []},
    ]
    rebut = str(c.get("rebuttal") or "").strip()
    if rebut:
        reading.append({"strong": "反例　", "text": rebut, "refs": c.get("refs") or []})
    action = str(c.get("action") or "").strip()
    if action:
        reading.append({"strong": "所以　", "text": action, "refs": c.get("refs") or []})
    sec = {
        "title": str(c.get("claim") or ""),
        "question": str(c.get("question") or ""),
        "refs": c.get("refs") or [],
        "reading": reading,
        "boundary": str(c.get("qualifier") or ""),
        "falsifier": str(c.get("falsifier") or ""),
        "answers": c.get("answers") or ([c["qid"]] if c.get("qid") else []),
        "chart": encoding_to_chart(c),
        "appendix": str(c.get("tier") or "main") == "support",
        # 决策排序与头条数字由作者给，不再由渲染层猜
        "decision_rank": int(c.get("decision_rank") or 9999),
        "headline": str(c.get("headline") or ""),
        "headline_ref": str(c.get("headline_ref") or ""),
    }
    if c.get("table"):
        sec["table"] = c["table"]
    return sec


def _headline_of(c: Dict[str, Any]) -> str:
    """决策数字：作者给的 headline 优先；否则按 headline_ref 找 row；最后才退第一行。"""
    s = str(c.get("headline") or "").strip()
    if s:
        return s
    rows = c.get("rows") or []
    ref = str(c.get("headline_ref") or "")
    if ref:
        for r in rows:
            if str(r.get("ref") or r.get("id") or "") == ref:
                return f"{float(r.get('value', 0)):g}{r.get('unit') or c.get('unit') or ''}"
    if rows:
        r0 = rows[0]
        return f"{float(r0.get('value', 0)):g}{r0.get('unit') or c.get('unit') or ''}"
    return ""


def build_decision(draft: Dict[str, Any]) -> Dict[str, Any]:
    """claims → 一页决策纸：按 decision_rank 取前 N 条，每条 1 数字 + 1 动作 + 1 停止。"""
    from core import report_contract
    claims = [c for c in (draft.get("claims") or [])
              if str(c.get("tier") or "main") == "main"]
    claims = sorted(
        enumerate(claims),
        key=lambda x: (int(x[1].get("decision_rank") or 9999), x[0]))
    claims = [c for _i, c in claims][: int(report_contract.get("decision_items_max", 5))]
    items = []
    for c in claims:
        items.append({
            "claim": str(c.get("claim") or "")[:80],
            "number": _headline_of(c),
            "action": str(c.get("action") or "待验证"),
            "stop": str(c.get("falsifier") or c.get("qualifier") or "待验证"),
        })
    first = items[0]["claim"] if items else "报告"
    return {
        "title": first[:20],
        "subtitle": "给一人公司：做不做 / 先做哪个 / 钱怎么分",
        "items": items,
        "one_thing": items[0]["action"] if items else "",
        "boundary": "以上判断的证据、口径与缺口见附录。",
    }


def build_sections(draft: Dict[str, Any]) -> List[Dict[str, Any]]:
    from core import report_contract
    claims = list(draft.get("claims") or [])
    # 作者给的 decision_rank 是主判断顺序；没给才按原顺序
    claims = [c for _i, c in sorted(
        enumerate(claims),
        key=lambda x: (int(x[1].get("decision_rank") or 9999), x[0]))]
    secs = [claim_to_section(c, i) for i, c in enumerate(claims, 1)]
    main = [s for s in secs if not s.get("appendix")]
    sup = [s for s in secs if s.get("appendix")]
    cap = report_contract.main_claims_max()
    if cap > 0 and len(main) > cap:
        # 只有显式设置上限时才截断；0 = 自适应，全部保留在正文
        for s in main[cap:]:
            s["appendix"] = True
        sup = main[cap:] + sup
        main = main[:cap]
    return main + sup
