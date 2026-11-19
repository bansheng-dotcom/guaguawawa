# -*- coding: utf-8 -*-
"""report_kernel.contract —— 报告开工前的「验收契约」。

一张报告在写第一段之前，必须先回答六件事：
  给谁看（audience）、支持哪个决定（decision）、必须回答哪三个问题（questions）、
  数据截止到哪天（data_cutoff）、目标档位（target_level）、谁签字（owner/reviewer）。

没有契约就开写，章节一定漂移；契约不锁档位，最后一定按「能出报告」而不是
「能决策」交付。本模块只做确定性校验，不替人写内容。
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

TARGET_LEVELS = ("L3", "L4")
REQUIRED_TEXT = ("report_id", "title", "decision", "audience",
                 "data_cutoff", "target_level", "owner", "reviewer")
MIN_QUESTIONS = 3


def _blank(v: Any) -> bool:
    return not str(v or "").strip()


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(str(s))
        return True
    except ValueError:
        return False


def template(report_id: str = "RPT-YYYYMMDD-01", title: str = "") -> Dict[str, Any]:
    return {
        "report_id": report_id,
        "title": title,
        "decision": "",
        "audience": "",
        "questions": ["", "", ""],
        "data_cutoff": "",
        "target_level": "L4",
        "owner": "",
        "reviewer": "",
        "source_count": 0,
        "series_periods": 0,
        "time_span_days": 0,
        "cross_market": False,
        "alignment_note": "",
        "trend_required": False,
        "notes": "",
    }


def validate(data: Dict[str, Any]) -> Dict[str, Any]:
    """返回 {ok, errors, warnings, normalized}；errors 全是 blocker。"""
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["契约必须是 JSON 对象"], "warnings": [],
                "normalized": {}}

    for k in REQUIRED_TEXT:
        if _blank(data.get(k)):
            errors.append(f"缺字段或为空：{k}")

    qs = data.get("questions") or []
    qs = [str(q).strip() for q in qs if str(q).strip()] if isinstance(qs, list) else []
    if len(qs) < MIN_QUESTIONS:
        errors.append(f"questions 至少 {MIN_QUESTIONS} 条（当前 {len(qs)}）")

    cutoff = str(data.get("data_cutoff") or "")
    if cutoff and not _valid_date(cutoff):
        errors.append(f"data_cutoff 不是 YYYY-MM-DD：{cutoff}")

    target = str(data.get("target_level") or "")
    if target and target not in TARGET_LEVELS:
        errors.append(f"target_level 只能是 {TARGET_LEVELS}：{target}")

    if str(data.get("report_id") or "") and not re.match(r"^[A-Za-z0-9._-]{4,64}$",
                                                         str(data["report_id"])):
        errors.append("report_id 只能是 4—64 位字母/数字/._-")

    periods = int(data.get("series_periods") or 0)
    if data.get("trend_required") and periods < 12:
        errors.append(f"声明 trend_required=true，但 series_periods={periods} < 12")

    span = int(data.get("time_span_days") or 0)
    if span > 1 and "对齐" not in str(data.get("alignment_note") or ""):
        errors.append(f"time_span_days={span} > 1，但 alignment_note 未写“对齐”")

    src = int(data.get("source_count") or 0)
    if src and src < 10:
        warnings.append(f"source_count={src} < 10，证据规模偏小")
    if target == "L4" and data.get("trend_required") and periods < 12:
        warnings.append("L4 决策稿的趋势节需要 ≥12 期序列")

    normalized = dict(data)
    normalized["questions"] = qs
    normalized["target_level"] = target or "L4"
    normalized["source_count"] = src
    normalized["series_periods"] = periods
    normalized["time_span_days"] = span
    normalized["cross_market"] = bool(data.get("cross_market"))
    normalized["trend_required"] = bool(data.get("trend_required"))
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "normalized": normalized}


def load(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path: str | Path, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def find_for(html_path: str | Path) -> Optional[Path]:
    """按优先级找同名 ship 契约。"""
    p = Path(html_path)
    for cand in (p.with_suffix(".ship.json"),
                 p.parent / "report_ship.json",
                 p.parent / f"{p.stem}.contract.ship.json"):
        if cand.exists():
            return cand
    return None
