# -*- coding: utf-8 -*-
"""双轴替代：上下两栏共享时间轴（图型 C12）。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from .prokit2 import (  # noqa: E402
    ACCENT, BLUE, INK2, LINE, LINE2, MUTED, FAINT, WHITE,
    TOTAL, ln, pa, rc, svg, sx, sy, t,
)


def fig_dual_panels() -> str:
    W, H = 640, 380
    L, R = 64, 590
    T1, B1 = 42, 190
    Y1 = sy(18, 46, B1, T1)
    X = sx(0, len(TOTAL) - 1, L + 6, R - 6)
    b = svg(W, H, "月度规模与同比（上下两栏）")
    for v in (20, 30, 40):
        b.append(ln(L, Y1(v), R, Y1(v), LINE, 1))
        b.append(t(L - 8, Y1(v) + 3, str(v), 7.2, FAINT, anchor="end"))
    b.append(t(L, T1 - 10, "规模（亿元）", 7.4, MUTED))
    pts = [(X(i), Y1(v)) for i, v in enumerate(TOTAL)]
    b.append(pa("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts), "none", INK2, 1.6))

    T2, B2 = 236, 340
    yoy = [(TOTAL[i] / TOTAL[i - 12] - 1) * 100 for i in range(12, 36)]
    Y2 = sy(-12, 12, B2, T2)
    b.append(ln(L, Y2(0), R, Y2(0), LINE2, 1))
    for v in (-10, 10):
        b.append(t(L - 8, Y2(v) + 3, f"{v:+d}%", 7.2, FAINT, anchor="end"))
    b.append(t(L, T2 - 10, "同比", 7.4, MUTED))
    slot = (R - L) / len(yoy)
    for i, v in enumerate(yoy):
        x = L + slot * i + slot * 0.2
        b.append(rc(x, Y2(max(v, 0)), slot * 0.6, abs(Y2(v) - Y2(0)),
                    ACCENT if v < 0 else BLUE, rx=1, opacity=".85"))
    b.append(t(20, 362, "两个量纲不叠在一张图上：上栏规模、下栏同比，共享同一时间轴。", 7.4, MUTED))
    b.append("</svg>")
    return "".join(b)
