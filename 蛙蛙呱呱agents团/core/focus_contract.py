# -*- coding: utf-8 -*-
"""core/focus_contract —— 主表/主指标由模型选，规则只负责校验。

分工：
  模型（读任务卡 + 数据画像）→ 产出 focus.json：选哪张表、哪个指标、哪个维度、为什么
  规则（本模块）→ 校验：表存在、行数够、指标是数值列、维度存在、理由不能为空

校验不过就拒绝，不回退到词表——词表只在没有 focus 时做兜底，并在 brief 里标明。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIDENCE = {"high", "medium", "low"}
PROFILE_ONLY = ("share", "pct", "ratio", "占比")


def load_focus(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_focus(focus: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    table_name = str(focus.get("table") or "")
    if not table_name:
        return ["缺少 table"]
    table = next((t for t in profile["tables"]
                  if Path(t["file"]).name == table_name or t["file"].endswith(table_name)), None)
    if table is None:
        return [f"表不存在于画像：{table_name}（画像里有 {[Path(t['file']).name for t in profile['tables']]}）"]

    if table["rows"] < 5:
        errs.append(f"表只有 {table['rows']} 行，样本不足 5 行")
    measure = str(focus.get("measure") or "")
    if measure not in table["measures"]:
        errs.append(f"measure={measure!r} 不是该表的数值列（可选：{table['measures']}）")
    if any(w in measure.lower() for w in PROFILE_ONLY):
        errs.append(f"measure={measure!r} 是占比/派生列，不能当主指标")
    dim = focus.get("dimension")
    if dim and dim not in table["dimensions"]:
        errs.append(f"dimension={dim!r} 不在该表维度里（可选：{table['dimensions']}）")
    if str(focus.get("confidence", "")) not in CONFIDENCE:
        errs.append(f"confidence 必须是 {sorted(CONFIDENCE)} 之一")
    if len(str(focus.get("reason") or "")) < 10:
        errs.append("reason 太短：需要写清为什么选这张表/这个指标")
    return errs


def focus_note(focus: Dict[str, Any], table: Dict[str, Any]) -> str:
    dim = f"、主维度 {focus['dimension']}" if focus.get("dimension") else ""
    return (f"模型选定主表 {Path(table['file']).name}、主指标 {focus['measure']}{dim}"
            f"（置信度 {focus.get('confidence')}；理由：{focus.get('reason')}）。规则校验通过。")
