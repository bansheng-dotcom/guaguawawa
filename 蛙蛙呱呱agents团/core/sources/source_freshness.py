# -*- coding: utf-8 -*-
"""core.source_freshness —— 来源时效度量（不改判据，只把「旧」变成可看见的数字）。

口径：
    - 只解析 YYYY / YYYY-MM / YYYY-MM-DD；
    - 只有年份的按当年 7 月 1 日算（年报口径的中点，避免把今年年报判成两年旧）；
    - 以「距今月数」为准，窗口默认 18 个月；
    - 解析不了日期的来源不计入分母，单独记 undated。
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Dict, List, Sequence

_DATE = re.compile(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$")
DEFAULT_WINDOW_MONTHS = 18


def parse_date(value: Any) -> _dt.date | None:
    m = _DATE.match(str(value or "").strip())
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2)) if m.group(2) else 7
    d = int(m.group(3)) if m.group(3) else 1
    try:
        return _dt.date(y, min(max(mo, 1), 12), min(max(d, 1), 28))
    except ValueError:
        return None


def months_between(a: _dt.date, b: _dt.date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def summarize(sources: Sequence[Dict[str, Any]],
              window_months: int = DEFAULT_WINDOW_MONTHS,
              today: _dt.date | None = None) -> Dict[str, Any]:
    now = today or _dt.date.today()
    dated: List[tuple] = []
    undated = 0
    for s in sources:
        d = parse_date(s.get("date"))
        if d is None:
            undated += 1
            continue
        dated.append((months_between(d, now), d))
    if not dated:
        return {"window_months": window_months, "dated": 0, "undated": undated,
                "newest": None, "oldest": None, "median_age_months": None,
                "stale_ratio": None, "fresh_ratio": None}
    ages = sorted(x[0] for x in dated)
    stale = sum(1 for a in ages if a > window_months)
    return {
        "window_months": window_months,
        "dated": len(dated),
        "undated": undated,
        "newest": max(d for _, d in dated).isoformat(),
        "oldest": min(d for _, d in dated).isoformat(),
        "median_age_months": ages[len(ages) // 2],
        "stale_ratio": round(stale / len(dated), 3),
        "fresh_ratio": round(1 - stale / len(dated), 3),
    }
