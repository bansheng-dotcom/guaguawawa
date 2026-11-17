# -*- coding: utf-8 -*-
"""core/report_compose —— 把分析方法库产出的 finding 装配成章节稿并过账。

分工（这条产线只有一条，本模块是「分析 → 稿」这一段，不渲染）：
    analysis_desk  读数据、建证据索引
    analysis_methods  跑方法、出带数字的判断
    report_thesis  选题：这批证据要回答哪几个问题
    report_compose（本模块）  装配章节稿 → evidence_pack + draft_sections
    report_flow    逐节过账（数字必须可由 refs 解释）→ 唯一渲染器

约束：
1. 章节只来自 finding，不手写 HTML、不写「通用总结」；
2. 每个数字都已在 Cite 里登记（pack id 或 derived 公式），校验器能复算；
3. 缺的节写进「缺口」，不用形容词补；
4. 开篇结论、动作清单由纲领层给，本模块只做装配与一致性检查。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import (analysis_desk, analysis_methods, claims, frames, frames_cheese,
                  frames_framework, methods, report_flow, report_thesis,
                  runner)
from core.report_kernel import contract as kernel_contract

PRODUCER = "r01"

# P4：lens 只做方法权重（选哪些方法进报告），不改章节结构、不改门禁。
LENS_METHODS: Dict[str, List[str]] = {
    "market": ["size", "sizing_multi", "growth", "demand", "structure", "mix",
               "trend", "volume", "channel", "region", "supply", "policy",
               "consistency", "coverage", "concentration", "momentum",
               "trajectory", "contribution", "economics", "transmission",
               "arbitrage", "risk", "sample"],
    "ops": ["economics", "cost", "margin", "unit_econ", "breakeven", "structure",
            "contribution", "momentum", "trajectory", "transmission", "risk",
            "sample"],
    "chain": ["transmission", "chain", "economics", "arbitrage", "contribution",
              "risk"],
    "fix": ["economics", "breakeven", "transmission", "contribution", "risk"],
}

# 装配器注册表：每个装配模块用 FRAMES 声明自己负责哪些纲领，这里只做汇总。
# 新增一个域 = 在所属模块的 FRAMES 里加一行，不改本文件的控制流；
# 同一纲领被两个模块注册会直接报错，避免又长出一份「都能装配」的隐式 fallback。
_ASSEMBLERS: Dict[str, Any] = {}
for _mod in (frames, frames_cheese, frames_framework):
    for _key in getattr(_mod, "FRAMES", {}):
        if _key in _ASSEMBLERS:
            raise RuntimeError(f"纲领 {_key} 被多个装配器注册，先删掉旧的那一份")
        _ASSEMBLERS[_key] = _mod.build


def _assemble(th: str, ctx, findings: Dict[str, Any]):
    """按纲领找装配器；没有注册的走通用「按 finding 出节」。"""
    fn = _ASSEMBLERS.get(th)
    return fn(th, ctx, findings) if fn else None


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def _subject(project: str) -> str:
    s = str(project)
    for prefix in ("新业务_", "新业务-", "研究_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    for tail in ("调研", "分析", "报告", "可行性"):
        s = s.replace(tail, "")
    if "_" in s and s.rsplit("_", 1)[-1][:2].isdigit():
        s = s.rsplit("_", 1)[0]
    return s.strip("_- ") or project


def _section_from(f) -> Dict[str, Any]:
    sec: Dict[str, Any] = {
        "title": f.title,
        "question": f.question,
        "refs": list(dict.fromkeys(f.refs)),
        "reading": [dict(r) for r in f.reading],
        "assumptions": list(dict.fromkeys(round(float(a), 6) for a in f.assumptions)),
    }
    if f.chart:
        sec["chart"] = f.chart
    if f.table:
        sec["table"] = f.table
    if f.boundary:
        sec["boundary"] = f.boundary
    return sec


def _section_of(f) -> Dict[str, Any]:
    """v7：方法带 Claim 的，走论证层装配（观察→机理→落点→证伪）；
    老方法没有 Claim，仍按原来的方式装配，两条路共用同一个渲染器与同一套门禁。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    if cl is not None:
        return claims.to_section(cl, f.question)
    return _section_from(f)


