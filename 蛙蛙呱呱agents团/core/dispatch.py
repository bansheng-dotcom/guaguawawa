# -*- coding: utf-8 -*-
"""core/dispatch —— 按 brief 发任务卡、收 claims、合并出报告（v12.2）。

这一步补的是「专家按 brief 自动跑」的骨架：
    之前：brief 有了、闸有了，中间是我手工开子智能体、手工拼 claims。
    现在：三件事进仓库，形成流水线

        python guagua.py report brief   --intent "…" --out <dir>   # 发卡
        （执行者按卡去查，每张卡交 cards/<role>/claims.json）
        python guagua.py report collect --dir <dir> --out <dir>    # 收卡 → 合并 → 过闸 → 出报告

设计原则：
    * 发卡只发「契约 + 角色能力」，不发「该查什么」——查什么由执行者判断；
    * 收卡先验每张卡的完整性（数字有来源、结论有引文、证伪有阈值），
      不合格的卡**不合并**，并列出缺什么；
    * 合并时数字与来源按 id 去重，节次按角色顺序重排，冲突交给交叉质询。

不做什么：
    * 不调用模型（仓库没有 Key，也不该有）——模型在外面跑，这里只做调度与验收。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

CARD_SCHEMA = "dsh.task_card/v1"


def _need(claims: Dict[str, Any]) -> List[str]:
    """一张卡最少要有什么。缺 quote 的来源等于没查，整张卡拒收。"""
    from core import source_verify

    miss = []
    nums = claims.get("numbers") or []
    sources = claims.get("sources") or []
    if not nums:
        miss.append("numbers（没有数字就是没查）")
    if not sources:
        miss.append("sources（没有来源就是没查）")
    if not claims.get("sections"):
        miss.append("sections（没有判断就是没写）")

    src_ids = {str(s.get("file") or "") for s in sources}
    bad_src = []
    for i, s in enumerate(sources, 1):
        fields = source_verify.check_fields(s)
        if fields:
            bad_src.append(f"{s.get('file') or 'S' + str(i)} 缺 " + "/".join(fields))
    if bad_src:
        miss.append("来源字段不全：" + "；".join(bad_src[:3]))
    for n in nums:
        sf = str(n.get("source_file") or "")
        if sf and sf not in src_ids:
            miss.append(f"数字 {n.get('id')} 指向不存在的来源 {sf}")

    local_ids = {str(n.get("id")) for n in nums}
    local_ids |= {str(d.get("id")) for d in (claims.get("derived") or [])}
    for s in claims.get("sections") or []:
        t = str(s.get("title") or "")
        if not s.get("refs"):
            miss.append(f"节「{t}」缺 refs")
        unknown = [r for r in (s.get("refs") or []) if str(r) not in local_ids]
        if unknown:
            miss.append(f"节「{t}」refs 找不到本卡数字：{unknown[:3]}")
        if len([r for r in (s.get("reading") or []) if r.get("text")]) < 2:
            miss.append(f"节「{t}」解读少于 2 条")
        if not s.get("falsifier"):
            miss.append(f"节「{t}」缺证伪条件")
    return miss


def _write_coverage(base: Path, intent: str) -> None:
    """初始化 coverage/ 三件套（骨架）。

    覆盖单元与维度由项目按需补全；这里只保证 r04 门禁有据可查：
    页数下限 21、来源账本由 collect 回填。
    """
    import datetime
    import hashlib
    from core import coverage_plan

    cov = base / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    task_id = (datetime.date.today().isoformat() + "-"
               + hashlib.sha256(intent.encode("utf-8")).hexdigest()[:8])
    frame = {
        "schema": "dsh.task_frame/v1",
        "task_id": task_id,
        "brief": intent,
        "decision": {"question": intent, "type": "inferred"},
        "units": [],
        "dimensions": [],
        "maps": [],
        "depth": {"core_units": []},
    }
    plan = coverage_plan.build(frame, [], 21, [], [])
    (cov / "task_frame.json").write_text(
        json.dumps(frame, ensure_ascii=False, indent=2), encoding="utf-8")
    (cov / "coverage_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    ledger = cov / "source_ledger.json"
    if not ledger.exists():
        ledger.write_text(json.dumps({"sources": []}, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def write_cards(intent: str, out_dir: str, only: List[str] | None = None) -> Dict[str, Any]:
    """按名册给每个可进报告的角色发一张任务卡。"""
    from core import research_protocol, roster

    base = Path(out_dir)
    cards = base / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    brief = research_protocol.plan(intent)
    (base / "brief.md").write_text(research_protocol.to_markdown(brief),
                                   encoding="utf-8")
    (base / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    _write_coverage(base, intent)

    rb = roster.build()
    written = []
    for rid, r in rb["roles"].items():
        if not r["enters_report"]:
            continue
        if only and rid not in only:
            continue
        d = cards / rid
        d.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# 任务卡：{rid} {r['name']}（{r['title']}）",
            "",
            f"- 总任务：{intent}",
            f"- 数据通道：**{brief['data_lane']}** —— {brief['lane_note']}",
            f"- 你负责：{', '.join(r['capabilities'][:4])}",
            f"- 可用技能：{', '.join(r['skills'][:12]) or '（无）'}",
            f"- 可用动作：{', '.join(a['label'] for a in r['actions'][:8]) or '（无）'}",
            "",
            "## 你要判断什么（自己定，不要等我给）",
            "",
            "从你的专业出发，回答这个问题里**只有你能回答**的部分。"
            "答不了就写进 missing，不要编。",
            "",
            "## 交什么",
            "",
            f"写到 `{d.as_posix()}/claims.json`，格式见 `brief.md` 的「一条结论必须长这样」，",
            "最少包含：numbers / sources / sections（每节 title 带数字、≥2 条解读、带 refs、带 falsifier）。",
            "",
            "## 交数据的要求（决定图上能不能画出来）",
            "",
            "- 每个判断至少 **3 个可比点**（不同规格 / 地区 / 期次 / 主体）",
            "- 价格类：给完整阶梯（产地 → 出厂 → 批发 → 零售），不要只给一个价",
            "- 趋势类：至少 4 期；不足 4 期就不要写趋势结论",
            "- 同一指标有区间就给上下限，别只给中位数",
            "- 2 个点画不成图，报告会退成表格——这是丢分项",
            "",
            "## 来源要求（缺一条，整张卡拒收）",
            "",
            "- 每条 source 必须带 `url`（http/https）、`date`（YYYY 或 YYYY-MM-DD）、`quote`（原文片段 ≥12 字）",
            "- 每个数字必须指向本卡的某个 `source_file`；指向不存在的来源，整卡拒收",
            "- 只填域名首页、检索页、没有原文片段的，一律算没查",
            "- 同一指标两个数，必须在 conflicts 里写清口径差",
            "",
            "## 边界",
            "",
            "- 只用公开可核来源；查不到写 missing",
        ]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "role": rid,
            "numbers": [{"id": "N1", "name": "", "value": 0, "unit": "",
                         "period": "", "source_file": "S1"}],
            "sources": [{"file": "S1", "title": "", "org": "", "url": "",
                         "date": "", "grade": "A", "quote": ""}],
            "conflicts": [],
            "sections": [{"title": "…（含数字）", "question": "对谁做决定有用",
                          "refs": ["N1"],
                          "reading": [{"text": "观察：…", "refs": ["N1"]},
                                      {"text": "机理：判别方法是…", "refs": ["N1"]}],
                          "falsifier": "若…超过 X% 则本节作废"}],
            "missing": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(rid)
    return {"ok": True, "cards": len(written), "roles": written,
            "brief": str(base / "brief.md")}


def _coverage_gaps(base: Path) -> Dict[str, Any]:
    """从 coverage/ 三件套读缺口：缺哪些单元×维度、哪些地图没画、页数差多少。"""
    cov = base / "coverage"
    frame_p, plan_p = cov / "task_frame.json", cov / "coverage_plan.json"
    if not frame_p.is_file() or not plan_p.is_file():
        return {}
    try:
        frame = json.loads(frame_p.read_text(encoding="utf-8-sig"))
        plan = json.loads(plan_p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    cells = plan.get("cells") or []
    missing = [f"{c.get('unit')}×{c.get('dimension')}"
               for c in cells if c.get("status") == "missing"]
    estimated = [f"{c.get('unit')}×{c.get('dimension')}"
                 for c in cells if c.get("status") == "estimated"]
    need_maps = [m.get("level") for m in frame.get("maps") or []
                 if m.get("required", True)]
    have_maps = plan.get("maps") or []
    return {
        "units": len(frame.get("units") or []),
        "core_units": plan.get("core_units") or [],
        "cells": len(cells),
        "missing_count": len(missing),
        "missing_cells": missing[:80],
        "estimated_count": len(estimated),
        "estimated_cells": estimated[:80],
        "maps_required": need_maps,
        "maps_have": have_maps,
        "maps_missing": [m for m in need_maps if m not in have_maps],
        "page_estimate": plan.get("page_estimate"),
        "page_floor": plan.get("page_floor") or frame.get("page_floor"),
    }


def collect(out_dir: str, require_all: bool = False,
            min_sources: int = 0, verify_quotes: bool = False,
            strict_verify: bool = False, fetch=None) -> Tuple[Dict[str, Any], List[str]]:
    """收到各角色的 claims，验完整性后合并成一份。

    覆盖门禁（2026-11-19 体检补）：发出去的卡（有 TASK.md 的目录）与实际交回
    claims.json 的卡必须对得上。缺卡默认只记录在 `merged["coverage"]`；
    `require_all=True` 时缺卡进 problems（CLI 默认严格，`--allow-partial` 放行）。

    证据门禁（2026-11-19 补）：
    - 每条 source 必须有 url/date/quote；缺 quote 的卡拒收（见 `_need`）；
    - `min_sources` 是来源条数下限（CLI 默认 50，`--min-sources 0` 关闭）；
    - `verify_quotes=True` 时才联网回抓；`strict_verify=True` 时未核过即失败；
    - 缺口清单写进 `merged["gaps"]`：缺单元×维度、缺地图、页数差、来源缺口。
    """
    base = Path(out_dir) / "cards"
    merged: Dict[str, Any] = {"numbers": [], "sources": [], "sections": [],
                              "conflicts": [], "missing": [], "boundaries": [],
                              "derived": []}
    seen_n: Dict[str, Dict[str, Any]] = {}
    seen_s: set = set()
    bad: List[str] = []
    rejected: List[Dict[str, Any]] = []
    got = 0
    expected = sorted(d.name for d in base.glob("*")
                      if d.is_dir() and (d / "TASK.md").is_file()
                      and not d.name.startswith("_"))
    delivered: List[str] = []

    for d in sorted(p for p in base.glob("*") if p.is_dir()):
        f = d / "claims.json"
        if not f.is_file():
            continue
        got += 1
        delivered.append(d.name)
        try:
            c = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            bad.append(f"{d.name}: claims.json 解析失败")
            continue
        miss = _need(c)
        if miss:
            bad.append(f"{d.name}: " + "；".join(miss[:3]))
            rejected.append({"role": d.name, "reasons": miss[:6]})
            continue
        for n in c.get("numbers") or []:
            nid = str(n.get("id") or "")
            key = f"{d.name}:{nid}"
            n = dict(n, id=key,
                     source_file=f"{d.name}:{n.get('source_file') or 'S?'}")
            if key not in seen_n:
                seen_n[key] = n
                merged["numbers"].append(n)
        # 派生量：id 与公式一起加本卡命名空间，否则合并后 refs 找不到
        import re as _re
        local_ids = {str(n.get("id")) for n in (c.get("numbers") or [])}
        local_ids |= {str(x.get("id")) for x in (c.get("derived") or [])}
        for dv in c.get("derived") or []:
            dv = dict(dv)
            formula = str(dv.get("formula") or "")
            formula = _re.sub(r"[A-Za-z_][A-Za-z0-9_]*",
                              lambda m: (f"{d.name}:{m.group(0)}"
                                         if m.group(0) in local_ids else m.group(0)),
                              formula)
            dv["formula"] = formula
            dv["id"] = f"{d.name}:{dv.get('id')}"
            merged["derived"].append(dv)
        for s in c.get("sources") or []:
            s = dict(s)
            s["file"] = f"{d.name}:{s.get('file')}"
            if s["file"] not in seen_s:
                seen_s.add(s["file"])
                merged["sources"].append(s)
        # 节次与 refs 都要重写成本卡命名空间
        for sec in c.get("sections") or []:
            sec = json.loads(json.dumps(sec))
            sec["refs"] = [f"{d.name}:{r}" for r in (sec.get("refs") or [])]
            for rd in sec.get("reading") or []:
                rd["refs"] = [f"{d.name}:{r}" for r in (rd.get("refs") or [])]
            ch = sec.get("chart") or {}
            if ch:
                # 智能体产出的图按「报告级」验收：必须有基线、有标注。
                ch["report_grade"] = True
            if ch.get("refs"):
                ch["refs"] = [f"{d.name}:{r}" for r in ch["refs"]]
            merged["sections"].append(sec)
        for b in c.get("boundaries") or []:
            merged["boundaries"].append(f"[{d.name}] {b}")
        for m in c.get("missing") or []:
            merged["missing"].append(f"{d.name}: {m}")
        for conf in c.get("conflicts") or []:
            merged["conflicts"].append(conf)

    merged["boundaries"] = list(dict.fromkeys(
        merged["boundaries"] + [f"{m}" for m in merged["missing"]]))

    # 证据面：来源字段齐不齐、数字与节够不够；缺 quote 的卡已在上面拒收。
    from core import source_verify
    src = merged["sources"]
    fields_ok = sum(1 for s in src if not source_verify.check_fields(s))
    merged["evidence"] = {
        "sources": len(src),
        "sources_fields_ok": fields_ok,
        "numbers": len(merged["numbers"]),
        "sections": len(merged["sections"]),
        "quote_rate": round(fields_ok / len(src), 3) if src else 0.0,
        "min_sources": int(min_sources),
    }
    merged["source_verify"] = {}
    if verify_quotes:
        vr = source_verify.verify_sources(
            src, fetch=fetch or source_verify.default_fetch)
        merged["source_verify"] = {
            "ok": vr["ok"], "total": vr["total"], "verified": vr["verified"],
            "counts": vr["counts"], "rows": vr["rows"][:300],
        }
        if strict_verify:
            pending = [r["id"] for r in vr["rows"] if r["status"] != "verified"]
            if pending:
                bad.append(f"回抓未通过 {len(pending)}/{vr['total']}："
                           + "、".join(pending[:10]))
    if min_sources and len(src) < int(min_sources):
        bad.append(f"来源 {len(src)} 条，低于门槛 {min_sources}；"
                   "补采后重跑，或 `--min-sources 0` 关闭")

    # 覆盖门禁：发了卡却没交、或交了但被拒的，都要能一眼看出来
    missing_cards = [r for r in expected if r not in delivered]
    merged["coverage"] = {
        "expected": len(expected), "delivered": len(delivered),
        "missing": missing_cards, "rejected": rejected,
        "rate": round(len(delivered) / len(expected), 3) if expected else 0.0,
    }
    gaps = _coverage_gaps(Path(out_dir))
    if min_sources:
        gaps["source_shortfall"] = max(0, int(min_sources) - len(src))
    merged["gaps"] = gaps
    if require_all and missing_cards:
        bad.append("缺卡 " + str(len(missing_cards)) + "/" + str(len(expected)) + "："
                   + "、".join(missing_cards) + "（发了卡但没交 claims.json）")
    # 导语必须是带数字的结论：取第一节标题（契约要求标题即结论且含数字）
    if merged["sections"]:
        merged["standfirst"] = str(merged["sections"][0].get("title") or "")
    merged["meta"] = {"title": "自动汇编报告",
                      "doc_type": "调研报告", "intent": "", "profile": "baseline"}
    return merged, (bad + ([] if got else ["一张 claims 都没收到"]))
