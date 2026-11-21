# -*- coding: utf-8 -*-
"""core.intake —— R01 接活：12 问 + brief + 用户签字。

规则（SOP v5）：
    少于 10 个有效回答 → 不许拆卡；
    brief 未签字 → report_dispatch.issue 拒绝发卡；
    签字动作由 `report brief --plan --confirm` 触发（--confirm 即用户确认）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

QUESTIONS: List[Dict[str, str]] = [
    {"id": "I1", "group": "问题", "text": "你要解决的真问题是什么（不是“做个调研”）？"},
    {"id": "I2", "group": "问题", "text": "这份东西支持哪个决定？谁拍板？"},
    {"id": "I3", "group": "问题", "text": "不做会怎样？不做也可以的话，为什么要做？"},
    {"id": "I4", "group": "问题", "text": "成功长什么样？三个月后什么算这活干成了？"},
    {"id": "I5", "group": "上下文", "text": "现在手上已有哪些数据/结论/报告？"},
    {"id": "I6", "group": "上下文", "text": "你所在行业/区域有什么硬约束（监管、渠道、预算）？"},
    {"id": "I7", "group": "上下文", "text": "竞争对手或对标是谁？你更想赢哪一点？"},
    {"id": "I8", "group": "上下文", "text": "时间、预算、人手各是什么量级？"},
    {"id": "I9", "group": "交付", "text": "你最想要哪 3 个判断？最不想要什么？"},
    {"id": "I10", "group": "交付", "text": "报告给谁看？他习惯什么格式（一页纸/长报告/PPT）？"},
    {"id": "I11", "group": "交付", "text": "口径有偏好吗（全国/区域、平台/统计、含税/不含）？"},
    {"id": "I12", "group": "交付", "text": "哪些结论不能出现（合规、政治、内部敏感）？"},
]

MIN_ANSWERS = 10


def _w(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _r(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def start(project: Path, intent: str) -> Dict[str, Any]:
    project = Path(project)
    intake = {
        "schema": "dsh.intake/v1",
        "intent": intent,
        "questions": QUESTIONS,
        "answers": {},
        "status": "pending",
        "min_answers": MIN_ANSWERS,
    }
    _w(project / "intake.json", intake)
    brief = {
        "schema": "dsh.brief/v1",
        "problem": "",
        "decision": "",
        "audience": "",
        "success": "",
        "scope": {"in": [], "out": []},
        "panel_plan": [],
        "challenges": [],
        "signed": None,
    }
    _w(project / "brief.json", brief)
    return {"ok": True, "intake": str(project / "intake.json"),
            "questions": len(QUESTIONS), "min_answers": MIN_ANSWERS}


def answer(project: Path, pairs: List[str], by: str = "user") -> Dict[str, Any]:
    """pairs: I1=... I2=...

    `by` 记录答案是谁给的（2026-11-22）：只有 user 才算用户确认；
    agent 代填会留在 answered_by 里，preflight/签 brief 都不认。
    """
    project = Path(project)
    intake = _r(project / "intake.json") or {}
    answers = intake.get("answers") or {}
    by_map = intake.get("answered_by") or {}
    by = "user" if str(by).lower() == "user" else "agent"
    for p in pairs:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip().upper()
        if any(q["id"] == k for q in QUESTIONS) and v.strip():
            answers[k] = v.strip()
            by_map[k] = by
    intake["answers"] = answers
    intake["answered_by"] = by_map
    user_n = sum(1 for k in answers if by_map.get(k) == "user")
    intake["user_answers"] = user_n
    ok_count = len(answers)
    intake["status"] = ("complete" if ok_count >= MIN_ANSWERS and user_n >= MIN_ANSWERS
                        else "pending")
    _w(project / "intake.json", intake)
    return {"ok": ok_count >= MIN_ANSWERS, "answered": ok_count,
            "user_answered": user_n, "min": MIN_ANSWERS,
            "status": intake["status"],
            "note": ("答案由 agent 代填，未获用户确认；签 brief 会被拒"
                     if user_n < MIN_ANSWERS else "答案由用户确认")}


def complete(project: Path) -> bool:
    intake = _r(Path(project) / "intake.json") or {}
    return len(intake.get("answers") or {}) >= MIN_ANSWERS


def sign_brief(project: Path, by: str = "user", user_said: str = "") -> Dict[str, Any]:
    """签 brief（2026-11-22 起）：必须是用户本人确认，并留一句用户原话。

    agent 代答、没有原话、用户答案不足 10 条，三者任一 → 拒签。
    """
    import hashlib
    import time
    project = Path(project)
    brief = _r(project / "brief.json") or {}
    intake = _r(project / "intake.json") or {}
    if not complete(project):
        return {"ok": False, "error": "intake 有效回答不足 10 个，不能签 brief"}
    user_n = int(intake.get("user_answers") or 0)
    if user_n < MIN_ANSWERS:
        return {"ok": False,
                "error": f"用户确认的回答只有 {user_n} 条（需 ≥{MIN_ANSWERS}）；"
                         "agent 代填不算，请把问题问给用户后重填"}
    if str(by).lower() != "user":
        return {"ok": False, "error": "brief 只能由 user 签；agent 不能代签"}
    if len(str(user_said or "").strip()) < 6:
        return {"ok": False,
                "error": "缺用户原话：--user-said \"用户对目标的一句确认\""}
    brief["problem"] = brief.get("problem") or str(intake.get("intent") or "")
    brief["answers"] = intake.get("answers") or {}
    raw = json.dumps(brief, ensure_ascii=False, sort_keys=True).encode("utf-8")
    brief["signed"] = {"by": "user", "user_said": str(user_said).strip(),
                       "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "sha": hashlib.sha256(raw).hexdigest()[:16]}
    _w(project / "brief.json", brief)
    return {"ok": True, "signed": brief["signed"]}


def signed(project: Path) -> Optional[Dict[str, Any]]:
    brief = _r(Path(project) / "brief.json") or {}
    return brief.get("signed")
