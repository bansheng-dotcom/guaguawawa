# -*- coding: utf-8 -*-
"""core/report_thesis —— 报告纲领（v11：只保留 analysis 一条）。

历史：v5 曾有 22 个业务纲领（research / operations / remediation / chain / forecast /
growth / product / support / people / sre / marketing / sku / store / market_entry /
market / cheese_* × 6 / analysis），每个纲领自带 order/opening/actions，
导致「同一批证据出 22 种报告」。v10 起 `THESES` 只剩 `analysis`，
但那 21 个纲领的字典与分支仍留在文件里（约 600 行不可达代码）。

v11（P1）按 `交付/报告产线重构-SOP-2026-11-18.md` 把它们删干净：

- 只保留 `analysis` 的 order（方法清单）与 ask（报告要回答什么）；
- `infer()` 恒返回 `"analysis"`：**报告类型不再是入口参数，域判定交给编排器**；
- `resolve/standfirst/summary/actions` 只服务 analysis 一条路；
- `opening()` 删除（开篇由 P2 的叙事引擎生成）。

外部消费者（改造后）：
    core/report/report_cli.py    plan 子命令用 infer() 推断纲领
    core/report_compose.py 用 THESES / infer / resolve / summary（build 已封口，P2.4 删除）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 唯一纲领：analysis —— 不绑定业务，按「问题/数据/推导/风险/动作」装配
# --------------------------------------------------------------------------- #
THESES: Dict[str, Dict[str, Any]] = {
    "analysis": {
        "label": "专业分析",
        "doc_name": "专业分析报告",
        "doc_type": "专业分析报告",
        "order": [
            # 市场与结构
            "size", "growth", "structure", "demand", "volume", "channel", "region",
            "supply", "policy", "consistency", "coverage", "concentration",
            # 价格与经营
            "momentum", "trajectory", "contribution", "economics", "transmission",
            "arbitrage", "breakeven", "forecast", "risk", "sample",
            "unit_econ", "entry_gate",
            # 通用表族（订单/评价/投放/工单/SLA/招聘/容量/故障/商品/单店）
            "funnel", "retention", "rfm", "roi", "payment_mix", "reviews",
            "priority", "sla", "capacity", "headcount", "incidents", "sku", "store",
        ],
        "opening": "分析结论",
        "ask": "这份分析回答什么、数据支持哪些判断、哪些不能下、下一步做什么？",
    },
}

DEFAULT_THESIS = "analysis"


def infer(intent: str, profile: Optional[Dict[str, Any]] = None) -> str:
    """意图 → 纲领。v11 恒为 analysis：业务域由编排器判定，不再由纲领承载。

    保留函数签名，因为 `report plan` 与旧调用方仍会传入 intent/profile；
    参数故意不用，避免调用方以为「换个词就能换报告类型」。
    """
    return "analysis"


def resolve(thesis: str, findings: Dict[str, Any]) -> Tuple[List[Any], List[str]]:
    """按纲领 order 取节；缺的记入口径缺口，不补形容词。"""
    spec = THESES.get(thesis) or THESES[DEFAULT_THESIS]
    picked: List[Any] = []
    missing: List[str] = []
    for key in spec["order"]:
        f = findings.get(key)
        if f is None:
            missing.append(key)
        else:
            picked.append(f)
    return picked, missing


def _num(f, attr: str, default=None):
    """从 finding.meta 里安全取数。"""
    meta = getattr(f, "meta", {}) or {}
    return meta.get(attr, default)


def _tags(f) -> Dict[str, Any]:
    """claim 驱动的 finding 把量化标签放在 meta['claim'].tags。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    return (getattr(cl, "tags", None) or {}) if cl is not None else {}


def _refs(f) -> List[str]:
    """取本节可用的证据 id：claim 的 refs 优先（已含本节全部登记数字）。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    if cl is not None and getattr(cl, "refs", None):
        return list(cl.refs)
    return list(getattr(f, "refs", None) or [])


def standfirst(thesis: str, findings: Dict[str, Any]) -> str:
    """首段结论：取前两条 finding 的标题（标题即判断、带数字）。"""
    picked, _ = resolve(thesis, findings)
    if not picked:
        return "本轮没有命中可复算的判断，报告只保留缺口。"
    head = picked[0].title
    tail = f"；{picked[1].title.split('：', 1)[-1]}" if len(picked) > 1 else ""
    return f"{head}{tail}。"


def summary(thesis: str, findings: Dict[str, Any]) -> List[str]:
    """分条结论：直接取 finding 标题（标题即结论、带数字）。"""
    picked, _ = resolve(thesis, findings)
    out = [f.title for f in picked[:4]]
    if len(out) < 2:
        out.append("本节只保留可复算判断；未命中的方法记在缺口，不用估算补。")
    return out


def actions(thesis: str, findings: Dict[str, Any]) -> List[Dict[str, str]]:
    """动作与停止条件：由 finding 自带的 actions 触发，缺了就明说补数。"""
    out: List[Dict[str, str]] = []
    picked, _ = resolve(thesis, findings)
    for f in picked:
        for a in (getattr(f, "actions", None) or []):
            out.append(a)
            if len(out) >= 4:
                return out
    if out:
        return out
    return [{"do": "先补关键表再执行",
             "condition": "至少补齐一张能复算的主表",
             "stop": "补数两周仍未齐，暂停本类报告",
             "refs": []}]


def _join(items: List[str], limit: int = 3) -> str:
    return "、".join(items[:limit]) + ("等" if len(items) > limit else "")


__all__ = ["THESES", "DEFAULT_THESIS", "infer", "resolve", "standfirst",
           "summary", "actions"]
