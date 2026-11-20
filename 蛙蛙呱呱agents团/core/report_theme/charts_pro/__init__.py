# -*- coding: utf-8 -*-
"""charts_pro —— flow 图型库（49 型），由 viz_lab 收编。

用法（项目 charts.py）：
    from core.report_theme.charts_pro import render
    def fig_waterfall(): return render("fig_waterfall")
"""
from __future__ import annotations

from . import geo, pk_b1, pk_b2, pk_b3, pk_b4, pk_dual, prokit2

_REG = {}
for _m in (prokit2, pk_b1, pk_b2, pk_b3, pk_b4, pk_dual):
    for _k, _v in vars(_m).items():
        if _k.startswith("fig_") and callable(_v):
            _REG[_k] = _v


def names() -> list[str]:
    return sorted(_REG)


def render(name: str) -> str:
    if name not in _REG:
        raise KeyError(f"未知图型: {name}（可用 {len(_REG)} 型）")
    return _REG[name]()
