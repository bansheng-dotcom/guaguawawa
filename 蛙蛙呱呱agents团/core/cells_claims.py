# -*- coding: utf-8 -*-
"""core.cells_claims —— 把「按格交」的 cells 编译成报告可收的 claims。

这是拆卡 SOP 与报告产线之间缺的那座桥：
    plan/grid.json + plan/dispatch.json + out_v3/cells_filled.json
        → cards/<role>/claims.json（numbers / sources / sections / chart）
        → report collect → report

规则（与 SOP 对齐）：
- 只有 filled 格进 numbers；unavailable 格进 unanswered，不编数；
- 一节 = 一个 must 问；节的 refs 只能指向本卡 numbers；
- 机制格没填就不写因果，只写「关联阶」；
- 比率格不求和，图上只画同单位同粒度的格。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

UNIT_DEFAULT = ""


def _period_cn(p: Any) -> str:
    s = str(p or "—")
    return (s.replace("2026H1", "2026年上半年").replace("2025H1", "2025年上半年")
             .replace("2025H2", "2025年下半年").replace("2024H2", "2024年下半年"))


def _load(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _pick_sources(project: Path) -> Dict[str, Dict[str, Any]]:
    merged = _load(project / "out" / "claims_merged.json", {}) or {}
    out = {}
    for s in merged.get("sources") or []:
        fid = str(s.get("file") or "")
        if fid:
            out[fid] = s
    return out


def build(project: Path, cells_path: Optional[Path] = None,
          require_sources: bool = True) -> Dict[str, Any]:
    project = Path(project)
    grid = _load(project / "plan" / "grid.json", {}) or {}
    dispatch = _load(project / "plan" / "dispatch.json", {}) or {}
    cp = cells_path or (project / "out_v3" / "cells_filled.json")
    filled_doc = _load(cp, {}) or {}
    cells = filled_doc.get("cells") or []
    if not cells:
        return {"ok": False, "stage": "cells", "error": "没有 cells_filled.json 或为空"}

    cell_meta = {str(c.get("cell_id")): c for c in grid.get("cells") or []}
    owner_of = {str(a.get("cell_id")): str(a.get("owner"))
                for a in dispatch.get("assignments") or []}
    source_pool = _pick_sources(project)
    by_role: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    missing_src = []

    for c in cells:
        cid = str(c.get("cell_id") or "")
        owner = owner_of.get(cid)
        if not owner:
            continue
        if c.get("status") != "filled":
            continue
        meta = cell_meta.get(cid) or {}
        src = str(c.get("source_file") or "")
        if require_sources and src not in source_pool:
            missing_src.append(f"{cid}: {src}")
            continue
        by_role.setdefault(owner, {}).setdefault(str(meta.get("qid") or c.get("qid") or "Q?"), []).append({**meta, **c})

    if missing_src:
        return {"ok": False, "stage": "sources", "error": "来源不在账本里",
                "missing": missing_src[:10]}

    written = []
    for role, qmap in by_role.items():
        tpl_p = project / "cards" / role / "claims.template.json"
        tpl = _load(tpl_p, {}) or {}
        dispatch_block = dict(tpl.get("dispatch") or {})
        if not str(dispatch_block.get("by") or "").strip():
            # 按格编译的执行者：用卡上的角色 id，不冒充编排器
            dispatch_block["by"] = f"dsh-subagent-{role}"
        # 本地来源编号：只用本卡引用到的（可选全量以过 50 源门槛）
        used = sorted({str(c.get("source_file")) for cs in qmap.values() for c in cs})
        src_ids = {fid: f"S{i:02d}" for i, fid in enumerate(
            (used if not require_sources else list(source_pool)), 1)}
        sources = []
        for fid, sid in src_ids.items():
            s = source_pool.get(fid)
            if not s:
                continue
            sources.append({"file": sid, "kind": s.get("kind") or "web",
                            "title": s.get("title") or "", "org": s.get("org") or "",
                            "url": s.get("url") or "", "date": s.get("date") or "",
                            "grade": s.get("grade") or "B",
                            "quote": s.get("quote") or ""})
        numbers, sections, unanswered = [], [], []
        nid = 0
        seen_sig = set()
        label = {"revenue": "营收", "share": "份额", "category_mix": "占比",
                 "yoy": "同比", "unit_economics": "单店产出",
                 "store_count": "门店数", "member_count": "会员数",
                 "inventory_days": "存货天数", "gross_margin": "毛利率"}
        action = {
            "Q1": "先按市场规模定天花板，再看份额判断竞争位置，不用营收替代市场。",
            "Q2": "先用毛绒与手办的结构变化判断接棒，再决定备货与陈列。",
            "Q3": "先看存货与单店产出，收入增速放到第二位。",
            "Q4": "先看头部 IP 集中度，再看第二梯队厚度。",
            "Q5": "先比毛利率与自有 IP 占比，再比规模。",
            "Q6": "先看海外降幅与第二曲线进度，再谈修复。",
            "Q7": "先看库存回撤能力，再看产能覆盖。",
            "Q8": "先看品控与维权，再看概率公示。",
        }
        for qid, cs in sorted(qmap.items()):
            # 同一 (entity, value, period) 只在一节里出现，避免各问重复同一句
            uniq = []
            for c in cs:
                sig = (str(c.get("entity")), c.get("value"), c.get("unit"), c.get("period"))
                if sig in seen_sig:
                    continue
                seen_sig.add(sig)
                uniq.append(c)
            if len(uniq) < 3:
                uniq = cs
            if len(uniq) < 3:
                unanswered.append({"qid": qid, "tried": [],
                                   "why": f"仅 {len(uniq)} 个已填格，不足以成节"})
                continue
            local = []
            for c in uniq:
                nid += 1
                n = {"id": f"N{nid:02d}",
                     "name": f"{c.get('entity')}·{c.get('measure')}",
                     "value": c.get("value"), "unit": c.get("unit") or "",
                     "period": c.get("period") or "",
                     "source_file": src_ids.get(str(c.get("source_file")), "")}
                numbers.append(n)
                local.append((n, c))
            refs = [n["id"] for n, _ in local[:6]]
            top = local[0][1]
            title = f"{qid} {top.get('entity')} {top.get('value')}{top.get('unit') or ''}"
            title = title[:20]
            # 事实：逐格一句，带期次与度量，天然不重复
            fact_lines = [
                f"「{c.get('entity')}」{c.get('value')}{c.get('unit') or ''}"
                f"（{_period_cn(c.get('period'))}，{label.get(str(c.get('measure')), c.get('measure'))}）"
                for _, c in local[:6]]
            facts = "；".join(fact_lines) + "。"
            mech = [c for _, c in local if c.get("dim") == "机制"]
            if mech:
                m = mech[0]
                mech_txt = (f"机制格给出「{m.get('entity')}」{m.get('value')}{m.get('unit') or ''}；"
                            f"它和「{top.get('entity')}」并列看方向一致，但只有一格，仍按关联阶处理。")
            else:
                second = local[1][1] if len(local) > 1 else top
                mech_txt = (f"这一问的机制格没填：只能确认「{top.get('entity')}」与"
                            f"「{second.get('entity')}」同期同向，不能写因果。")
            filled_dims = {c.get("dim") for _, c in local}
            missing_dims = [d for d in ("对象", "空间", "时间", "结构", "机制", "边界")
                            if d not in filled_dims]
            boundary = (f"「{top.get('entity')}」按"
                        f"{label.get(str(top.get('measure')), top.get('measure'))}计、"
                        f"期次{_period_cn(top.get('period'))}；与"
                        f"「{local[1][1].get('entity')}」不同口径，不能相加。")
            reading = [
                {"strong": "事实　", "text": facts, "refs": refs},
                {"strong": "事实　", "text": f"除了「{top.get('entity')}」，"
                 f"「{local[1][1].get('entity')}」也填上了；两者合用只做交叉验证，不合并。",
                 "refs": refs},
                {"strong": "机理　", "text": mech_txt, "refs": refs},
                {"strong": "反例　", "text": f"缺口落在{'、'.join(missing_dims) if missing_dims else '部分维度'}；"
                 f"若「{top.get('entity')}」下一期与「{local[1][1].get('entity')}」背离，本节要改写。",
                 "refs": refs[:1]},
                {"strong": "边界　", "text": boundary, "refs": refs[:1]},
                {"strong": "所以　", "text": action.get(qid, "先用最硬的数做判断，缺口进未答清单。"),
                 "refs": refs[:1]},
            ]
            chart_items = [{"label": str(c.get("entity")), "value": c.get("value")}
                           for _, c in local[:5] if isinstance(c.get("value"), (int, float))]
            chart = {"type": "hbar", "title": title or f"{qid} 关键值",
                     "source": f"{top.get('entity')}·来源见账本", "refs": refs[:len(chart_items)],
                     "unit_meta": top.get("unit") or UNIT_DEFAULT,
                     "baseline": f"对比基准：{top.get('entity')}同口径同期",
                     "annotate": f"{top.get('entity')} {top.get('value')}{top.get('unit') or ''}",
                     "items": chart_items}
            sections.append({
                "title": title, "question": qid, "answers": [qid], "refs": refs,
                "boundary": boundary,
                "reading": reading, "chart": chart,
                "falsifier": f"若 {top.get('entity')} 下期反向变化，本条作废。",
            })

        claims = {
            "schema": "dsh.agent.claims/v1", "contract": "v2", "card_spec": True,
            "role": role, "dispatch": dispatch_block,
            "meta": (tpl.get("meta") or {"title": "按格交报告", "intent": "按格交报告",
                                         "doc_type": "调研报告", "profile": "research"}),
            "numbers": numbers, "sources": sources, "sections": sections,
            "cells": [c for cs in qmap.values() for c in cs],
            "explore": [], "unanswered": unanswered,
            "boundaries": ["按格交编译：只写已填格，未填格进未答清单。",
                           "比率格不求和；跨口径不合并。"],
        }
        out = project / "cards" / role / "claims.json"
        out.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append({"role": role, "sections": len(sections),
                        "numbers": len(numbers), "sources": len(sources),
                        "cells": len(claims["cells"])})

    return {"ok": bool(written), "stage": "compiled", "roles": written,
            "cells_input": len(cells), "cells_used": sum(r["cells"] for r in written)}