def _metrics(picked: List[Any], label_of: Dict[str, int]) -> List[Dict[str, Any]]:
    """指标带：只用正文里真的出现的节，避免「第 - 节」这种空洞指向。"""
    out: List[Dict[str, Any]] = []
    for f in picked:
        m = (getattr(f, "meta", None) or {}).get("metric")
        if m:
            out.append(dict(m))
            if len(out) >= 4:
                break
            continue
        idx = label_of.get(f.key, "-")
        if idx in ("-", "", None):
            continue
        rows = (f.meta or {}).get("rows") or (f.meta or {}).get("stats") or []
        if f.key == "economics" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 净利率", "value": r["margin"].p(),
                        "note": f"第 {idx} 节 · 扣损耗冷链",
                        "status": "healthy" if r["v"] > 0 else "critical"})
        elif f.key == "structure" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 区间涨幅", "value": r["ch"].p(),
                        "note": f"第 {idx} 节 · 首末两期",
                        "status": "critical" if r["v"] > 0 else "healthy"})
        elif f.key == "momentum" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 同比", "value": r["yoy"].p(),
                        "note": f"第 {idx} 节 · 最新一期",
                        "status": "critical" if r["y"] > 0 else "healthy"})
        elif f.key == "arbitrage" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 跨市净利",
                        "value": f"{r['nv'].value:+.2f} 元/斤",
                        "note": f"第 {idx} 节 · 扣运费冷链",
                        "status": "healthy" if r["v"] > 0 else "critical"})
        elif f.key == "breakeven" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 保本提价", "value": r["up"].p(),
                        "note": f"第 {idx} 节 · 只覆盖损耗冷链",
                        "status": "watch"})
        elif f.key == "trajectory" and rows:
            r = max(rows, key=lambda x: abs(x["ch"]))
            out.append({"label": f"{r['cat']} 区间变化", "value": f"{r['ch']:+.1f}%",
                        "note": f"第 {idx} 节 · 首末两期",
                        "status": "critical" if r["ch"] < 0 else "healthy"})
        elif f.key == "risk":
            n = (f.meta or {}).get("no_base_count")
            if n:
                out.append({"label": "无批发基准", "value": f"{n} 个",
                            "note": f"第 {idx} 节 · 覆盖缺口", "status": "watch"})
        if len(out) >= 4:
            break
    return out


def _actions_section(cite, findings: Dict[str, Any],
                     acts: List[Dict[str, str]]) -> Dict[str, Any]:
    rows = [[a["do"], a["condition"], a["stop"]] for a in acts]
    stops = sum(1 for a in acts if a.get("stop"))
    anchor = cite.n("动作条数", len(acts), "条", digits=0)
    reading = []
    for i, a in enumerate(acts, 1):
        refs = list(a.get("refs") or []) or [anchor.id]
        reading.append({"text": f"动作 {i}：{a['do']}；前置：{a['condition']}；"
                                f"停止：{a['stop']}。", "refs": refs})
    if len(reading) < 2:
        reading.append({"text": "动作只有一条时，先按前置条件做单点验证；"
                                "验证窗口不通过就不扩面。", "refs": [anchor.id]})
    return {
        "title": f"动作：{len(acts)} 条动作、{stops} 条停止条件", "reading_style": "list",
        "question": "接下来做什么，什么情况下必须停？",
        "reading": reading,
        # 阈值（配额 40%、履约 95%）是策略假设，显式声明后允许出现在正文
        "assumptions": [40, 95, 3, 5, 2, 20, 60],
        "table": {"caption": "动作 / 前置条件 / 停止条件",
                  "columns": [{"text": h} for h in ("动作", "前置", "停止")],
                  "rows": [[{"text": c} for c in r] for r in rows]},
        "boundary": "动作以本轮测算为前置；前置不成立时先补数，不执行。",
    }


