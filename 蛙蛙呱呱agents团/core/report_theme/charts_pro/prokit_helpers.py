# -*- coding: utf-8 -*-
"""prokit_helpers —— 图型基元（颜色 + SVG 原语），不含任何样例数据。

2026-11-23 从 prokit2.py 抽出：spec.py（生产 70 型渲染器）需要这些基元，
但 prokit2 同时带着历史项目的样例常量（`CATS = DS.CATS` 等），导致生产 import
就加载样例数据。现在 spec.py 改从这里导入，样例数据留待迁出。
"""
from __future__ import annotations

import math

INK, INK2, MUTED, FAINT = "#1F2A37", "#33424F", "#66737F", "#98A2AC"
LINE, LINE2 = "#E3E5E8", "#C9D0D6"
ACCENT, BLUE, WHITE = "#C0392B", "#2E6F9E", "#FFFFFF"


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def t(x, y, s, size=8.6, fill=INK, fw=400, anchor="start", halo=False, ls=None) -> str:
    a = (f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
         f'text-anchor="{anchor}" font-weight="{fw}"')
    if ls:
        a += f' letter-spacing="{ls}"'
    if halo:
        a += ' paint-order="stroke" stroke="#FFFFFF" stroke-width="3" stroke-linejoin="round"'
    return f"<text {a}>{esc(s)}</text>"


def ln(x1, y1, x2, y2, stroke=LINE, w=1, dash=None, cap="butt") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" stroke-linecap="{cap}"{d}/>')


def rc(x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}"{s}{o}/>')


def ci(cx, cy, r, fill, stroke=None, sw=1, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"{s}{o}/>'


def pa(d, fill="none", stroke=None, w=1, dash=None, opacity=None) -> str:
    s = f' stroke="{stroke}" stroke-width="{w}"' if stroke else ""
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<path d="{d}" fill="{fill}"{s}{ds}{o}/>'


def sx(lo, hi, a, b):
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def sy(lo, hi, b, top):
    return lambda v: b - (v - lo) / (hi - lo) * (b - top)


def blend(v: float) -> str:
    """0（白）→ 1（强调红）。热力图专用。"""
    a, c = (255, 255, 255), (192, 57, 43)
    p = max(0.0, min(1.0, v))
    return "#%02X%02X%02X" % tuple(int(a[i] + (c[i] - a[i]) * p) for i in range(3))


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs, q):
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
