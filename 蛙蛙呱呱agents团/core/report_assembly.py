# -*- coding: utf-8 -*-
"""core/report_assembly —— finding → 节/指标/计数（从 report_compose 拆出的唯一实现）。

为什么单独成模块（v11 / P1.4）：

`core/report_compose.py` 曾是 v9 的「装配器 + 22 纲领」大杂烩。
v10 起 `decision_report` 只用到它的四个私有函数：

    _section_of(f)                        finding → 节
    _metrics(picked, label_of)            指标带
    _subject(project)                     项目名 → 报告主题
    _counts(views, sections, picked, desk) 计数注册表

把四个函数搬到这里之后，`report_compose` 可以整份删除（P1.4），
而不影响线上唯一的 `decision_report` 路径。

纪律：
- **行为不变**：这是纯搬迁，函数体逐行保留（回归判据：report.md 哈希不变）。
- **只做装配，不做分析**：分析在 core/methods，渲染在 core/report_renderer。
"""
from __future__ import annotations

from typing import Any, Dict, List

from core import claims


def _subject(project: str) -> str:
    """项目目录名 → 报告主题（去掉「调研/分析/报告」与日期尾巴）。"""
    s = str(project)
    for prefix in ("新业务_", "新业务-", "研究_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    for tail in ("调研", "分析", "报告", "可行性"):
        s = s.replace(tail, "")
    if "_" in s and s.rsplit("_", 1)[-1][:2].isdigit():
        s = s.rsplit("_", 1)[0]
    return s.strip("_- ") or project


def _section_from(f) -> Dict[str, Any]:
    sec: Dict[str, Any] = {
        "title": f.title,
        "question": f.question,
        "refs": list(dict.fromkeys(f.refs)),
        "reading": [dict(r) for r in f.reading],
        "assumptions": list(dict.fromkeys(round(float(a), 6) for a in f.assumptions)),
        "falsifier": (getattr(f, "falsifier", "") or
                      f"若下一期数据与「{f.title}」方向相反，本节判断作废。"),
    }
    if f.chart:
        sec["chart"] = f.chart
    if f.table:
        sec["table"] = f.table
    if f.boundary:
        sec["boundary"] = f.boundary
    return sec


def _section_of(f) -> Dict[str, Any]:
    """方法带 Claim 的，走论证层装配（观察→机理→落点→证伪）；
    老方法没有 Claim，仍按原来的方式装配，两条路共用同一个渲染器与同一套门禁。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    if cl is not None:
        return claims.to_section(cl, f.question)
    return _section_from(f)


def _counts(views, sections: List[Dict[str, Any]], picked: List[Any],
            desk) -> Dict[str, int]:
    """P8b：把“计数”登记成可校验集合，替代 <31 的整段放行。"""
    vals: set = set()

    def add(x):
        try:
            n = int(x)
        except (TypeError, ValueError):
            return
        if n >= 0:
            vals.add(n)

    for obj in (getattr(views, "snapshot", {}), getattr(views, "series", {}),
                getattr(views, "wholesale", {}), getattr(views, "origins", []),
                getattr(views, "region", {}), getattr(views, "quotes", {}),
                getattr(views, "momentum", {})):
        try:
            add(len(obj))
        except TypeError:
            pass
    for s in (getattr(views, "series", {}) or {}).values():
        add(len(s))
    add(len(sections))
    add(len(picked))
    for f in picked:
        meta = getattr(f, "meta", None) or {}
        for key in ("rows", "stats"):
            try:
                add(len(meta.get(key) or []))
            except TypeError:
                pass
        ch = getattr(f, "chart", None) or {}
        for key in ("bars", "series"):
            try:
                add(len(ch.get(key) or []))
            except TypeError:
                pass
        tb = getattr(f, "table", None) or {}
        try:
            add(len(tb.get("rows") or []))
        except TypeError:
            pass
    for attr in ("facts", "assumptions", "derived"):
        try:
            add(len(getattr(desk, attr, []) or []))
        except TypeError:
            pass
    try:
        add(len((getattr(desk, "pack", None) or {}).get("sources") or []))
    except TypeError:
        pass
    # 方法把阈值（最少期数/最小样本/窗口）写在 finding.meta 里；这些也是“计数”。
    for f in picked:
        meta = getattr(f, "meta", None) or {}
        cl = meta.get("claim")
        if isinstance(cl, dict):
            for k in ("n", "count", "missing_count"):
                if isinstance(cl.get(k), (int, float)) and not isinstance(cl.get(k), bool):
                    add(int(cl[k]))
        else:
            tags = getattr(cl, "tags", None) or {}
            for k in ("n", "count", "missing_count"):
                if isinstance(tags.get(k), (int, float)) and not isinstance(tags.get(k), bool):
                    add(int(tags[k]))
        for k, v in meta.items():
            key = str(k).lower()
            if not any(t in key for t in ("min", "period", "window", "threshold", "sample", "n_")):
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                add(int(v))
    return {f"count_{i}": v for i, v in enumerate(sorted(vals))}


def _metrics(picked: List[Any], label_of: Dict[str, int]) -> List[Dict[str, Any]]:
    """指标带：只用正文里真的出现的节，避免「第 - 节」这种空洞指向。"""
    out: List[Dict[str, Any]] = []
    for f in picked:
        m = (getattr(f, "meta", None) or {}).get("metric")
        if m:
            out.append(dict(m))
            if len(out) >= 4:
                break
            continue
        idx = label_of.get(f.key, "-")
        if idx in ("-", "", None):
            continue
        rows = (f.meta or {}).get("rows") or (f.meta or {}).get("stats") or []
        if f.key == "economics" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 净利率", "value": r["margin"].p(),
                        "note": f"第 {idx} 节 · 扣损耗冷链",
                        "status": "healthy" if r["v"] > 0 else "critical"})
        elif f.key == "structure" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 区间涨幅", "value": r["ch"].p(),
                        "note": f"第 {idx} 节 · 首末两期",
                        "status": "critical" if r["v"] > 0 else "healthy"})
        elif f.key == "momentum" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 同比", "value": r["yoy"].p(),
                        "note": f"第 {idx} 节 · 最新一期",
                        "status": "critical" if r["y"] > 0 else "healthy"})
        elif f.key == "arbitrage" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 跨市净利",
                        "value": f"{r['nv'].value:+.2f} 元/斤",
                        "note": f"第 {idx} 节 · 扣运费冷链",
                        "status": "healthy" if r["v"] > 0 else "critical"})
        elif f.key == "breakeven" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 保本提价", "value": r["up"].p(),
                        "note": f"第 {idx} 节 · 只覆盖损耗冷链",
                        "status": "watch"})
        elif f.key == "trajectory" and rows:
            r = max(rows, key=lambda x: abs(x["ch"]))
            out.append({"label": f"{r['cat']} 区间变化", "value": f"{r['ch']:+.1f}%",
                        "note": f"第 {idx} 节 · 首末两期",
                        "status": "critical" if r["ch"] < 0 else "healthy"})
        elif f.key == "risk":
            n = (f.meta or {}).get("no_base_count")
            if n:
                out.append({"label": "无批发基准", "value": f"{n} 个",
                            "note": f"第 {idx} 节 · 覆盖缺口", "status": "watch"})
        if len(out) >= 4:
            break
    return out


__all__ = ["_subject", "_section_from", "_section_of", "_counts", "_metrics"]
