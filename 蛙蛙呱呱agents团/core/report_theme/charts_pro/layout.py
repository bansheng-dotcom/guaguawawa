# -*- coding: utf-8 -*-
"""charts_pro.layout —— 渲染前的 Layout 层（P4-3）。

不改 70 个渲染函数的绘图数学，而是在**它们之前**统一接管五件事：

    empty     空态：required 字段为空 → 直接返回「无数据」卡（全 70 型一致）
    domain    值域：有数值就给出 [min(0,lo), max(0,hi)]，写进 spec["domain"]
    tick      刻度：1/2/2.5/5 × 10^k 的 nice step
    labels    标签：按 spec 估算最长标签像素与可用宽度，写进 _layout 供渲染器用
    format    精度：从数值分布推断 decimals，并写入 spec["decimals"]

渲染函数可以继续自己算，也可以直接读 `spec["_layout"]`；
门禁要求 70/70 都能拿到同一份 layout，且空态必须被统一拦截。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .prokit_helpers import empty_chart, fmt_num, text_width

LAYOUT_KEY = "_layout"
_NUMERIC_KEYS = ("value", "values", "low", "high", "lo", "hi", "matrix",
                 "deltas", "start", "target", "band")


def _required(typ: str) -> tuple:
    from . import spec as _spec
    return tuple(_spec.REQUIRED.get(typ, ()))


def _alias(typ: str) -> str:
    from . import spec as _spec
    return _spec.ALIASES.get(str(typ), str(typ))


def _numbers(node: Any, depth: int = 0) -> List[float]:
    """递归收集「数据值」；跳过坐标/样式这类非数据数字字段。"""
    if depth > 6:
        return []
    out: List[float] = []
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        out.append(float(node))
    elif isinstance(node, (list, tuple)):
        for x in node:
            out.extend(_numbers(x, depth + 1))
    elif isinstance(node, dict):
        for k, v in node.items():
            if str(k).startswith("_") or k in ("x", "y", "w", "h", "rx", "opacity",
                                               "font", "size", "stroke", "width"):
                continue
            if k in _NUMERIC_KEYS or isinstance(v, (int, float, list, tuple, dict)):
                out.extend(_numbers(v, depth + 1))
    return out


def _nice_step(v: float) -> float:
    if v <= 0:
        return 1.0
    k = math.floor(math.log10(v))
    base = 10 ** k
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * base:
            return m * base
    return 10 * base


def _decimals(nums: List[float]) -> int:
    if not nums:
        return 1
    span = max(nums) - min(nums)
    scale = max(abs(max(nums)), abs(min(nums)), 1e-12)
    if span == 0:
        return 1 if scale < 1e4 else 0
    if span / scale < 0.01:
        return 1
    if max(abs(v) for v in nums) >= 1e4:
        return 0
    if all(abs(v - round(v)) < 1e-9 for v in nums):
        return 0
    return 1


def _is_empty(spec: Dict[str, Any], typ: str) -> bool:
    req = _required(typ)
    if not req:
        return False
    for k in req:
        if k not in spec:
            return False          # 缺字段交给 validate 报错，不当空态
        v = spec.get(k)
        if isinstance(v, (list, dict, tuple, str)) and not v:
            return True
    nums = _numbers({k: spec.get(k) for k in req})
    return not nums


def _label_px(spec: Dict[str, Any]) -> int:
    labels: List[str] = []
    for key in ("items", "points", "rows", "nodes"):
        for it in spec.get(key) or []:
            if isinstance(it, dict):
                for lk in ("label", "name", "id", "text"):
                    if it.get(lk):
                        labels.append(str(it[lk]))
                        break
            elif isinstance(it, str):
                labels.append(it)
    if not labels:
        return 0
    return int(max(text_width(x, 8.6) for x in labels))


def prepare(spec: Dict[str, Any]) -> Dict[str, Any]:
    """给任意图型 spec 注入 `_layout`（不修改调用方原始对象）。"""
    s = dict(spec or {})
    typ = _alias(str(s.get("type") or ""))
    if s.get("type"):
        s["type"] = typ
    nums = _numbers({k: s.get(k) for k in _required(typ)}) if typ else _numbers(s)
    raw_lo, raw_hi = ((min(nums), max(nums)) if nums else (0.0, 1.0))
    lo, hi = min(raw_lo, 0.0), max(raw_hi, 0.0)
    pad = (hi - lo) * 0.05 if hi > lo else 1.0
    lo = lo - pad if lo < 0 else 0.0
    hi = hi + pad
    if hi <= lo:
        hi = lo + 1.0
    dec = _decimals(nums)
    lay = {
        "type": typ,
        "empty": _is_empty(s, typ),
        "n": len(nums),
        "domain": [lo, hi],
        "negative": any(v < 0 for v in nums),
        "flat": bool(nums) and max(nums) == min(nums),
        "tick": _nice_step((hi - lo) / 4.0),
        "decimals": dec,
        "label_px": _label_px(s),
        "required": list(_required(typ)),
    }
    s[LAYOUT_KEY] = lay
    s.setdefault("decimals", dec)
    s.setdefault("domain", tuple(lay["domain"]))
    return s


def describe(spec: Dict[str, Any]) -> str:
    lay = spec.get(LAYOUT_KEY) or prepare(spec)[LAYOUT_KEY]
    if lay["empty"]:
        return "无数据"
    return "值域 %s—%s · 刻度 %s · 小数 %d" % (
        fmt_num(lay["domain"][0], lay["decimals"]),
        fmt_num(lay["domain"][1], lay["decimals"]),
        fmt_num(lay["tick"], lay["decimals"]), lay["decimals"])


def render_empty(spec: Dict[str, Any]) -> str:
    label = str(spec.get("label") or spec.get("title") or spec.get("type") or "图表")
    return empty_chart(640, 140, label, msg="无数据")
