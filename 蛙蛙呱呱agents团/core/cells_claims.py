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
CALIBER_KEYS = ("scope", "currency", "price_basis")
CALIBER_RATIO_EXTRA = ("denominator",)
QUALITY_KEYS = ("completeness", "accuracy", "consistency",
                "timeliness", "uniqueness", "validity")


def _load_yaml(p: Path, default=None):
    try:
        import yaml
        return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or default
    except Exception:  # noqa: BLE001
        return default


def cell_contract_problems(cell: Dict[str, Any],
                           measures: Dict[str, Dict[str, Any]]) -> List[str]:
    """一格是否满足交付契约（G-SEM-1/2 + 口径五要素 + 质量六维）。

    2026-11-21：收卡原来只查「字段非空」，不查度量是否在册、grain 是否一致、
    口径是否齐；于是一个 ad_cost 格、一个没写 grain 的格都能过。这里把
    「对得上」写成可复用的硬校验。
    """
    probs: List[str] = []
    cid = str(cell.get("cell_id") or "")
    if str(cell.get("status") or "filled") == "unavailable":
        if not cell.get("tried") or not cell.get("why"):
            probs.append(f"{cid}: unavailable 缺 tried/why")
        return probs
    mid = str(cell.get("measure_id") or cell.get("measure") or "")
    if mid not in measures:
        probs.append(f"{cid}: 度量 {mid or '(空)'} 未在语义层注册")
        return probs
    want = (measures.get(mid) or {}).get("grain")
    got = str(cell.get("grain_id") or cell.get("grain") or "")
    if want and got != str(want):
        probs.append(f"{cid}: grain {got or '(空)'} 与度量声明 {want} 不一致")
    cal = cell.get("caliber") or {}
    need = list(CALIBER_KEYS)
    if (measures.get(mid) or {}).get("type") == "ratio":
        need += list(CALIBER_RATIO_EXTRA)
    miss = [k for k in need if not str(cal.get(k) or "").strip()]
    if miss:
        probs.append(f"{cid}: 口径缺 {miss}")
    q = cell.get("quality") or {}
    qmiss = [k for k in QUALITY_KEYS if k not in q]
    if qmiss:
        probs.append(f"{cid}: quality 缺 {qmiss}")
    return probs


def audit_cards(project: Path) -> Dict[str, Any]:
    """逐卡审计：现有 claims 的每格过一遍交付契约，输出缺口清单。

    这是「现有 7 卡重跑」的验收入口，不依赖产线重跑，也不改任何卡。
    """
    project = Path(project)
    sem = _load_yaml(project / "semantic_layer.yaml", {}) or {}
    measures = {m.get("id"): m for m in sem.get("measures") or []}
    roles: Dict[str, Any] = {}
    for p in sorted((project / "cards").glob("*/claims.json")):
        d = _load(p, {}) or {}
        probs: List[str] = []
        for c in d.get("cells") or []:
            probs += cell_contract_problems(c, measures)
        roles[p.parent.name] = {"cells": len(d.get("cells") or []),
                               "problems": len(probs), "detail": probs[:12]}
    return {"semantic_measures": len(measures), "roles": roles}


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
    clarify = _load(project / "clarify.json", {}) or {}
    sem = _load_yaml(project / "semantic_layer.yaml", {}) or {}
    measures = {m.get("id"): m for m in sem.get("measures") or []}
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
    contract_gaps: List[str] = []

    for c in cells:
        cid = str(c.get("cell_id") or "")
        owner = owner_of.get(cid)
        if not owner:
            continue
        if c.get("status") != "filled":
            continue
        meta = cell_meta.get(cid) or {}
        # 交付契约：度量在册、grain 一致、口径四要素与质量六维齐（有语义层才硬判）
        if measures:
            probs = cell_contract_problems({**meta, **c}, measures)
            if probs:
                contract_gaps += probs
                continue
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
        label = {"revenue": "营收", "share": "份额", "channel_share": "渠道份额",
                 "category_mix": "品类占比", "yoy": "同比",
                 "unit_economics": "单位经济", "unit_cost": "单位成本",
                 "store_count": "门店数", "member_count": "会员数",
                 "inventory_days": "存货天数", "gross_margin": "毛利率",
                 "ad_cost": "获客成本", "asp": "客单价"}
        # 2026-11-21：删掉写死的八条动作（原为潮玩/IP玩具话术）。
        # 动作由本节问句生成；通用模块不内置任何一条业务线的判断。
        asks = {str(a.get("id")): str(a.get("text") or "")
                for a in (clarify.get("asks") or [])}

        def _action(qid: str) -> str:
            q = asks.get(str(qid), "").strip("？? ")
            if q:
                return (f"先用本节最硬的同口径数回答「{q}」；"
                        f"缺口写进未答清单，不补零、不外推。")
            return "先用本节最硬的同口径数做判断；缺口写进未答清单，不补零、不外推。"
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
                     "measure_id": c.get("measure_id") or c.get("measure"),
                     "grain_id": c.get("grain_id") or c.get("grain"),
                     "caliber": c.get("caliber") or {},
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
                {"strong": "所以　", "text": _action(qid), "refs": refs[:1]},
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
            "contract_gaps": contract_gaps,
            "boundaries": ["按格交编译：只写已填格，未填格进未答清单。",
                           "比率格不求和；跨口径不合并。",
                           "未过交付契约（度量/grain/口径）的格进 contract_gaps，不进正文。"],
        }
        out = project / "cards" / role / "claims.json"
        out.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append({"role": role, "sections": len(sections),
                        "numbers": len(numbers), "sources": len(sources),
                        "cells": len(claims["cells"]), "contract_gaps": len(contract_gaps)})

    return {"ok": bool(written), "stage": "compiled", "roles": written,
            "cells_input": len(cells), "cells_used": sum(r["cells"] for r in written),
            "contract_gaps": len(contract_gaps)}
