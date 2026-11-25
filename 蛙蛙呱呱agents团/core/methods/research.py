# -*- coding: utf-8 -*-
"""core/methods/research —— 研究类方法：规模增长、集中度、单位经济、进入闸门。

**业务无关**（2026-11-25 第三轮清理）：本模块只认「角色 → 指标」映射，
指标 id 全部来自项目 `method_params.yaml` 的 `metric_roles`：

    metric_roles:
      market_size: <项目里的规模指标 id>
      demand:      <需求量指标 id>
      output:      <产量指标 id>
      growth_a:    <第一段增速指标 id>
      growth_b:    <第二段增速指标 id>
      shares:      <份额指标 id>             # 多条事实，每条一个主体
      revenue:     <销售额指标 id>
      yield:       <单位产出耗用（假设）id>
      raw_cost:    <原料成本（假设）id>
      process_cost:<加工成本（假设）id>
      channel_rate:<渠道扣点（假设）id>

未配置角色 → 该方法不挂载（记 gap），**不会退回到某条业务线的默认口径**。
方法只算，不编：规模给 CAGR 与区间，集中度给 CR 与 HHI 上下界，
单位经济给保本价与敏感性，并给「什么条件下停」。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.analysis_methods import Finding, Num, _ids, _table
from core.method_params import current as _params
from core.methods.spec import method, register_need


def _u() -> str:
    """价格单位来自项目 method_params / 数据，不在方法里写死业务单位。"""
    return str(_params().get("price_unit") or "") or "元/单位"


def _roles() -> Dict[str, str]:
    r = _params().get("metric_roles") or {}
    return {str(k): str(v) for k, v in r.items() if v}


def _metric(role: str) -> str:
    return _roles().get(role, "")


def _has(caps, metric: str) -> bool:
    return bool(metric) and any(f.get("metric") == metric for f in caps.desk.facts)


def _facts(ctx, role: str) -> List[Dict[str, Any]]:
    mid = _metric(role)
    if not mid:
        return []
    return [f for f in ctx.desk.facts if f.get("metric") == mid]


def _fact(ctx, role: str) -> Optional[Dict[str, Any]]:
    got = _facts(ctx, role)
    return got[0] if got else None


def _assume(ctx, role: str) -> Optional[Dict[str, Any]]:
    mid = _metric(role)
    if not mid:
        return None
    for a in ctx.desk.assumptions:
        if a.get("metric") == mid:
            return a
    return None


def _num(ctx, role: str, name: str = "", digits: int = 2) -> Optional[Num]:
    f = _fact(ctx, role)
    if not f:
        return None
    c = ctx.cite
    unit = f.get("unit", "")
    val = float(f["value"])
    if unit == "%":                     # 百分比统一存比例，正文用 .p() 显示
        val = val / 100
    return c.n(name or f.get("name", role), val, unit,
               f.get("period", ""), f.get("source_id", ""), digits=digits)


def _an(ctx, role: str, name: str = "", digits: int = 2) -> Optional[Num]:
    a = _assume(ctx, role)
    if not a:
        return None
    c = ctx.cite
    unit = a.get("unit", "")
    val = float(a["value"])
    if unit == "%":
        val = val / 100
    return c.n(name or a.get("name", role), val, unit, "假设", "assumption",
               digits=digits)


def _finding(key: str, title: str, question: str, c, mark: int) -> Finding:
    return Finding(key=key, title=title, question=question, refs=c.since(mark))


def _year(p: Any) -> Optional[int]:
    s = str(p or "")
    for i in range(len(s) - 3):
        if s[i:i + 4].isdigit():
            y = int(s[i:i + 4])
            if 1900 <= y <= 2100:
                return y
    return None


# --------------------------------------------------------------------------- #
# 能力谓词（全部按项目角色解析）
# --------------------------------------------------------------------------- #
register_need("facts.market", lambda c: len(_facts(c, "market_size")) >= 2)
register_need("facts.shares", lambda c: len(_facts(c, "shares")) >= 2)
register_need("facts.cost", lambda c: bool(_metric("revenue") or _metric("raw_cost"))
              and bool(c.desk.assumptions or _facts(c, "revenue")))


# --------------------------------------------------------------------------- #
# 1. 增长：两期 CAGR + 可选两段增速
# --------------------------------------------------------------------------- #
@method("growth", family="research", needs=["facts.market"], produces="规模增长",
        tags=("research", "marketing"), priority=70,
        description="规模 CAGR + 需求/产量 + 两段增速对比")
def m_growth(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    rows = sorted(_facts(ctx, "market_size"),
                  key=lambda f: (_year(f.get("period")), str(f.get("period"))))
    if len(rows) < 2:
        return None
    a, b = rows[0], rows[-1]
    ya, yb = _year(a.get("period")), _year(b.get("period"))
    try:
        va, vb = float(a["value"]), float(b["value"])
    except (TypeError, ValueError):
        return None
    if va <= 0 or vb <= 0:
        return None
    n_years = (yb - ya) if (ya and yb and yb > ya) else (len(rows) - 1)
    n_years = max(1, n_years)
    label = str(b.get("name") or a.get("name") or "规模")
    unit = str(b.get("unit") or a.get("unit") or "")
    v1 = c.n(f"{label} {a.get('period') or '首期'}", va, unit,
             str(a.get("period") or ""), str(a.get("source_id") or ""))
    v2 = c.n(f"{label} {b.get('period') or '末期'}", vb, unit,
             str(b.get("period") or ""), str(b.get("source_id") or ""))
    cagr = (vb / va) ** (1.0 / n_years) - 1
    n_cagr = c.n(f"{n_years} 期 CAGR", cagr, "%")
    demand = _num(ctx, "demand")
    output = _num(ctx, "output")
    ga = _num(ctx, "growth_a")
    gb = _num(ctx, "growth_b")

    title = f"增长：{n_years} 期 CAGR {n_cagr.p()}"
    if ga and gb:
        title += f"，两段增速 {ga.p()} vs {gb.p()}"
    f = _finding("growth", title, "还在长吗？增长来自哪一段？", c, mark)
    f.add(f"{label}从 {v1} {unit}（{a.get('period') or '首期'}）到 {v2} {unit}"
          f"（{b.get('period') or '末期'}），{n_years} 期 CAGR {n_cagr.p()}。",
          _ids(v1, v2, n_cagr))
    if demand and output:
        f.add(f"同期需求 {demand}、产量 {output}；供需缺口决定价格与进口依赖。",
              _ids(demand, output))
    if ga and gb:
        ratio = (ga.value / gb.value) if gb.value else 0
        f.add(f"结构上，A 段增速 {ga.p()} 是 B 段 {gb.p()} 的 {ratio:.1f} 倍——"
              "增长引擎在切换，不能用一个平均增速做规划。", _ids(ga, gb))
        f.chart = {"type": "grouped_bar",
                   "title": f"{ga.p()} vs {gb.p()}：两段增速分化",
                   "subtitle": "同一口径 · 同比 %",
                   "note": "两段增速来自同一批来源，口径需一致",
                   "unit_meta": "同比增速（%）", "source": "事实表",
                   "refs": _ids(ga, gb, n_cagr),
                   "categories": [str(ga.id), str(gb.id)],
                   "series": [{"name": "增速", "values": [round(ga.value, 2),
                                                          round(gb.value, 2)]}]}
    f.table = _table("增长口径", ["指标", "值", "口径"],
                     [[f"{label} 首期", str(v1), unit],
                      [f"{label} 末期", str(v2), unit],
                      ["CAGR", n_cagr.p(), f"{n_years} 期"]]
                     + ([[str(demand), "需求", "事实表"]] if demand else [])
                     + ([[str(output), "产量", "事实表"]] if output else []))
    f.so_what = "用末期结构做规划，不要用平均增速外推；两段分化时优先投增速更快的一段。"
    f.boundary = "CAGR 只覆盖首末两期，中间波动被抹平；口径调整年份需单独核对。"
    return f


# --------------------------------------------------------------------------- #
# 2. 集中度：CR 与 HHI 上下界
# --------------------------------------------------------------------------- #
@method("concentration", family="research", needs=["facts.shares"],
        produces="集中度", tags=("research",), priority=65,
        description="CR2/CR3 与 HHI 上下界（未拆分份额只能给界）")
def m_concentration(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    rows = [f for f in _facts(ctx, "shares") if isinstance(f.get("value"), (int, float))]
    if len(rows) < 2:
        return None
    rows = sorted(rows, key=lambda f: -float(f["value"]))[:8]
    labels = [str(f.get("name") or f.get("entity") or "主体") for f in rows]
    nums = [c.n(nm, float(f["value"]) / 100, "%",
                str(f.get("period") or ""), str(f.get("source_id") or ""))
            for nm, f in zip(labels, rows)]
    top2 = sum(n.value for n in nums[:2]) / 100
    cr = c.n("CR2", top2, "%")
    obs = sum((float(f["value"])) ** 2 for f in rows)
    rest = max(0.0, 100.0 - sum(float(f["value"]) for f in rows))
    hhi_lo = c.d("R10", "sum(share_i^2)", obs, "HHI 下界（未列主体视为无限分散）")
    hhi_hi = c.d("R11", "sum(share_i^2)+rest^2", obs + rest ** 2,
                 "HHI 上界（未列主体视为一家）")
    title = (f"集中度：CR2 {cr.p()}，HHI 在 {hhi_lo}—{hhi_hi} 之间")
    f = _finding("concentration", title, "头部有多强？还能挤进去吗？", c, mark)
    f.add("已列主体合计 " + "、".join(f"{k} {v.p()}" for k, v in zip(labels, nums))
          + f"；未列部分 {rest:.1f}%，所以 HHI 只能给区间。",
          _ids(*nums, cr, hhi_lo, hhi_hi))
    f.table = _table("份额与集中度", ["主体", "份额", "说明"],
                     [[k, v.p(), "已列"] for k, v in zip(labels, nums)]
                     + [["CR2", cr.p(), "前二合计"],
                        ["HHI 区间", f"{hhi_lo}—{hhi_hi}", "未拆分导致区间"]])
    f.chart = {"type": "donut", "title": f"CR2 {cr.p()}，其余 {rest:.1f}% 未拆分",
               "subtitle": "份额（%）", "note": "未列主体合并为区间，不单列",
               "unit_meta": "份额（%）", "source": "事实表",
               "refs": _ids(*nums),
               "items": [{"label": k, "value": round(v.value * 100, 2)}
                         for k, v in zip(labels, nums)]}
    f.so_what = "高集中时不要正面打货架；从细分场景与上游切入。"
    f.boundary = "份额为已披露口径；未列主体未拆分，HHI 只能给上下界。"
    return f


# --------------------------------------------------------------------------- #
# 3. 单位经济
# --------------------------------------------------------------------------- #
@method("unit_econ", family="research", needs=["facts.cost"], produces="单位经济",
        tags=("research", "store"), priority=75,
        description="单价−原料−加工−渠道 → 净利、保本价、原料敏感性")
def m_unit_econ(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    sales = _num(ctx, "revenue", "销售额", 2)
    out = _num(ctx, "output", "产量", 0)
    yld = _an(ctx, "yield", "单位耗用", 1)
    raw = _an(ctx, "raw_cost", "原料成本", 2)
    proc = _an(ctx, "process_cost", "加工成本", 2)
    chan = _an(ctx, "channel_rate", "渠道扣点", 0)
    if not all([sales, out, yld, raw, proc, chan]):
        return None
    if out.value <= 0 or sales.value <= 0:
        return None
    price = c.d("R20", f"{sales.id}/1e8/({out.id}*1000)",
                sales.value / out.value, "单位均价", _u())
    cost = c.d("R21", f"{yld.id}*{raw.id}+{proc.id}",
               yld.value * raw.value + proc.value, "单位成本", _u())
    net = c.d("R22", f"{price.id}*(1-{chan.id})-{cost.id}",
              price.value * (1 - chan.value) - cost.value, "渠道后净利", _u())
    margin = c.d("R23", f"{net.id}/{price.id}", net.value / price.value, "净利率", "%")
    be = c.d("R24", f"{cost.id}/(1-{chan.id})",
             cost.value / (1 - chan.value), "保本单位价", _u())
    raw2 = c.d("R25", f"({yld.id}*{raw.id}*1.2+{proc.id})/(1-{chan.id})",
               (yld.value * raw.value * 1.2 + proc.value) / (1 - chan.value),
               "原料涨20%后的保本价", _u())
    net2 = c.d("R26", f"{price.id}*(1-{chan.id})-({yld.id}*{raw.id}*1.2+{proc.id})",
               price.value * (1 - chan.value) - (yld.value * raw.value * 1.2 + proc.value),
               "原料涨20%后的净利", _u())
    title = (f"单位经济：单价 {price}、成本 {cost}，扣渠道净利 {net}"
             f"（{margin.p()}），保本价 {be}")
    f = _finding("unit_econ", title, "一个单位赚多少？原料涨价会不会打穿？", c, mark)
    f.assumptions = [yld.value, raw.value, proc.value, chan.value]
    f.add(f"单价按 {sales} ÷ {out} 折算 {price} {_u()}；"
          f"成本 {cost} {_u()}（耗用 {yld} × 原料 {raw} + 加工 {proc}）。",
          _ids(price, cost, sales, out, yld, raw, proc))
    f.add(f"扣 {chan.p()} 渠道后净利 {net} {_u()}、净利率 {margin.p()}；"
          f"保本单位价 {be} {_u()}——低于这个价，规模越大亏得越多。",
          _ids(chan, net, margin, be))
    f.add(f"原料涨 20%：保本价升到 {raw2}，净利降到 {net2}；"
          "先锁原料或做价格联动。", _ids(raw2, net2))
    f.table = _table("单位经济（" + _u() + "）", ["项目", "数值", "说明"],
                     [["单价", str(price), "销售额 ÷ 产量"],
                      ["原料成本", f"{yld.value * raw.value:.2f}", f"{yld} × {raw}"],
                      ["加工成本", str(proc), "人工/能耗/包装"],
                      ["单位成本", str(cost), "原料+加工"],
                      ["渠道后净利", str(net), f"扣 {chan.p()}"],
                      ["净利率", margin.p(), "净利 ÷ 单价"],
                      ["保本单位价", str(be), "低于即亏"]])
    f.chart = {"type": "hbar",
               "title": f"净利率 {margin.p()}，原料涨20%后只剩 {net2.value:.2f} {_u()}",
               "subtitle": "单位口径 · 扣渠道后", "note": "不含折旧、固定人力与税",
               "unit_meta": _u(), "source": "事实表 + 显式假设",
               "refs": _ids(price, cost, net, net2),
               "items": [{"label": "单价", "value": round(price.value, 2)},
                         {"label": "单位成本", "value": round(cost.value, 2)},
                         {"label": "净利", "value": round(net.value, 2)},
                         {"label": "涨价后净利", "value": round(net2.value, 2)}]}
    f.so_what = f"单价低于 {be} {_u()} 不做；先锁原料或价格联动，再扩量。"
    f.boundary = ("耗用/原料/加工/渠道均为项目假设，未取得企业台账；"
                  "净利不含设备折旧、固定人力与税。" + " " + _params_note())
    f.actions = [
        {"do": "先锁原料或签价格联动条款，再启动扩量",
         "condition": f"原料成本不高于 {raw} {_u()}，且能锁定 6 个月",
         "stop": f"原料涨 20% 后净利低于 {net2} {_u()}，暂停扩量",
         "refs": _ids(raw, net2, be)},
        {"do": "报价不低于保本单位价",
         "condition": f"单价 ≥ {be} {_u()}，且渠道扣点 ≤ {chan}%",
         "stop": "连续两个月低于保本价，停止接单",
         "refs": _ids(be, chan, price)},
    ]
    f.meta = {"price": price.value, "cost": cost.value, "net": net.value,
              "margin": margin.value, "breakeven": be.value, "net_up20": net2.value}
    ctx.memo["unit_econ"] = f.meta
    return f


def _params_note() -> str:
    from core import method_params as _mp
    return _mp.footnote()


# --------------------------------------------------------------------------- #
# 4. 进入闸门
# --------------------------------------------------------------------------- #
@method("entry_gate", family="research", needs=["facts.cost"], produces="进入闸门",
        tags=("research",), priority=85,
        description="两条进入条件 + 两条杀死条件（可判定）")
def m_entry_gate(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    eco = (ctx.memo or {}).get("unit_econ")
    sizing = (ctx.memo or {}).get("sizing")
    if not eco:
        return None
    price = c.n("单价", eco["price"], _u())
    net = c.n("净利", eco["net"], _u())
    be = c.n("保本价", eco["breakeven"], _u())
    up = c.n("涨价后净利", eco["net_up20"], _u())
    lo = c.n("可服务市场下限", (sizing or {}).get("lo", 0), "亿元")
    hi = c.n("可服务市场上限", (sizing or {}).get("hi", 0), "亿元")
    title = (f"闸门：单价 ≥ {be}、原料涨幅 ≤ 20%"
             + (f"、可服务市场 ≥ {lo} 亿元" if (sizing or {}).get("lo") else "")
             + "，同时满足才进")
    f = _finding("entry_gate", title, "什么条件下做、什么条件下不做？", c, mark)
    f.add(f"进入条件：单价 {price}、净利 {net} {_u()}",
          _ids(price, net))
    f.add(f"杀死条件：原料涨 20% 后净利只剩 {up} {_u()}；单价跌破 {be} {_u()}；"
          "连续两个月低于保本价——命中任一条立即停。", _ids(up, be))
    f.table = _table("进入与退出闸门", ["类型", "判据", "动作"],
                     [["进入", f"单价 ≥ {be.value:.2f} {_u()}", "报价"],
                      ["进入", f"净利率 ≥ {net.value / price.value * 100:.0f}%"
                       if price.value else "净利率 ≥ 门槛", "扩量"],
                      ["退出", f"原料涨 20% 后净利 < {up.value:.2f} {_u()}", "暂停"],
                      ["退出", f"单价 < {be.value:.2f} {_u()}", "停止接单"]])
    f.actions = [
        {"do": "先小规模验证需求，不重资产投入",
         "condition": "拿到可核实的意向订单后再扩产",
         "stop": "约定窗口内拿不到意向订单，停止投入",
         "refs": _ids(lo, hi, price, net)},
        {"do": "与客户签价格联动条款",
         "condition": "原料波动 ±10% 时单价可同向调整",
         "stop": "客户拒绝联动且原料上行，退出该客户",
         "refs": _ids(up, be, net)},
    ]
    f.so_what = "先验证再扩产：把固定成本风险留到最后。"
    f.boundary = "闸门阈值来自本轮测算与假设，不是行业标准；执行前需用真实报价校准。"
    return f
