# -*- coding: utf-8 -*-
"""业务框架：每个角色「这门生意靠什么转」的声明式定义。

框架只回答三件事：有哪些对象、有哪些决策、要答哪些问题（以及每个问题需要什么数据）。
数据够不够由 analysis_ops.coverage 判定，缺的进「数据缺口」节——不靠文案糊过去。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRAME_DIR = ROOT / "report_specs" / "frames"


def load(role: str) -> Optional[Dict[str, Any]]:
    p = FRAME_DIR / f"{role}.yaml"
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8")) or None


def questions(role: str) -> List[Dict[str, Any]]:
    frame = load(role) or {}
    return list(frame.get("questions") or [])


def gap_section(role: str, available: List[str],
                title: str = "数据缺口：这盘生意还答不了什么") -> Optional[Dict[str, Any]]:
    """把「框架要答但数据没有」的问题做成报告的一节（业务视角，不是技术视角）。"""
    from shared.analysis_ops import coverage

    frame = load(role)
    if not frame:
        return None
    rows = coverage(frame, available)
    blocked = [r for r in rows if r["status"] == "blocked"]
    if not blocked:
        return None
    claims = []
    declared = {}
    try:
        from shared import data_ports
        declared = data_ports.declared_lookup()
    except Exception:  # noqa: BLE001
        declared = {}
    for i, r in enumerate(blocked, 1):
        hint = ""
        for need in (r.get("missing") or []):
            if need in declared:
                d = declared[need]
                hint = f"（端口已声明，待接入：{d['system']}）"
                break
        claims.append({
            "id": f"GAP-{r['id']}", "kind": "opinion",
            "text": f"缺口 {i}/{len(blocked)}：「{r['question']}」——缺 {r['need']}；"
                    f"因此「{r['decision']}」只能靠经验判断，不能写进结论。"
                    f"补齐后本节变成一张可签字的表。{hint}",
            "source_ids": ["FRAME"],
        })
    return {
        "title": "数据缺口",
        "heading": f"{title}：{len(blocked)} 个问题缺数据",
        "verdict": f"{len(blocked)} 个业务问题因缺数据无法回答，已单列并排除出结论。",
        "claim_ids": [c["id"] for c in claims],
        "_claims": claims,
    }


def skeleton_contract(role: str, available: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """没有写作配置的角色也能出一份「业务框架体检」：每个问题可答/缺什么。

    它的价值不在数字，而在把「这盘生意该问什么、现在缺什么」摊开——
    所有角色接入正式证据包之前的第 0 份报告。
    """
    from shared.analysis_ops import coverage

    frame = load(role)
    if not frame:
        return None
    rows = coverage(frame, available or [])
    frame_qs = {str(q.get("id", "")): list(q.get("needs") or [])
                for q in (frame.get("questions") or [])}
    try:
        from shared import data_ports
        _declared = data_ports.declared_lookup()
    except Exception:  # noqa: BLE001
        _declared = {}
    sections: List[Dict[str, Any]] = []
    for i, r in enumerate(rows, 1):
        ok = r["status"] == "answered"
        text = (f"{'可答' if ok else '缺 ' + r['need']}；这条答案会改写「{r['decision']}」。")
        if not ok:
            for need in (r.get("missing") or []):
                if need in _declared:
                    text += f"（端口已声明，待接入：{_declared[need]['system']}）"
                    break
        sections.append({
            "index": i, "title": r["question"],
            "question": "需要：" + ("、".join(frame_qs.get(r["id"], [])) or "—"),
            "reading": [{"strong": "状态：", "text": text}],
            "boundary": {"text": "本节只回答“能不能答”，不代替业务结论。"},
        })
    answered = sum(1 for r in rows if r["status"] == "answered")
    return {
        "doc_type": f"业务框架体检 · {frame.get('domain', role)}",
        "title_lines": [f"{role.upper()} 业务框架体检",
                        f"{len(rows)} 个业务问题，{len(rows) - answered} 个缺数据"],
        "standfirst": f"{frame.get('domain', '')}：先说清该问什么、现在缺什么，再谈报告深度。",
        "metric_strip": [
            {"label": "业务问题", "value": str(len(rows)), "note": "框架声明", "status": "accent"},
            {"label": "可答", "value": str(answered), "note": "现有数据能回答", "status": "healthy"},
            {"label": "缺数据", "value": str(len(rows) - answered), "note": "已单列", "status": "critical"}],
        "meta": [f"角色 {role}", f"对象 {len(frame.get('objects') or [])} 个",
                 f"决策 {len(frame.get('decisions') or [])} 个", "数据：无（框架体检）"],
        "summary": [{"label": "结论：", "text": f"{len(rows)} 个问题里 {answered} 个现在能答，"
                                           f"{len(rows) - answered} 个缺数据；缺的那几个决定动作。"}],
        "sections": sections,
        "notes": {"summary": "口径与边界",
                  "items": [{"label": "来源：", "text": "report_specs/frames/" + role + ".yaml"},
                            {"label": "用法：", "text": "数据补齐后，本报告被正式证据包替换"}]},
        "footer": [f"{role} · shared/business_frame", "无数据时出体检，不编结论"],
    }
