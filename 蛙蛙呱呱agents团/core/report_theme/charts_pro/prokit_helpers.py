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
    """线性映射；零域（hi==lo）映射到画布中线，避免 SinglePoint/全零数据除零。"""
    span = hi - lo
    if abs(span) < 1e-12:
        mid = (a + b) / 2
        return lambda v: mid
    return lambda v: a + (v - lo) / span * (b - a)


def sy(lo, hi, b, top):
    span = hi - lo
    if abs(span) < 1e-12:
        mid = (b + top) / 2
        return lambda v: mid
    return lambda v: b - (v - lo) / span * (b - top)


def blend(v: float) -> str:
    """0（白）→ 1（强调红）。热力图专用；负值按 0 处理，故只用于非负矩阵。"""
    a, c = (255, 255, 255), (192, 57, 43)
    p = max(0.0, min(1.0, v))
    return "#%02X%02X%02X" % tuple(int(a[i] + (c[i] - a[i]) * p) for i in range(3))


def diverging(v: float, lo: float, hi: float) -> str:
    """负 → 蓝，0 → 白，正 → 红。含负值的矩阵/热力用它，避免"负数与 0 同色"。"""
    if hi - lo < 1e-12:
        return "#FFFFFF"
    if v >= 0:
        t_ = v / hi if hi > 0 else 0.0
        a, c = (255, 255, 255), (192, 57, 43)
    else:
        t_ = v / lo if lo < 0 else 0.0
        a, c = (255, 255, 255), (46, 111, 158)
    t_ = max(0.0, min(1.0, t_))
    return "#%02X%02X%02X" % tuple(int(a[i] + (c[i] - a[i]) * t_) for i in range(3))


def fmt_num(v: float, dec: int | None = None) -> str:
    """统一数值格式：整数不带 .0，非整数按 dec（默认 1 位）并去尾零。"""
    if dec is None:
        dec = 0 if abs(v - round(v)) < 1e-9 else 2
    s = f"{v:.{dec}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def text_width(s: str, size: float) -> float:
    """估算文本宽度：CJK 按 1.0em，ASCII 按 0.55em。"""
    w = 0.0
    for ch in str(s):
        w += size * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return w


def fit_text(s: str, max_w: float, size: float, max_lines: int = 2) -> list[str]:
    """按宽度切行；最后一行放不下则截断加省略号。返回至少一行。"""
    s = str(s)
    if text_width(s, size) <= max_w:
        return [s]
    lines: list[str] = []
    buf = ""
    for ch in s:
        if text_width(buf + ch, size) > max_w and buf:
            lines.append(buf)
            buf = ch
            if len(lines) >= max_lines:
                break
        else:
            buf += ch
    if len(lines) < max_lines and buf:
        lines.append(buf)
    if len(lines) == max_lines and "".join(lines) != s:
        last = lines[-1]
        while last and text_width(last + "…", size) > max_w:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines or [""]


def empty_chart(w, h, label, msg="无数据") -> str:
    """空态：不抛异常、不返回空串，给一张说明卡。"""
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(label)}：{esc(msg)}" preserveAspectRatio="xMidYMid meet">'
            + t(w / 2, h / 2 - 4, msg, 10.5, MUTED, anchor="middle")
            + t(w / 2, h / 2 + 18, "检查筛选条件、期次或单位", 7.6, FAINT, anchor="middle")
            + "</svg>")


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs, q):
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
