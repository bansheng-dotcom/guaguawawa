# -*- coding: utf-8 -*-
"""report_kernel.series —— 序列与时间口径门禁。

两条硬规则：
  S1 趋势节必须 ≥12 期序列；不足 12 期只能写“情景”，不能写“趋势/预测”。
  S2 跨时点数据必须写对齐说明；跨市场结论跨 >1 天即算未对齐。

规则只认契约里声明的 series_periods / time_span_days / alignment_note，
不从正文猜；声明与正文不一致时，以契约为主并在 gate 里报错。
"""
from __future__ import annotations

from typing import Any, Dict, List

TREND_WORDS = ("趋势", "预测", "走势", "拐点")
MIN_PERIODS = 12


def check_series(contract: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    periods = int(contract.get("series_periods") or 0)
    trend_required = bool(contract.get("trend_required"))

    if trend_required and periods < MIN_PERIODS:
        errors.append(f"trend_required=true，但 series_periods={periods} < {MIN_PERIODS}")

    for sec in contract.get("sections") or []:
        title = str(sec.get("title") or "")
        q = str(sec.get("question") or "")
        if not any(w in title + q for w in TREND_WORDS):
            continue
        local = int(sec.get("series_periods") or periods)
        if local < MIN_PERIODS:
            errors.append(f"趋势节“{title}”只有 {local} 期，< {MIN_PERIODS}")

    span = int(contract.get("time_span_days") or 0)
    note = str(contract.get("alignment_note") or "")
    if span > 1 and "对齐" not in note:
        errors.append(f"time_span_days={span} > 1，但 alignment_note 未写“对齐”")
    if contract.get("cross_market") and span > 1 and "时点差" not in note:
        warnings.append("跨市场结论跨 >1 天，建议在 alignment_note 写清时点差")

    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "periods": periods, "time_span_days": span}
