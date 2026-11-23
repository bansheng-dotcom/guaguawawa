# -*- coding: utf-8 -*-
"""charts_pro —— 生产图型库（70 型，走 spec.py）。

2026-11-23：样例渲染器（pk_b1..b4 / prokit2，连带历史项目样例数据）改为**懒加载**——
只有真的调用 `render("fig_xxx")` 时才导入它们；生产画图（spec.render）不再被样例数据拖累。
"""
from __future__ import annotations

_REG: dict = {}


def _registry() -> dict:
    """懒加载样例渲染器注册表（第一次调 render/names 时才导入）。"""
    if not _REG:
        try:
            from samples import pk_b1, pk_b2, pk_b3, pk_b4, pk_dual, prokit2  # noqa: PLC0415
        except Exception:  # samples/ 不在路径上时静默降级（生产不需要样例）
            return _REG
        for _m in (prokit2, pk_b1, pk_b2, pk_b3, pk_b4, pk_dual):
            for _k, _v in vars(_m).items():
                if _k.startswith("fig_") and callable(_v):
                    _REG[_k] = _v
    return _REG


def names() -> list:
    return sorted(_registry())


def render(name: str) -> str:
    reg = _registry()
    if name not in reg:
        raise KeyError(f"未知图型: {name}（可用 {len(reg)} 型）")
    return reg[name]()