def _gap_section(cite, missing: List[str], gaps: List[str],
                 risk) -> Optional[Dict[str, Any]]:
    items = []
    label = {"structure": "横截面分化", "momentum": "环比/同比", "trajectory": "时间轨迹",
             "contribution": "两期贡献", "economics": "单位经济", "transmission": "上下游传导",
             "arbitrage": "跨市场价差", "breakeven": "保本线", "risk": "风险",
             "sample": "样本充分性"}
    # 同一个方法只留一句：方法层已经给出更准确的原因（算不下去 / 数据不足）时，
    # 不再补一句「未命中：数据里没有支撑字段」，否则同一件事会被说两遍。
    said = set()
    for g in gaps:
        m = re.match(r"^「([^」]+)」", g)
        if m:
            said.add(m.group(1))
    for k in missing:
        name = label.get(k, k)
        if name in said:
            continue
        items.append(f"「{name}」本轮未命中：数据里没有支撑该判断的字段。")
    for g in gaps:
        items.append(g)
    if not items:
        return None
    anchor = cite.n("未观测项数", len(items), "项", digits=0)
    reading = [{"text": t, "refs": [anchor.id]} for t in items]
    if len(reading) < 2:
        reading.append({"text": "缺口不影响已观测部分的数字；本节只说明哪些判断现在还不能下。",
                        "refs": [anchor.id]})
    sec = {
        "title": f"缺口：{len(items)} 项未观测，相关结论不写", "reading_style": "list",
        "question": "哪些结论现在还不能下？",
        "reading": reading,
        "assumptions": [],
        "refs": [anchor.id],
    }
    if risk and risk.table:
        sec["table"] = risk.table
        sec["refs"] = list(dict.fromkeys(list(risk.refs) + [anchor.id]))
    return sec


def _count_numbers(pack: Dict[str, Any]) -> int:
    return len(pack.get("numbers") or [])


