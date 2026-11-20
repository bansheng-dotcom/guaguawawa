# -*- coding: utf-8 -*-
"""charts_pro.spec_time —— 时间族参数化渲染器（gantt / timeline / cal_heatmap / candle / ym_heat）。"""
from __future__ import annotations

import math

from .prokit2 import (
    ACCENT, BLUE, INK, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    blend, ci, ln, pa, rc, sx, sy, t,
)


def _svg(w, h, label):
    return [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{label}" preserveAspectRatio="xMidYMid meet">']


def _gantt(s: dict) -> str:
    tasks = s["tasks"]
    W, H = 640, 50 + len(tasks) * 32 + 20
    L, R = 140, 580
    end = max(t["end"] for t in tasks) or 1
    X = sx(0, end, L, R)
    b = _svg(W, H, "甘特")
    for i, tk in enumerate(tasks):
        y = 56 + i * 32
        b.append(t(20, y + 4, tk["label"], 7.6, INK2))
        b.append(rc(X(tk["start"]), y - 7, max(X(tk["end"]) - X(tk["start"]), 2), 14, INK2, rx=1.5))
    for ms in s.get("milestones", []):
        b.append(ln(X(ms["at"]), 40, X(ms["at"]), 40 + len(tasks) * 32, ACCENT, 1, "2 3"))
        b.append(t(X(ms["at"]) + 4, 38, ms["label"], 7, ACCENT))
    for k in range(5):
        v = end * k / 4
        b.append(t(X(v), H - 10, f"{v:g}", 6.8, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _timeline(s: dict) -> str:
    ms = s["milestones"]
    W, H = 640, 240
    L, R = 60, 590
    end = max(m["at"] for m in ms) or 1
    X = sx(0, end, L, R)
    b = _svg(W, H, "里程碑")
    b.append(ln(L, 120, R, 120, LINE2, 1.4))
    for i, m in enumerate(ms):
        y = 90 if i % 2 == 0 else 156
        b.append(ln(X(m["at"]), 120, X(m["at"]), y + (6 if i % 2 == 0 else -6), INK2, 1))
        b.append(ci(X(m["at"]), 120, 4, ACCENT))
        b.append(t(X(m["at"]), y, m["label"], 7.4, INK2, 600, anchor="middle"))
    for k in range(5):
        v = end * k / 4
        b.append(t(X(v), 132, f"{v:g}", 6.8, FAINT, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


def _cal(s: dict) -> str:
    vals = [float(v) for v in s["values"]]
    W, H = 640, 300
    L, T = 56, 44
    cw, ch = 17, 16
    mx = max(vals) or 1
    b = _svg(W, H, "日历热力")
    for m in range(12):
        b.append(t(L - 8, T + m * ch + 12, f"{m + 1}月", 7, FAINT, anchor="end"))
    for i, v in enumerate(vals):
        m, d = divmod(i, 30)
        if m > 11:
            break
        b.append(rc(L + d * cw, T + m * ch, cw - 2, ch - 2, blend(v / mx)))
    b.append("</svg>")
    return "".join(b)


def _candle(s: dict) -> str:
    bars = s["ohlc"]
    W, H = 640, 320
    L, R, T, B = 60, 596, 48, 250
    lo = min(b["l"] for b in bars) * .995
    hi = max(b["h"] for b in bars) * 1.005
    Y = sy(lo, hi, B, T)
    slot = (R - L) / len(bars)
    bw = slot * .56
    b = _svg(W, H, "蜡烛")
    for i, k in enumerate(bars):
        cx = L + slot * i + slot / 2
        up = k["c"] >= k["o"]
        color = BLUE if up else ACCENT
        b.append(ln(cx, Y(k["h"]), cx, Y(k["l"]), color, 1))
        b.append(rc(cx - bw / 2, Y(max(k["o"], k["c"])), bw,
                    max(abs(Y(k["o"]) - Y(k["c"])), 1.5), color, rx=1))
    b.append("</svg>")
    return "".join(b)


def _ym_heat(s: dict) -> str:
    rows, cols, M = s["rows"], s.get("cols") or [str(i + 1) for i in range(12)], s["matrix"]
    W, H = 640, 300
    L, T = 70, 46
    cw, ch = 40, 56
    mx = max(max(r) for r in M) or 1
    b = _svg(W, H, "年 × 月热力")
    for j, c in enumerate(cols):
        b.append(t(L + j * cw + cw / 2, T - 10, c, 7, FAINT, anchor="middle"))
    for i, r in enumerate(rows):
        b.append(t(L - 10, T + i * ch + 34, r, 7.4, INK2, anchor="end"))
        for j in range(len(cols)):
            v = M[i][j]
            b.append(rc(L + j * cw + 1, T + i * ch + 1, cw - 2, ch - 2, blend(v / mx)))
            b.append(t(L + j * cw + cw / 2, T + i * ch + 34, f"{v:.0f}", 6.8,
                       WHITE if v / mx > .55 else INK2, anchor="middle"))
    b.append("</svg>")
    return "".join(b)


RENDERERS = {"gantt": _gantt, "timeline": _timeline, "cal_heatmap": _cal,
             "candle": _candle, "ym_heat": _ym_heat}
