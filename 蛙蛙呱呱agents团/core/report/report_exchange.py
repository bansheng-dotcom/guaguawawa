# -*- coding: utf-8 -*-
"""core.report.report_exchange —— 卡间协商（一集散卡，角色之间互相要数据）。

2026-11-20 的 6 张卡是"同一张卡印 6 份"：互相不知道对方存在，也不知道自己
接在谁后面。用户要的是「系统有组织协调能力，让他们交互起来」。

这里的做法不是让模型自己聊天，而是给一条**可校验的协商协议**：

    cards/<A>/needs.json      A 说：我缺 B 的某样东西（id / to / what / why）
    report exchange           把 A 的请求投到 cards/<B>/INBOX.md
    cards/<B>/answers.json    B 回：need=A:N1，带 value + source_file（或 declined+原因）
    collect                   每个 need 必须 answered 或 declined，open 的不收

协调不靠 R01 传话：谁向谁要了什么、给没给、为什么没给，全在文件里。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "dsh.report.exchange/v1"


def _load(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def scan(base: str) -> Dict[str, Any]:
    """收集全部 needs 与 answers，按 need id 对齐。"""
    root = Path(base) / "cards"
    needs: List[Dict[str, Any]] = []
    answers: Dict[str, Dict[str, Any]] = {}
    for d in sorted(p for p in root.glob("*") if p.is_dir()):
        role = d.name
        for n in (_load(d / "needs.json").get("needs") or []):
            if not str(n.get("what") or "").strip():
                continue  # 空模板不算需求
            needs.append({
                "id": f"{role}:{n.get('id') or 'N?'}",
                "from": role, "to": str(n.get("to") or ""),
                "what": str(n.get("what") or ""), "why": str(n.get("why") or ""),
                "status": str(n.get("status") or "open"),
            })
        for a in (_load(d / "answers.json").get("answers") or []):
            key = str(a.get("need") or "")
            # 空壳回答不算回答：要么有值，要么明确 declined + 原因
            said = str(a.get("value") or "").strip() or str(a.get("quote") or "").strip()
            if not key or not (said or a.get("declined")):
                continue
            answers[key] = {**a, "by": role}
    for n in needs:
        a = answers.get(n["id"])
        if a:
            n["status"] = "declined" if a.get("declined") else "answered"
            n["answer"] = a
    return {"schema": SCHEMA, "needs": needs,
            "answers": list(answers.values()),
            "counts": {
                "total": len(needs),
                "answered": sum(1 for n in needs if n["status"] == "answered"),
                "declined": sum(1 for n in needs if n["status"] == "declined"),
                "open": sum(1 for n in needs if n["status"] == "open"),
            }}


def route(base: str) -> Dict[str, Any]:
    """把 open 的 needs 投递到对方 INBOX.md；返回投递结果。"""
    root = Path(base) / "cards"
    data = scan(base)
    by_to: Dict[str, List[Dict[str, Any]]] = {}
    for n in data["needs"]:
        if n["status"] != "open":
            continue
        if not n["to"]:
            continue
        by_to.setdefault(n["to"], []).append(n)
    for to, items in by_to.items():
        d = root / to
        d.mkdir(parents=True, exist_ok=True)
        L = [f"# INBOX：{to} 收到的数据请求", ""]
        for n in items:
            L += [f"## {n['id']}（来自 {n['from']}）", "",
                  f"- 要什么：{n['what']}", f"- 为什么：{n['why'] or '-'}",
                  f"- 回法：写 `cards/{to}/answers.json`，"
                  f"`need` 填 `{n['id']}`；给不了就 `declined: true` + 原因", ""]
        (d / "INBOX.md").write_text("\n".join(L), encoding="utf-8")
    return {"ok": True, "routed": {k: len(v) for k, v in by_to.items()},
            "counts": data["counts"],
            "open": [n["id"] for n in data["needs"] if n["status"] == "open"]}


def verify(base: str) -> Dict[str, Any]:
    """收卡前的协商闭环检查：open 的 need 就是没闭环。"""
    data = scan(base)
    open_needs = [n for n in data["needs"] if n["status"] == "open"]
    return {"ok": not open_needs, "counts": data["counts"],
            "open": [{"id": n["id"], "to": n["to"], "what": n["what"]}
                     for n in open_needs],
            "resolved": [n for n in data["needs"] if n["status"] != "open"]}


def render_md(base: str) -> str:
    data = scan(base)
    c = data["counts"]
    L = ["# 卡间协商台账", "",
         f"- 需求 {c['total']} 条：answered {c['answered']} / "
         f"declined {c['declined']} / **open {c['open']}**", ""]
    if data["needs"]:
        L += ["| 需求 | 发起 | 要找 | 要什么 | 状态 |", "|---|---|---|---|---|"]
        for n in data["needs"]:
            L.append(f"| {n['id']} | {n['from']} | {n['to'] or '-'} | "
                     f"{n['what']} | {n['status']} |")
    else:
        L.append("这一轮没有任何跨角色请求——如果角色之间真的没有依赖，"
                 "要么任务太浅，要么没人认真想过缺什么。")
    return "\n".join(L)
