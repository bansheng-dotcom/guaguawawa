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
    """一张卡最少要有什么。"""
    miss = []
    if not claims.get("numbers"):
        miss.append("numbers（没有数字就是没查）")
    if not claims.get("sources"):
        miss.append("sources（没有来源就是没查）")
    if not claims.get("sections"):
        miss.append("sections（没有判断就是没写）")
    for s in claims.get("sections") or []:
        t = str(s.get("title") or "")
        if not s.get("refs"):
            miss.append(f"节「{t}」缺 refs")
        if len([r for r in (s.get("reading") or []) if r.get("text")]) < 2:
            miss.append(f"节「{t}」解读少于 2 条")
        if not s.get("falsifier"):
            miss.append(f"节「{t}」缺证伪条件")
    return miss


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
            "## 边界",
            "",
            "- 只用公开可核来源；查不到写 missing",
            "- 同一指标两个数，必须在 conflicts 里写清口径差",
        ]
        (d / "TASK.md").write_text("\n".join(lines), encoding="utf-8")
        (d / "claims.template.json").write_text(json.dumps({
            "role": rid,
            "numbers": [{"id": "N1", "name": "", "value": 0, "unit": "",
                         "period": "", "source_file": "S1"}],
            "sources": [{"file": "S1", "title": "", "org": "", "url": "",
                         "grade": "A", "quote": ""}],
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


def collect(out_dir: str) -> Tuple[Dict[str, Any], List[str]]:
    """收到各角色的 claims，验完整性后合并成一份。"""
    base = Path(out_dir) / "cards"
    merged: Dict[str, Any] = {"numbers": [], "sources": [], "sections": [],
                              "conflicts": [], "missing": [], "boundaries": [],
                              "derived": []}
    seen_n: Dict[str, Dict[str, Any]] = {}
    seen_s: set = set()
    bad: List[str] = []
    got = 0

    for d in sorted(p for p in base.glob("*") if p.is_dir()):
        f = d / "claims.json"
        if not f.is_file():
            continue
        got += 1
        try:
            c = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            bad.append(f"{d.name}: claims.json 解析失败")
            continue
        miss = _need(c)
        if miss:
            bad.append(f"{d.name}: " + "；".join(miss[:3]))
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
    # 导语必须是带数字的结论：取第一节标题（契约要求标题即结论且含数字）
    if merged["sections"]:
        merged["standfirst"] = str(merged["sections"][0].get("title") or "")
    merged["meta"] = {"title": "自动汇编报告",
                      "doc_type": "调研报告", "intent": "", "profile": "baseline"}
    return merged, (bad + ([] if got else ["一张 claims 都没收到"]))
