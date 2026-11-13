# -*- coding: utf-8 -*-
"""分析算子库：与业务无关的「怎么算」，报告深度从这里来，而不是从文案里来。

每个算子返回统一结构，writer/证据包只负责拼装：

    {"op": "...", "title": "...", "headline": "...", "numbers": {...},
     "text": "可直接进报告的判断句", "caveat": "这条结论的成立条件",
     "sources": [...], "needs": [...]}

纪律：
1. 算子不算自己拿不到的数——缺输入就 raise MissingData，由 coverage 汇总成缺口；
2. 每个算子必须自带 caveat（口径/样本/方法限制），否则不许进报告。
"""
from __future__ import annotations

import statistics
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


class MissingData(Exception):
    """该问题所需的数据不在，不允许用话术糊过去。"""

    def __init__(self, what: str, need: str):
        super().__init__(f"{what}：缺 {need}")
        self.what, self.need = what, need


# ────────────────────────────── 算子 ──────────────────────────────
def variance_share(rows: Sequence[Dict[str, Any]], dim: str, value: str,
                   sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """价差/差异归因：某个维度解释了总量的多少（η²，一方差分析）。

    rows: [{"<dim>": 组, "<value>": 数值}, ...]
    """
    data = [(str(r[dim]), float(r[value])) for r in rows
            if r.get(dim) and r.get(value) not in (None, "")]
    if len(data) < 4:
        raise MissingData("方差归因", f"{dim} × {value} 至少 4 条观测")
    grand = statistics.mean(v for _, v in data)
    ss_total = sum((v - grand) ** 2 for _, v in data)
    groups: Dict[str, List[float]] = {}
    for g, v in data:
        groups.setdefault(g, []).append(v)
    ss_between = sum(len(v) * (statistics.mean(v) - grand) ** 2 for v in groups.values())
    eta = ss_between / ss_total if ss_total else 0.0
    return {
        "op": "variance_share", "title": f"{dim} 对差异的解释力",
        "numbers": {"eta2": round(eta, 4), "groups": len(groups), "n": len(data)},
        "headline": f"{dim} 解释了 {eta:.1%} 的差异",
        "text": (f"{len(data)} 条观测里，{dim} 解释了 {eta:.1%} 的差异（η²），"
                 f"其余 {1 - eta:.1%} 来自组内——差异主要在 {dim} 之间，不在同一 {dim} 内部。"),
        "caveat": "η² 只说明差异分布，不说明因果；组间差异可能由未观测变量驱动。",
        "sources": sources or [],
    }


def benchmark(value: float, history: Sequence[float],
              sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """基准位置：当前值在历史同窗口里的 z 分数与分位。"""
    hist = [float(x) for x in history if x is not None]
    if len(hist) < 3:
        raise MissingData("基准位置", "至少 3 年同窗口历史值")
    mu = statistics.mean(hist)
    sd = statistics.pstdev(hist)
    z = (value - mu) / sd if sd else 0.0
    pct = sum(1 for h in hist if h < value) / len(hist)
    where = "高于" if z > 0 else "低于"
    return {
        "op": "benchmark", "title": "历史基准位置",
        "numbers": {"value": value, "mean": round(mu, 4), "sd": round(sd, 4),
                    "z": round(z, 2), "pct": round(pct, 3), "n": len(hist)},
        "headline": f"当前 {value:g} 比历史均值 {where} {abs(z):.2f} 个标准差",
        "text": (f"当前值 {value:g}，历史同窗口均值 {mu:g}、标准差 {sd:g}，"
                 f"z={z:+.2f}，处于历史 {pct:.0%} 分位。"),
        "caveat": "样本年份少（n<10）时 z 分数不稳定；序列自相关会放大显著性，只作描述。",
        "sources": sources or [],
    }


def correlation(xs: Sequence[float], ys: Sequence[float],
                sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """两条序列的同步性（Pearson r）。"""
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    if len(x) != len(y) or len(x) < 4:
        raise MissingData("同步性", "两条等长序列且至少 4 期")
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    r = num / den if den else 0.0
    strength = "几乎不同步" if abs(r) < 0.2 else ("弱同步" if abs(r) < 0.5 else "明显同步")
    return {
        "op": "correlation", "title": "两端同步性",
        "numbers": {"r": round(r, 3), "n": len(x)},
        "headline": f"r={r:.2f}（{strength}）",
        "text": f"{len(x)} 期数据显示两端相关 r={r:.2f}（{strength}），不能当作传导关系。",
        "caveat": "点少时 r 的置信区间很宽；相关不等于因果。",
        "sources": sources or [],
    }


def explain_share(total: float, parts: Sequence[Dict[str, Any]],
                  sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """价差/差额拆解：各分项解释了总额的多少，残差多少。

    parts: [{"label": 名称, "value": 数值}, ...]
    """
    if not parts:
        raise MissingData("差额拆解", "至少一个分项")
    explained = sum(float(p["value"]) for p in parts)
    resid = total - explained
    share = explained / total if total else 0.0
    top = max(parts, key=lambda p: abs(float(p["value"])))
    return {
        "op": "explain_share", "title": "差额拆解",
        "numbers": {"total": total, "explained": round(explained, 3),
                    "residual": round(resid, 3), "share": round(share, 4)},
        "headline": f"{top['label']} 解释了 {abs(float(top['value'])) / total:.1%}",
        "text": (f"总差 {total:g} 中，" +
                 "、".join(f"{p['label']} {float(p['value']):+g}" for p in parts) +
                 f"，合计解释 {share:.1%}，残差 {resid:+g}；"
                 f"最大单项是{top['label']}，占 {abs(float(top['value'])) / total:.1%}。"),
        "caveat": "分项之间必须互斥且可加，否则残差会失真；口径不匹配时只作方向。",
        "sources": sources or [],
    }


def sensitivity(fn: Callable[[float], float], grid: Sequence[float],
                label: str = "参数", unit: str = "",
                sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """单参数敏感性：给一组取值，算目标函数怎么变。"""
    grid = [float(g) for g in grid]
    if len(grid) < 2:
        raise MissingData("敏感性", "至少两个取值点")
    base = fn(grid[0])
    pts = [{"x": g, "y": round(fn(g), 4)} for g in grid]
    span = (max(p["y"] for p in pts) - min(p["y"] for p in pts))
    pct = span / abs(base) if base else 0.0
    return {
        "op": "sensitivity", "title": f"{label} 敏感性",
        "numbers": {"points": pts, "span": round(span, 4), "pct_of_base": round(pct, 4)},
        "headline": f"{label} 在 {grid[0]:g}–{grid[-1]:g}{unit} 内使结果变动 {pct:.1%}",
        "text": (f"{label} 从 {grid[0]:g}{unit} 到 {grid[-1]:g}{unit}，结果由 {base:.2f} 变动到 "
                 f"{fn(grid[-1]):.2f}（跨度 {span:.2f}，占基准 {pct:.1%}）；"
                 f"每变动 1 个单位约带动 {span / (grid[-1] - grid[0]):.3f}。"),
        "caveat": "只做单参数扰动，不含参数间交互；线性外推到区间外不成立。",
        "sources": sources or [],
    }


def coverage(frame: Dict[str, Any], available: Iterable[str]) -> List[Dict[str, str]]:
    """业务框架 × 现有数据 → 能答/答不了的问题清单（缺口必须进报告）。"""
    have = set(available)
    out: List[Dict[str, str]] = []
    for q in frame.get("questions") or []:
        need = list(q.get("needs") or [])
        missing = [n for n in need if n not in have]
        out.append({
            "id": str(q.get("id", "")),
            "question": str(q.get("question", "")),
            "status": "answered" if not missing else "blocked",
            "needs": need,
            "missing": missing,
            "need": "、".join(missing),
            "decision": str(q.get("decision", "")),
        })
    return out
