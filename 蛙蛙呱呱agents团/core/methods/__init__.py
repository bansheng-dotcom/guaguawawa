# -*- coding: utf-8 -*-
"""core/methods —— 方法注册表的装配层。

实现分两类：
- 价格/成本类：沿用 `core/analysis_methods.py` 的函数（它们已经验证过口径），
  这里只补「能力声明」，让调度器能按数据自动挂载；
- 通用表类：`core/methods/generic.py`，订单/评价/履约/投放/优先级/容量/故障/招聘/商品/单店。

对外只暴露：
    plan(desk, views, profile, thesis_key)  → 挂载计划
    run(plan_obj, ctx)                      → 执行 + 缺口
    catalog()                               → 能力清单
    register_need / Caps                    → 给新方法扩展用
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.methods import spec
from core.methods.spec import (Caps, MethodSpec, REGISTRY, catalog, method,  # noqa: F401
                               plan as _plan, register, register_need, run as _run)
from core import analysis_methods as A

# --------------------------------------------------------------------------- #
# 价格类能力谓词
# --------------------------------------------------------------------------- #
register_need("price.retail", lambda c: bool(c.views.snapshot))
register_need("price.wholesale", lambda c: len(c.views.wholesale) >= 3)
register_need("price.origin", lambda c: bool(c.views.origins))
register_need("price.region", lambda c: len(c.views.region) >= 2 or len(c.views.quotes) >= 4)
register_need("price.momentum", lambda c: sum(
    1 for m in c.views.momentum.values() if "mom" in m and "yoy" in m) >= 3)
register_need("price.series2", lambda c: any(len(s) >= 2 for s in c.views.series.values()))
register_need("price.series3", lambda c: any(len(s) >= 3 for s in c.views.series.values()))
register_need("price.series4", lambda c: sum(
    1 for s in c.views.series.values() if len(s) >= 4) >= 2)
register_need("price.economics", lambda c: len(
    [k for k in c.views.snapshot if k in c.views.wholesale]) >= 3)


def _reg(key: str, fn, family: str, needs, produces: str, tags=(), priority=50,
         optional=True, description: str = "") -> None:
    register(MethodSpec(key=key, fn=fn, family=family, needs=tuple(needs),
                        produces=produces, tags=tuple(tags), priority=priority,
                        optional=optional, description=description))


_reg("structure", A.m_structure, "price", ["price.series2"], "横截面分化",
     ("research", "operations"), 55, description="品类间首末变化与离散度")
_reg("momentum", A.m_momentum, "price", ["price.momentum"], "环比/同比节奏",
     ("research", "operations"), 56, description="环比与同比的四象限")
_reg("trajectory", A.m_trajectory, "price", ["price.series3"], "时间轨迹与波动",
     ("research", "forecast"), 57, description="首末、CV、回撤、引擎复核")
_reg("contribution", A.m_contribution, "price", ["price.series2"], "涨跌贡献",
     ("research", "remediation"), 45, description="涨端/跌端毛变动")
_reg("economics", A.m_economics, "price", ["price.economics"], "单位经济",
     ("operations", "remediation", "research"), 70, description="加价率→扣损耗冷链→净毛利")
_reg("transmission", A.m_transmission, "chain", ["price.origin", "price.wholesale"],
     "上下游传导", ("research", "operations", "chain"), 68, description="产地→批发→零售三段价差")
_reg("arbitrage", A.m_arbitrage, "chain", ["price.region"], "跨市场价差",
     ("research", "operations", "chain"), 62, description="跨市净利与配额")
_reg("breakeven", A.m_breakeven, "price", ["price.economics"], "保本线",
     ("operations", "remediation"), 58, description="保本提价与保本直采占比")
_reg("forecast", A.m_forecast, "price", ["price.series4"], "趋势外推",
     ("forecast",), 60, description="最小二乘外推＋残差区间")
_reg("risk", A.m_risk, "risk", ["price.series2"], "风险与缺口",
     ("research", "operations", "remediation", "chain"), 40, description="期数、CV、回撤、基准价")
_reg("sample", A.m_sample, "risk", ["price.series2"], "样本充分性",
     ("research", "operations"), 35, description="Wilson 区间与所需样本量")

# 通用表方法（由 generic 模块的 @method 装饰器注册）
from core.methods import generic  # noqa: E402,F401  仅为触发注册
# 新业务研究方法（facts.json 驱动）
from core.methods import research  # noqa: E402,F401
# v7 区域消费市场研究方法（带来源事实表驱动）
from core.methods import market  # noqa: E402,F401
# v8 奶酪零食（特色乳制品零食）方法族（带来源事实表 + 电商报价驱动）
# [v12 退场] from core.methods import cheese  # noqa: E402,F401
# v11 调味料（调味品）方法族（公开事实表驱动：规模区间/品类结构/渠道场景）
# [v12 退场] from core.methods import seasoning  # noqa: E402,F401

# 方法别名：同一实现，不同纲领里叫法不同
_ALIAS = {
    "cost": "economics", "margin": "economics",
    "spread": "arbitrage", "chain": "transmission",
}
for alias, target in _ALIAS.items():
    if target in REGISTRY and alias not in REGISTRY:
        s = REGISTRY[target]
        register(MethodSpec(key=alias, fn=s.fn, family=s.family, needs=s.needs,
                            produces=s.produces, tags=s.tags,
                            priority=s.priority, optional=s.optional,
                            description=s.description))


def plan(desk, views, profile: Dict[str, Any], thesis_key: str = "research") -> Dict[str, Any]:
    from core import report_thesis
    thesis = report_thesis.THESES.get(thesis_key) or {}
    p = _plan(desk, views, profile, thesis)
    p["thesis"] = thesis_key
    return p


def run(plan_obj: Dict[str, Any], ctx):
    findings, gaps = _run(plan_obj, ctx)
    # 证据台账最后跑：它要引用前面所有 finding
    led = A.m_ledger(ctx, list(findings.values()))
    if led:
        findings["ledger"] = led
    # P11：逐方法专属 falsifier（没有的留空，report_compose 会补方向反转兜底）
    for key, f in findings.items():
        if not getattr(f, "falsifier", ""):
            f.falsifier = A.FALSIFIERS.get(key, "")
    return findings, gaps


__all__ = ["plan", "run", "catalog", "REGISTRY", "Caps", "MethodSpec", "method",
           "register", "register_need"]