# --------------------------------------------------------------------------- #
# 开工前契约：动笔之前先回答六件事（判定规则见 core/report_kernel/contract.py）
# --------------------------------------------------------------------------- #
def _contract(intent: str, th: str, spec: Dict[str, Any], title: str,
              desk, views, picked: List[Any], sections: List[Dict[str, Any]],
              audience: str) -> Dict[str, Any]:
    """从纲领 + 数据 + 已选节推导契约。

    能从数据里算出来的字段（截止日、期数、跨度、跨市、来源数）一律实算；
    算不出来的（受众）由调用方给，给不出就留空让 validate 报 blocker——
    不允许用「通用」「待定」这类字眼把必填项糊过去。
    """
    qs: List[str] = []
    for q in ([str(spec.get("ask") or "")] +
              [str(getattr(f, "question", "") or "") for f in picked] +
              [str(s.get("question") or "") for s in sections]):
        q = q.strip()
        if q and q not in qs:
            qs.append(q)

    dates = sorted(d for d in (analysis_methods._iso_date(str(t))
                               for pts in (views.series or {}).values()
                               for t, _ in pts) if d)
    cutoff = dates[-1] if dates else ""
    periods = max((len(v) for v in (views.series or {}).values()), default=0)
    span = 0
    if dates:
        try:
            span = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days
        except ValueError:
            span = 0
    # 期次对齐是可验证的：所有品类共用同一组期标签才算对齐
    sets = {tuple(t for t, _ in pts) for pts in (views.series or {}).values()}
    aligned = bool(sets) and len(sets) == 1
    regions = {k[0] for k in (views.region or {})} | {k[0] for k in (views.quotes or {})}
    src_n = len((desk.pack or {}).get("sources") or [])
    # 档位由证据规模决定，不再一律自称 L4
    target_level = "L4" if (src_n >= 10 and periods >= 6) else "L3"

    raw = {
        "report_id": f"RPT-{datetime.now():%Y%m%d}-{th.replace('_', '-')[:12]}",
        "title": title,
        "decision": intent,
        "audience": audience,
        "questions": qs[:5],
        "data_cutoff": cutoff,
        "target_level": target_level,
        "owner": PRODUCER,
        "reviewer": "r04",
        "source_count": src_n,
        "series_periods": periods,
        "time_span_days": span,
        "cross_market": len(regions) >= 2,
        "alignment_note": "各品类期次已对齐（同一批采集期）" if span > 1 and aligned else "",
        "trend_required": bool(th == "forecast" and periods >= 12),
    }
    v = kernel_contract.validate(raw)
    return {"contract": v["normalized"],
            "check": {"ok": v["ok"], "errors": v["errors"], "warnings": v["warnings"]}}


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def build(intent: str, project_dir: str, out_dir: str,
          thesis: Optional[str] = None, theme: str = "paper",
          pdf: bool = False, keep_tmp: bool = False,
          audience: str = "业务负责人",
          require_contract: bool = False,
          quote_mode: str = "off",
          lens: Optional[str] = None) -> Dict[str, Any]:
    desk = analysis_desk.scan(project_dir)
    prof = analysis_desk.profile(desk)
    views = analysis_methods.build_views(desk)
    cite = analysis_methods.Cite(desk)
    skills = analysis_methods.Skills()
    os.makedirs(out_dir, exist_ok=True)
    # 注意：不能用 tempfile.mkdtemp（0o700 会切断继承 ACL，沙箱下不可写）
    tmpdir = os.path.join(out_dir, "_work")
    os.makedirs(tmpdir, exist_ok=True)
    ctx = analysis_methods.Ctx(desk=desk, views=views, skills=skills, cite=cite,
                               profile=prof, tmpdir=tmpdir,
                               ft=getattr(desk, "ft", None))
    th = thesis or report_thesis.infer(intent, prof)
    ctx.frame = th
    ctx.intent = intent
    plan_obj = methods.plan(desk, views, prof, th)
    order = list((report_thesis.THESES.get(th) or {}).get("order") or [])
    if order:
        # 只跑本纲领点名的节：不把别的纲领的方法也跑一遍，避免无关键与假缺口
        # （v8：从 market 专属放宽到所有有明确问题链的纲领，含奶酪零食五类）
        allowed = set(order)
        plan_obj["mounted"] = [m for m in plan_obj["mounted"] if m["key"] in allowed]
    if lens:
        allowed = set(LENS_METHODS.get(lens) or [])
        if allowed:
            plan_obj["mounted"] = [m for m in plan_obj["mounted"] if m["key"] in allowed]
    findings, gaps = methods.run(plan_obj, ctx)
    picked, missing = report_thesis.resolve(th, findings)
    prim = report_thesis.PRIMARY.get(th) or []
    if prim and not any(k in findings for k in prim):
        need: List[str] = []
        for m in plan_obj.get("skipped", []):
            if m["key"] in prim:
                need += m.get("missing", [])
        raise report_flow.FlowError(
            f"「{th}」纲领缺主证据（{', '.join(prim)}）："
            f"需要能力 {', '.join(sorted(set(need))) or '未知'}；"
            "补数据后重跑，或先用 report plan 看这份数据能挂哪些方法")
    if not picked:
        need = [n for m in plan_obj.get("skipped", []) for n in m.get("missing", [])]
        raise report_flow.FlowError(
            f"「{th}」纲领没有命中任何可判定的方法："
            f"缺能力 {', '.join(sorted(set(need))) or '未知'}；"
            "请补数据后重跑，或换一个与其数据匹配的纲领（report plan 可先看挂载计划）")

    sections: List[Dict[str, Any]] = []
    label_of: Dict[str, int] = {}
    opening = report_thesis.opening(th, ctx, findings)
    if opening:
        sections.append(opening)
    frame_secs = _assemble(th, ctx, findings)
    if frame_secs:
        # 价格类经营/链路/整改 + 奶酪零食整改：按问题链装配，不按 finding 顺序平铺
        sections.extend(frame_secs)
        for i, s in enumerate(sections):
            t = str(s.get("title") or "")
            for k, w in (("economics", "单位经济"), ("arbitrage", "套利"), ("risk", "风险"),
                         ("transmission", "传导"), ("momentum", "节奏"),
                         ("breakeven", "保本")):
                if w in t:
                    label_of.setdefault(k, i + 1)
    else:
        for f in picked:
            label_of[f.key] = len(sections) + 1
            sections.append(_section_of(f))
    # 整改帧（肉禽蛋）与奶酪零食整改帧已经把动作拆进根因/分段/拍板/不做，
    # 不再追加一份通用的动作清单，避免同一件事说两遍。
    if th not in ("remediation", "cheese_fix", "analysis"):
        acts = report_thesis.actions(th, findings)
        act_sec = _actions_section(cite, findings, acts)
        label_of["actions"] = len(sections) + 1
        sections.append(act_sec)
    risk = findings.get("risk")
    vg = views.gaps or []
    if not any(f.key in ("structure", "economics") for f in picked):
        vg = [g for g in vg if "零售价" not in g and "价格" not in g]
    # 已经有专门的「覆盖缺口」节时，不再追加一份重复的缺口节
    if "coverage" not in findings and th != "analysis":
        gap_sec = _gap_section(cite, missing + vg, gaps, risk)
        if gap_sec:
            sections.append(gap_sec)

    spec = report_thesis.THESES.get(th) or report_thesis.THESES[report_thesis.DEFAULT_THESIS]
    # 项目可自带标题（data/meta.json），避免从目录名硬拼出「家居百货内蒙市场调研报告」这种别扭名
    title = ""
    meta_path = desk.root / "data" / "meta.json"
    if meta_path.exists():
        try:
            title = str(json.loads(meta_path.read_text(encoding="utf-8-sig")).get("title") or "")
        except (json.JSONDecodeError, OSError):
            title = ""
    title = title or f"{_subject(desk.project)}{spec.get('doc_name') or spec['label']}"
    # 契约先立后写：字段算不出来就 blocker，不靠文案兜底。
    # 文件名必须用 report_ship.json：out_dir/contract.json 是渲染契约（report_flow 写），
    # 两者语义不同，同名会互相覆盖。
    cob = _contract(intent, th, spec, title, desk, views, picked, sections, audience)
    os.makedirs(out_dir, exist_ok=True)
    kernel_contract.save(os.path.join(out_dir, "report_ship.json"), cob["contract"])
    if require_contract and not cob["check"]["ok"]:
        raise report_flow.FlowError(
            "开工前契约不成立：" + "；".join(cob["check"]["errors"]))
    sf = report_thesis.standfirst(th, findings)
    titles = [t for t in report_thesis.summary(th, findings) if t != sf]
    summ = titles if th == "market" else [sf] + titles
    draft = {
        "profile": th,
        "intent": intent,
        "title_lines": [title, f"{spec['doc_type']} · {len(sections)} 节 · "
                               "数字由角色技能实跑与公式复算"],
        "standfirst": sf,
        "metrics": _metrics(picked, label_of),
        "summary": summ[:4],
        "sections": sections,
        "boundary": [f.boundary for f in picked if f.boundary][:6] + [
            "所有价格为采集价/报价口径，不是企业结算价；净毛利为情景测算，不含租金、人力与税。"],
        "derived": desk.derived,
    }
    # 非假设型边界不再逐节挂「本节边界」，集中到末节口径里（减少同一个壳）
    agg = []
    for sec in sections:
        if sec.get("boundary") and not sec.get("_inline"):
            agg.append(sec.pop("boundary"))
    for f in picked:
        cl = (getattr(f, "meta", None) or {}).get("claim")
        if f.boundary and not (cl is not None and getattr(cl, "inline_boundary", False)):
            if f.boundary not in agg:
                agg.append(f.boundary)
    seen_b = set()
    draft["boundaries"] = [b for b in agg if not (b in seen_b or seen_b.add(b))]

    # 证据包：项目全部数字 + 本轮登记的数字 + 派生量
    pack = desk.pack
    src_json = desk.root / "data" / "sources.json"
    if src_json.exists():
        try:
            srcs = json.loads(src_json.read_text(encoding="utf-8-sig")).get("sources") or []
            pack.setdefault("sources", []).append(
                {"file": "data/sources.json", "kind": "sources",
                 "hash": report_flow._sha_file(str(src_json)),
                 "numbers": len(srcs)})
        except Exception:  # noqa: BLE001
            pass
    os.makedirs(out_dir, exist_ok=True)
    pack_path = os.path.join(out_dir, "evidence_pack.json")
    with open(pack_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(desk.pack, f, ensure_ascii=False, indent=1)
    draft_path = os.path.join(out_dir, "draft_sections.json")
    with open(draft_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)

    res = report_flow.run(intent=intent, evidence=pack_path, draft=draft,
                          out_dir=out_dir, theme=theme, pdf=pdf,
                          quote_mode=quote_mode)

    # R04 独立评审：物料清点（存在/非空）
    files = res.get("files") or {}
    items = [{"path": files.get("html", ""), "type": "html", "required": True},
             {"path": files.get("md", ""), "type": "md", "required": True},
             {"path": pack_path, "type": "json", "required": True},
             {"path": draft_path, "type": "json", "required": True}]
    if files.get("pdf"):
        items.append({"path": files["pdf"], "type": "pdf", "required": False})
    inv_path = os.path.join(out_dir, "r04_inventory_input.json")
    with open(inv_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=1)
    inv = skills.call("r04", "artifact", "inventory", ["--input", inv_path])
    inv_verdict = inv.get("verdict") or ("COMPLETE" if inv.get("ok") else "BLOCKED")

    # v7 深度门禁：v7 的四类纲领必须过「反模板」检查，不过就判 FAIL（文件保留，便于复盘）
    from core import report_quality
    qa = report_quality.audit(files.get("html", "")) if files.get("html") else {
        "ok": False, "score": 0, "checks": [], "sections": 0, "chars": 0,
        "numbers": 0, "density": 0}
    with open(os.path.join(out_dir, "quality.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(qa, f, ensure_ascii=False, indent=2)
    STRICT = {"market", "operations", "chain", "remediation",
              "cheese_market", "cheese_ops", "cheese_chain",
              "cheese_content", "cheese_fix", "cheese_data", "analysis"}
    quality_ok = bool(qa.get("ok")) if th in STRICT else True

    # 分析轨迹 + manifest 追写
    trace = {
        "schema": "dsh.analysis_transcript/v1",
        "intent": intent,
        "project": str(desk.root),
        "thesis": th,
        "thesis_label": spec["label"],
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "profile": prof,
        "views": {"primary": views.primary, "snapshot": len(views.snapshot),
                  "series": len(views.series), "wholesale": len(views.wholesale),
                  "region": len(views.region), "origins": len(views.origins),
                  "notes": views.source_notes},
        "findings": [{"key": f.key, "title": f.title, "refs": len(f.refs),
                      "chart": (f.chart or {}).get("type"),
                      "table": bool(f.table)} for f in picked],
        "method_plan": plan_obj,
        "missing": missing,
        "gaps": gaps,
        "skills": [{"role": r["role"], "skill": r["skill"], "action": r["action"],
                    "ok": r["ok"]} for r in skills.runs],
        "covered": skills.covered(),
        "numbers": cite.desk.counts(),
        "derived": len(desk.derived),
        "gate": {"section_check": bool(res.get("ok")),
                 "r04": inv_verdict,
                 "r04_missing": inv.get("missing_required") or [],
                 "contract": cob["check"]},
    }
    with open(os.path.join(out_dir, "analysis_trace.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)

    man_path = os.path.join(out_dir, "manifest.json")
    if os.path.exists(man_path):
        man = json.loads(Path(man_path).read_text(encoding="utf-8"))
        man.update({"thesis": th, "thesis_label": spec["label"],
                    "covered": skills.covered(), "gaps": gaps, "missing": missing,
                    "r04": {"verdict": inv_verdict,
                            "missing": inv.get("missing_required") or []},
                    "contract": {"ok": cob["check"]["ok"],
                                 "report_id": cob["contract"].get("report_id"),
                                 "errors": cob["check"]["errors"]},
                    "quality": {"ok": quality_ok, "score": qa.get("score"),
                                "sections": qa.get("sections"),
                                "checks": [{"id": c["id"], "ok": c["ok"],
                                            "value": c.get("value")}
                                           for c in (qa.get("checks") or [])]},
                    "analysis_trace": "analysis_trace.json",
                    "ok": bool(man.get("ok")) and inv_verdict in ("COMPLETE", "PASS")
                    and quality_ok})
        with open(man_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)

    if not keep_tmp:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return {
        "ok": bool(res.get("ok")) and quality_ok,
        "thesis": th,
        "sections": len(sections),
        "findings": [f.key for f in picked],
        "covered": skills.covered(),
        "numbers": desk.counts(),
        "files": files,
        "r04": inv_verdict,
        "contract": {"ok": cob["check"]["ok"],
                     "required": bool(require_contract),
                     "report_id": cob["contract"].get("report_id"),
                     "errors": cob["check"]["errors"],
                     "warnings": cob["check"]["warnings"]},
        "quality": {"ok": quality_ok, "score": qa.get("score"),
                    "sections": qa.get("sections"), "chars": qa.get("chars"),
                    "density": qa.get("density")},
        "out": out_dir,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="report_compose")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--thesis", default=None,
                    choices=list(report_thesis.THESES) + [None])
    ap.add_argument("--theme", default="paper")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--audience", default="业务负责人")
    ap.add_argument("--require-contract", action="store_true")
    ap.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="off")
    a = ap.parse_args(argv)
    res = build(a.intent, a.dir, a.out, thesis=a.thesis, theme=a.theme, pdf=a.pdf,
                audience=a.audience, require_contract=a.require_contract,
                quote_mode=a.quote_mode)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
