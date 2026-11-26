# -*- coding: utf-8 -*-
"""图表规格契约：图表不是装饰，必须先声明要证明什么、缺什么不许画。"""
from __future__ import annotations

from typing import Any, Dict, List

REQUIRED = ("type", "title", "source", "unit_meta", "claim_to_prove")


def errors(chart: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for k in REQUIRED:
        if not str(chart.get(k) or "").strip():
            out.append(f"chart 缺 {k}")
    if not chart.get("required_annotations"):
        out.append("chart 缺 required_annotations（起止值/差值/目标线/样本量至少一项）")
    if not chart.get("fail_if_missing"):
        out.append("chart 缺 fail_if_missing（缺什么就不许画）")
    return out


def assert_ok(chart: Dict[str, Any]) -> None:
    e = errors(chart)
    if e:
        raise ValueError("；".join(e))
