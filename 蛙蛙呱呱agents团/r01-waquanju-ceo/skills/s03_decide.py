# -*- coding: utf-8 -*-
"""S03 经营与硬决策 —— 能力域 3。

整合自 c-level-agents 的 decide / hard-call / cross-eval / freeze。
核心主张：按可逆性分级、先求尽调更高 bar、不可逆必须你授权。
  reversibility  可逆性三级分级（关键词 + 撤回成本 + 决策前五问）
  card           决策卡门禁（10/10/10 + 预公告测试 + 回滚计划）
  escalate       升级判定（不可逆/高成本/董事会拆分/推翻共识 → 人工签发）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "decide"
DESC = "经营与硬决策：reversibility/card/escalate"

_BEFORE_DECIDE = [
    "最弱假设是什么？",
    "证据是否可复现？",
    "谁为这个决定的失败负责？",
    "撤回成本是多少？",
    "是否把可逆决策当成不可逆在拖延（是=逃避）？",
]


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("reversibility", "可逆性三级分级 + 决策前五问"),
                 ("card", "决策卡门禁（回滚计划/成功杀死标准）"),
                 ("escalate", "升级判定（何时必须人工签发）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"reversibility": _reversibility, "card": _card,
          "escalate": _escalate}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _grade_reversibility(topic: str) -> str:
    t = c.load_thresholds()["decide"]
    if any(k in topic for k in t["irreversible_keywords"]):
        return "不可逆"
    if any(k in topic for k in t["hard_keywords"]):
        return "难逆"
    if any(k in topic for k in t["reversible_keywords"]):
        return "可逆"
    return "可逆"


def _reversibility(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["decide"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}
    topic = str(data.get("topic", ""))
    checks.append(_ck(bool(topic), "决策主题非空", "decide.topic"))

    level = data.get("reversibility") or _grade_reversibility(topic)
    checks.append(_ck(level in t["levels"], f"可逆性={level}", "decide.level"))

    cost = {"可逆": "低", "难逆": "中", "不可逆": "高"}[level]
    action = {"不可逆": "需你最终授权，禁止自动执行",
              "难逆": "加人工审批点",
              "可逆": "可授权角色快速执行"}[level]

    answers = data.get("before_decide_answers") or {}
    for q in _BEFORE_DECIDE[:4]:
        checks.append(_ck(bool(answers.get(q)),
                          f"决策前五问已答：{q}", "decide.before_decide"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "topic": topic, "reversibility": level,
            "cost_if_wrong": cost, "action": action,
            "before_decide": _BEFORE_DECIDE, "checks": checks}


def _card(data: Any) -> Dict[str, Any]:
    """决策卡门禁：选项≥2（什么都不做也是选项）；不可逆必须有回滚计划；
    成功/杀死标准先于决策；预公告测试立得住。"""
    t = c.load_thresholds()["decide"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    for f in t["card_fields"]:
        checks.append(_ck(bool(data.get(f)), f"决策卡含 {f}", f"card.{f}"))

    options = data.get("options") or []
    checks.append(_ck(len(options) >= t.get("options_min", 2)
                      if "options_min" in t else len(options) >= 2,
                      "选项 ≥2（「什么都不做」永远是选项之一）", "card.options"))

    level = data.get("reversibility", "")
    checks.append(_ck(level in t["levels"], f"可逆性分级合法（{level}）",
                      "card.reversibility"))
    if level == "不可逆" and not data.get("rollback_plan"):
        checks.append(_ck(False, "不可逆决策缺回滚/失败预案", "card.rollback",
                          "CRITICAL"))

    for key in ("success_criteria", "kill_criteria"):
        items = data.get(key) or []
        well = (isinstance(items, list) and items
                and all(isinstance(x, dict) and x.get("metric")
                        and x.get("threshold") is not None for x in items))
        checks.append(_ck(well, f"{key} 含 metric+threshold（决策前定）",
                          f"card.{key}"))

    # 预公告测试：先写出公告信「我们做这个决定是因为……」——立不住=没准备好
    checks.append(_ck(bool(data.get("announcement_draft")),
                      "预公告测试：公告信草稿已写（立不住=没准备好）",
                      "card.preannouncement"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "reversibility": level, "card_fields": t["card_fields"],
            "checks": checks}


def _escalate(data: Any) -> Dict[str, Any]:
    """升级判定：不可逆 / 反转成本>6个月公司时间 / 拆分董事会投票 /
    gut-feel 推翻顾问一致 → 必须人工签发。"""
    t = c.load_thresholds()["decide"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    level = data.get("reversibility") or "可逆"
    months = data.get("rollback_cost_months") or 0
    board_split = bool(data.get("board_vote_split"))
    gut_override = bool(data.get("overrides_consensus"))

    reasons = []
    if level == "不可逆":
        reasons.append("不可逆（单向门）")
    if months > t["escalate_cost_months"]:
        reasons.append(f"反转成本 {months} 个月 > {t['escalate_cost_months']} 个月公司时间")
    if board_split:
        reasons.append("董事会投票拆分")
    if gut_override:
        reasons.append("gut-feel 推翻顾问一致意见")

    must = bool(reasons)
    declared = bool(data.get("human_signoff_required"))
    checks.append(_ck(declared == must,
                      f"人工签发判定正确（应为 {must}）"
                      + (f"：{reasons}" if reasons else "：可授权角色执行"),
                      "escalate.signoff"))
    if must and not declared:
        checks.append(_ck(False, "该决策必须升级人工签发，未声明", "escalate.missed",
                          "CRITICAL"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "must_escalate": must, "reasons": reasons,
            "human_signoff_required": must,
            "rule": f"反转成本 > {t['escalate_cost_months']} 个月公司时间 → 升级 cross-eval + 人工",
            "checks": checks}
