# -*- coding: utf-8 -*-
"""W5 briefing：项目理解 → 选项/利弊 → 建议 → 归档。

门禁：
  - 不代决策：必须写明决策人（decision_owner，且不能是本角色），只给建议，
    禁止「我决定 / 最终决定 / 就这么定 / 拍板」等代决策措辞；
  - 至少 2 个选项，每个选项有利有弊；
  - 有回链：至少 1 条上游工件回链（kind + ref），归档才成立。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c

STAGE = "briefing"
ARTIFACT = "briefing_pack"

_DECISION_WORDS = ("我决定", "最终决定", "就这么定", "拍板", "定稿执行")
_SELF_ROLES = ("r07", "蛙得明", "产品经理", "pm")


def _list_of_dicts(raw: Any) -> List[Dict[str, Any]]:
    return [x for x in (raw if isinstance(raw, list) else []) if isinstance(x, dict)]


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    options = _list_of_dicts(data.get("options"))
    rec = data.get("recommendation") if isinstance(data.get("recommendation"), dict) else {}
    links = _list_of_dicts(data.get("backlinks"))
    checks: List[Dict[str, Any]] = []

    # ---------- 1. 项目理解 ----------
    for key, label in (("name", "项目名"), ("background", "背景"), ("goals", "目标"),
                       ("current_state", "现状"), ("constraints", "约束")):
        checks.append(c.ck(not c.blank(project.get(key)),
                           f"项目理解缺少{label}（project.{key}）",
                           f"project.{key}", "BLOCKER"))
    stakeholders = project.get("stakeholders")
    stakeholders = stakeholders if isinstance(stakeholders, list) else []
    checks.append(c.ck(bool([s for s in stakeholders if not c.blank(s)]),
                       "项目理解缺少干系人（project.stakeholders）",
                       "project.stakeholders", "BLOCKER"))

    # ---------- 2. 选项 / 利弊 ----------
    checks.append(c.ck(len(options) >= 2,
                       f"选项 {len(options)} 个 < 2 个，汇报无法比较",
                       "options.count", "BLOCKER"))
    for idx, opt in enumerate(options):
        checks.append(c.ck(not c.blank(opt.get("name")),
                           f"选项 {idx} 缺少名称", "options.name", "BLOCKER"))
        checks.append(c.ck(not c.blank(opt.get("description")),
                           f"选项 {idx} 缺少说明", "options.description", "BLOCKER"))
        pros = opt.get("pros")
        cons = opt.get("cons")
        checks.append(c.ck(bool([p for p in (pros or []) if not c.blank(p)]),
                           f"选项 {idx} 缺少利（pros）", "options.pros", "BLOCKER"))
        checks.append(c.ck(bool([x for x in (cons or []) if not c.blank(x)]),
                           f"选项 {idx} 缺少弊（cons）", "options.cons", "BLOCKER"))

    # ---------- 3. 建议（不代决策） ----------
    checks.append(c.ck(not c.blank(rec.get("rationale")),
                       "缺少建议理由（recommendation.rationale）",
                       "recommendation.rationale", "BLOCKER"))
    owner = str(rec.get("decision_owner") or "").strip()
    checks.append(c.ck(bool(owner), "缺少决策人（recommendation.decision_owner）",
                       "recommendation.decision_owner", "BLOCKER"))
    checks.append(c.ck(owner.lower() not in _SELF_ROLES,
                       f"决策人不能是本角色：{owner!r}", "recommendation.decision_owner",
                       "BLOCKER"))
    text = " ".join(str(rec.get(k) or "") for k in ("summary", "rationale", "statement"))
    checks.append(c.ck(not any(w in text for w in _DECISION_WORDS),
                       "汇报出现代决策措辞（只允许给选项与建议）",
                       "recommendation.no_decision", "BLOCKER"))
    questions = rec.get("open_questions")
    questions = questions if isinstance(questions, list) else []
    checks.append(c.ck(bool([q for q in questions if not c.blank(q)]),
                       "缺少待决策问题（recommendation.open_questions）",
                       "recommendation.open_questions", "BLOCKER"))

    # ---------- 4. 回链与归档 ----------
    checks.append(c.ck(bool(links), "缺少回链（backlinks）", "backlink", "BLOCKER"))
    for idx, link in enumerate(links):
        checks.append(c.ck(not c.blank(link.get("kind")) and not c.blank(link.get("ref")),
                           f"回链 {idx} 缺少 kind/ref", "backlink", "BLOCKER"))

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "project": project,
        "options": options,
        "recommendation": rec,
        "backlinks": links,
        "archive": {"recorded": bool(g["ok"]), "format": "json",
                    "links": links},
        "gate": g,
    }
