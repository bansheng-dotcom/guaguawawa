# -*- coding: utf-8 -*-
"""S06 决策留痕与复盘 —— 能力域 6。

整合自 c-level-agents decision-logger（两层记忆 + DO_NOT_RESURFACE）+ 复盘闭环。
核心主张：已批准层 append-only；被否提案重提=BLOCKED；复盘只对预承诺标准打分。
  entry     决策日志条目门禁（决策/Owner/Deadline/理由/否弃/待办）
  conflict  写前冲突检查（DO_NOT_RESURFACE 违规/同主题矛盾/归属歧义）
  retro     复盘（预承诺标准打分 WIN/PARTIAL/LOSS/MIXED + 回访异议）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "decisionlog"
DESC = "决策留痕与复盘：entry/conflict/retro"


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("entry", "决策日志条目门禁"),
                 ("conflict", "写前冲突检查（DO_NOT_RESURFACE）"),
                 ("retro", "复盘门禁（预承诺标准打分）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"entry": _entry, "conflict": _conflict, "retro": _retro}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _entry(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["decisionlog"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    for f in t["entry_fields"]:
        checks.append(_ck(bool(data.get(f)), f"日志条目含 {f}", f"log.{f}"))

    rejected = data.get("rejected") or []
    for i, r in enumerate(rejected):
        checks.append(_ck(bool(r.get("proposal")) and bool(r.get("reason")),
                          f"否弃[{i}] 带提案+原因", f"log.rejected.{i}"))

    todos = data.get("todos") or []
    for i, td in enumerate(todos):
        checks.append(_ck(bool(td.get("item")) and bool(td.get("owner"))
                          and bool(td.get("due")),
                          f"待办[{i}] 带 item+owner+due", f"log.todos.{i}"))

    # 理由 = 为何胜过替代（不是复述结论）
    rationale = str(data.get("rationale", ""))
    checks.append(_ck(len(rationale) >= 10 and rationale != str(data.get("decision", "")),
                      "理由回答「为何胜过替代」（非复述决策）", "log.rationale"))

    # 两层记忆：本条目必须落在已批准层（append-only），未决之争禁止回灌
    checks.append(_ck(data.get("layer") in (None, "approved"),
                      "条目属已批准层（原始议事录永不自动回灌）", "log.layer"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "entry_fields": t["entry_fields"], "checks": checks}


def _conflict(data: Any) -> Dict[str, Any]:
    """写前必查冲突：①DO_NOT_RESURFACE 违规（被否提案重提→BLOCKED）
    ②同主题结论矛盾 ③动作归属歧义。"""
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    proposed = data.get("proposed") or {}
    existing = data.get("existing_entries") or []
    topic = str(proposed.get("title", "")).strip()

    # ① DO_NOT_RESURFACE 违规
    dns_hits = []
    for e in existing:
        same_topic = topic and topic in str(e.get("title", ""))
        for r in (e.get("rejected") or []):
            if same_topic and r.get("do_not_resurface") and \
                    str(r.get("proposal", "")) in str(proposed.get("decision", "")):
                dns_hits.append(str(r.get("proposal")))
    checks.append(_ck(not dns_hits,
                      "无 DO_NOT_RESURFACE 违规" +
                      (f"（被否提案重提: {dns_hits}）" if dns_hits else ""),
                      "conflict.dns", "" if not dns_hits else "CRITICAL"))

    # ② 同主题结论矛盾
    contradictions = []
    for e in existing:
        if topic and topic in str(e.get("title", "")):
            if str(e.get("decision", "")) and \
                    str(e.get("decision", "")) != str(proposed.get("decision", "")):
                contradictions.append(e.get("title"))
    resolved = bool(proposed.get("supersedes"))
    checks.append(_ck(not contradictions or resolved,
                      "同主题结论矛盾已用 supersedes 声明" +
                      (f"（冲突: {contradictions}）" if contradictions and not resolved
                       else ""),
                      "conflict.contradiction"))

    # ③ 动作归属歧义：同 owner 同期两个矛盾待办
    todos = proposed.get("todos") or []
    owner_actions: Dict[str, List[str]] = {}
    for td in todos:
        owner_actions.setdefault(td.get("owner", "?"), []).append(
            str(td.get("action", td.get("item", ""))))
    ambiguous = [o for o, acts in owner_actions.items() if len(acts) != len(set(acts))]
    checks.append(_ck(not ambiguous,
                      "待办无归属歧义" + (f"（歧义: {ambiguous}）" if ambiguous else ""),
                      "conflict.ambiguity"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "dns_hits": dns_hits,
            "contradictions": contradictions, "checks": checks}


def _retro(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["decisionlog"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    trigger = data.get("trigger", "")
    checks.append(_ck(trigger in t["retro_triggers"],
                      f"复盘触发合法（{trigger}）", "retro.trigger"))

    grades = data.get("grades") or []
    checks.append(_ck(bool(grades), "对预承诺标准逐条打分", "retro.grades"))
    for i, g in enumerate(grades):
        checks.append(_ck(g.get("grade") in t["retro_grades"],
                          f"标准[{g.get('criterion', i)}] 打分合法"
                          f"（{g.get('grade')}）", f"retro.{i}.grade"))
        checks.append(_ck(bool(g.get("pre_committed")),
                          f"标准[{g.get('criterion', i)}] 为决策前预承诺"
                          "（事后补的标准不可打分）", f"retro.{i}.pre_committed"))

    checks.append(_ck(bool(data.get("dissent_reviewed")),
                      "已回访被保留的异议", "retro.dissent"))
    checks.append(_ck(bool(data.get("assumption_audit")),
                      "假设审计完成", "retro.assumptions"))

    # LOSS 必须闭环：新增 boardroom 或 brief
    has_loss = any(g.get("grade") == "LOSS" for g in grades)
    follow_up = bool(data.get("new_boardroom") or data.get("new_brief"))
    checks.append(_ck((not has_loss) or follow_up,
                      "LOSS 触发新 boardroom/brief" if has_loss
                      else "无 LOSS 项", "retro.loss_followup",
                      "" if ((not has_loss) or follow_up) else "CRITICAL"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "trigger": trigger, "has_loss": has_loss,
            "retro_grades": t["retro_grades"], "checks": checks}
