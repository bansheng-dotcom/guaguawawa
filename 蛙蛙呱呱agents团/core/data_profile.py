# -*- coding: utf-8 -*-
"""core/data_profile —— 先看数据长什么样，再决定能问什么。

不做「问题模板」：这里只做**数据画像**（有哪些列、哪些是维度、哪些是度量、
时间轴多长、组别多少），问题由 question_derive 按画像规则生成。

用法：
    from core.data_profile import profile_dir
    p = profile_dir("…/data")     # → {"files":[...], "tables":[{...}]}
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

TIME_NAMES = {"year", "month", "date", "period", "quarter", "week", "ym", "年份", "月份", "时间"}
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
TIME_VALUE_RE = re.compile(r"^(19|20)\d{2}([-/]?\d{1,2})?$|^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$")


def _is_num(v: str) -> bool:
    return bool(NUM_RE.match(str(v).strip()))


def _looks_time(col: str, vals: List[str]) -> bool:
    if col.lower() in TIME_NAMES or col in TIME_NAMES:
        return True
    sample = [v for v in vals[:20] if v]
    return bool(sample) and sum(1 for v in sample if TIME_VALUE_RE.match(str(v).strip())) >= len(sample) * 0.8


def profile_csv(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:  # noqa: BLE001
        return None
    if not rows:
        return None
    cols = list(rows[0].keys())
    info = []
    for c in cols:
        vals = [r.get(c, "") for r in rows]
        numeric = sum(1 for v in vals if _is_num(v)) >= max(1, len(vals) * 0.9)
        uniq = len({v for v in vals if v != ""})
        # 列名命中时间词（year/month/date…）时，即使全是数字也按时间轴处理
        by_name = c.lower() in TIME_NAMES or c in TIME_NAMES
        info.append({"name": c, "numeric": numeric, "unique": uniq,
                     "time": by_name or (not numeric and _looks_time(c, vals))})
    return {
        "file": str(path).replace("\\", "/"),
        "rows": len(rows),
        "cols": info,
        "time": [c["name"] for c in info if c["time"]],
        "measures": [c["name"] for c in info if c["numeric"] and not c["time"]],
        "dimensions": [c["name"] for c in info if not c["numeric"] and not c["time"] and 1 < c["unique"] <= max(50, len(rows))],
        "sample": rows[:2],
    }


def profile_dir(data_dir: str | Path) -> Dict[str, Any]:
    d = Path(data_dir)
    tables = []
    for p in sorted(d.glob("*.csv")):
        t = profile_csv(p)
        if t:
            tables.append(t)
    return {"dir": str(d).replace("\\", "/"), "tables": tables}


if __name__ == "__main__":
    import sys
    print(json.dumps(profile_dir(sys.argv[1]), ensure_ascii=False, indent=1)[:2000])
