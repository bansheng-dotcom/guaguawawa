# -*- coding: utf-8 -*-
"""core.shape_gate —— 数据形状门禁（SOP §2.5，2026-11-23 新增）。

判据（照 SOP 原文）：
    shape_ok_ratio = 同 metric ≥3 行的指标数 / 总指标数
    ≥0.5 通过 | 0.3–0.5 只许 1D 图 | <0.3 FAIL 并写缺哪一维

为什么需要：一张图要「多主体 / 多期次」才画得出关系。如果数据里每个指标
只有 1 行，那无论怎么选图都只能画单点或 1D 条——这不是渲染器的问题，是
**数据形状**的问题。这个门禁在出图前把它量出来。

默认**软门禁**（写文件、给 warnings，不拦），`GUAGUA_SHAPE_HARD=1` 才硬拦。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

PASS = 0.5
ONLY_1D = 0.3


def shape_ok_ratio(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """同 metric ≥3 行的指标数 / 总指标数。"""
    by_metric: Counter = Counter()
    for r in rows or []:
        m = str(r.get("metric_id") or r.get("metric") or "").strip()
        if m:
            by_metric[m] += 1
    total = len(by_metric)
    ok = sum(1 for n in by_metric.values() if n >= 3)
    ratio = (ok / total) if total else 0.0
    verdict = ("pass" if ratio >= PASS
               else ("1d_only" if ratio >= ONLY_1D else "fail"))
    thin = sorted((m for m, n in by_metric.items() if n < 3),
                  key=lambda m: by_metric[m])
    return {
        "ratio": round(ratio, 3),
        "ok_metrics": ok,
        "total_metrics": total,
        "verdict": verdict,
        # 缺哪一维：这些指标只有 1–2 行，缺「对照主体/期次」
        "thin_metrics": [{"metric": m, "rows": by_metric[m]} for m in thin[:10]],
    }


def gate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """返回门禁结果：ok 表示是否可出 2D 图。"""
    r = shape_ok_ratio(rows)
    r["ok"] = r["verdict"] == "pass"
    r["allowed_charts"] = ("2d" if r["verdict"] == "pass"
                           else ("1d" if r["verdict"] == "1d_only" else "none"))
    return r
