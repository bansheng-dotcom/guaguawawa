# -*- coding: utf-8 -*-
"""core/methods/research —— 新业务研究类方法：规模多路径、集中度、增长、单位经济、进入闸门。

与价格/表类方法的区别：它们吃的是「带来源的事实表」（`data/facts.json`），
每条事实都有 id、单位、期、来源 id、证据等级；假设单独放 `assumptions`，
报告里必须声明，不能混进事实。

方法只算，不编：
- 规模至少给两条路径 + 区间 + 差异倍数，不给单点；
- 集中度给 CR2 与 HHI 上下界（「其他」未拆分时只能给界）；
- 单位经济给保本价与敏感性，并给「什么条件下停」。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.analysis_methods import Finding, Num, _ids, _table
from core.methods.spec import method, register_need


def _u() -> str:
    """价格单位来自项目 method_params / 数据，不在方法里写死业务单位。"""
    from core import method_params as _mp
    return str(_mp.current().get("price_unit") or "") or "元/单位"

# --------------------------------------------------------------------------- #
# 能力谓词
# --------------------------------------------------------------------------- #
def _has(caps, metric: str) -> bool:
    return any(f.get("metric") == metric for f in caps.desk.facts)


register_need("facts.market", lambda c: _has(c, "cn_retail") and _has(c, "cn_demand"))
register_need("facts.region", lambda c: _has(c, "nm_value") and _has(c, "xm_sales"))
register_need("facts.shares", lambda c: _has(c, "share_miaoke"))
register_need("facts.cost", lambda c: _has(c, "raw_price") or bool(c.desk.assumptions))


def _fact(ctx, metric: str) -> Optional[Dict[str, Any]]:
    for f in ctx.desk.facts:
        if f.get("metric") == metric:
            return f
    return None


def _assume(ctx, metric: str) -> Optional[Dict[str, Any]]:
    for a in ctx.desk.assumptions:
        if a.get("metric") == metric:
            return a
    return None


def _num(ctx, metric: str, name: str = "", digits: int = 2) -> Optional[Num]:
    f = _fact(ctx, metric)
    if not f:
        return None
    c = ctx.cite
    unit = f.get("unit", "")
    val = float(f["value"])
    if unit == "%":                     # 百分比统一存比例，正文用 .p() 显示
        val = val / 100
    return c.n(name or f.get("name", metric), val, unit,
               f.get("period", ""), f.get("source_id", ""), digits=digits)


def _an(ctx, metric: str, name: str = "", digits: int = 2) -> Optional[Num]:
    a = _assume(ctx, metric)
    if not a:
        return None
    c = ctx.cite
    unit = a.get("unit", "")
    val = float(a["value"])
    if unit == "%":
        val = val / 100
    return c.n(name or a.get("name", metric), val, unit, "假设", "assumption",
               digits=digits)


def _finding(key: str, title: str, question: str, c, mark: int) -> Finding:
    return Finding(key=key, title=title, question=question, refs=c.since(mark))


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 2. 增长：两段增速与引擎切换
# --------------------------------------------------------------------------- #
@method("growth", family="research", needs=["facts.market"], produces="增长与引擎切换",
        tags=("research", "marketing"), priority=70,
        description="零售额 CAGR、供需增速、B 端 vs C 端增速")
def m_growth(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    ret22 = _fact(ctx, "cn_retail")
    rets = [f for f in ctx.desk.facts if f.get("metric") == "cn_retail"]
    if len(rets) < 2:
        return None
    r17 = [f for f in rets if f.get("period") == "2017"]
    r22 = [f for f in rets if f.get("period") == "2022"]
    if not r17 or not r22:
        return None
    v17 = c.n("全国奶酪零售额", float(r17[0]["value"]), "亿元", "2017", "S5")
    v22 = c.n("全国奶酪零售额", float(r22[0]["value"]), "亿元", "2022", "S5")
    cagr = ((v22.value / v17.value) ** (1 / 5) - 1) * 100
    n_cagr = c.n("五年 CAGR", cagr / 100, "%")
    demand = _num(ctx, "cn_demand", "2025 需求量", 1)
    output = _num(ctx, "cn_output", "2025 国产产量", 1)
    g_b2b = _num(ctx, "g_b2b", "餐饮工业增速", 2)
    g_ready = _num(ctx, "g_ready", "即食营养增速", 2)
    if not all([demand, output, g_b2b, g_ready]):
        return None
    title = (f"增长：五年 CAGR {n_cagr.p()}，但引擎已切换——"
             f"B 端 {g_b2b.p()} vs C 端 {g_ready.p()}")
    f = _finding("growth", title, "行业还在长吗？增长来自哪一端？", c, mark)
    f.add(f"全国奶酪零售额从 {v17} 亿元（2017）到 {v22} 亿元（2022），"
          f"五年 CAGR {n_cagr.p()}；2025 年需求 {demand} 万吨、国产 {output} 万吨。",
          _ids(v17, v22, n_cagr, demand, output))
    f.add(f"结构上，餐饮工业增速 {g_b2b.p()} 是即食营养 {g_ready.p()} 的 "
          f"{g_b2b.value / g_ready.value:.1f} 倍；C 端即食已经进入存量竞争，"
          "新进入者从 B 端起量更顺。", _ids(g_b2b, g_ready))
    f.add("进口依存度 46%、原制自给率不足 20%：国产替代是长期主线，"
          "但替代发生在供应链与 B 端，不在货架前端。",
          _ids(_num(ctx, "import_dep", "进口依存度", 0), _num(ctx, "raw_self", "原制自给率上限", 0)))
    f.table = _table("增长口径", ["指标", "值", "口径"],
                     [["零售额 2017", str(v17), "亿元"],
                      ["零售额 2022", str(v22), "亿元"],
                      ["五年 CAGR", n_cagr.p(), "2017—2022"],
                      ["2025 需求", f"{demand} 万吨", "全国"],
                      ["2025 国产", f"{output} 万吨", "全国"],
                      ["餐饮工业增速", g_b2b.p(), "妙可 2024"],
                      ["即食营养增速", g_ready.p(), "妙可 2024"]])
    f.chart = {"type": "grouped_bar",
               "title": f"B 端 {g_b2b.p()} vs C 端 {g_ready.p()}：增长引擎已切换",
               "subtitle": "2024 年 · 餐饮工业 vs 即食营养 · 同比 %",
               "note": "两项增速来自单一上市公司，不代表全行业",
               "unit_meta": "同比增速（%）", "source": "S2/S5",
               "refs": _ids(g_b2b, g_ready, n_cagr),
               "categories": ["餐饮工业", "即食营养"],
               "series": [{"name": "2024 增速", "values": [round(g_b2b.value, 2),
                                                           round(g_ready.value, 2)]}]}
    f.so_what = "先做 B 端（烘焙/茶饮/快餐）与礼盒，C 端即食等供应链和品牌预算到位再进。"
    f.boundary = "CAGR 用 2017—2022 零售额，不含 2023 后口径调整；B/C 增速来自单一上市公司，不代表全行业。"
    return f


# --------------------------------------------------------------------------- #
# 3. 集中度
# --------------------------------------------------------------------------- #
@method("concentration", family="research", needs=["facts.shares"],
        produces="集中度", tags=("research",), priority=65,
        description="CR2/CR4/HHI 上下界（其他未拆分时只能给界）")
def m_concentration(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    mk = _num(ctx, "share_miaoke", "妙可蓝多份额", 1)
    yl = _num(ctx, "share_yili", "伊利份额", 1)
    ot = _num(ctx, "share_other", "其他品牌合计", 1)
    if not all([mk, yl, ot]):
        return None
    cr2 = mk.value + yl.value
    n_cr2 = c.n("CR2", cr2 / 100, "%")
    hhi_frag = c.d("R10", f"{mk.id}*{mk.id}+{yl.id}*{yl.id}",
                   mk.value ** 2 + yl.value ** 2, "HHI 下界（其他视为无限分散）")
    hhi_one = c.d("R11", f"{mk.id}*{mk.id}+{yl.id}*{yl.id}+{ot.id}*{ot.id}",
                  mk.value ** 2 + yl.value ** 2 + ot.value ** 2,
                  "HHI 上界（其他视为一家）")
    title = (f"集中度：CR2 {n_cr2.p()}，HHI 在 {hhi_frag}—{hhi_one} 之间，"
             "典型双寡头")
    f = _finding("concentration", title,
                 "这个行业还能挤进去吗？头部有多强？", c, mark)
    f.add(f"妙可蓝多 {mk.p()} + 伊利 {yl.p()}，CR2 {n_cr2.p()}；"
          f"『其他』合计 {ot.p()}，但未拆分，所以 HHI 只能给区间。",
          _ids(mk, yl, ot, n_cr2, hhi_frag, hhi_one))
    f.add(f"HHI 下界 {hhi_frag}、上界 {hhi_one}：无论取哪一端都落在高集中区间；"
          "新进入者只能在细分场景（区域特色、B 端定制）找缝。",
          _ids(hhi_frag, hhi_one))
    f.table = _table("份额与集中度", ["主体", "份额", "说明"],
                     [["妙可蓝多", mk.p(), "全国第一"],
                      ["伊利", yl.p(), "渠道协同"],
                      ["其他", ot.p(), "未拆分"],
                      ["CR2", n_cr2.p(), "双寡头"],
                      ["HHI 区间", f"{hhi_frag}—{hhi_one}", "未拆分导致区间"]])
    f.chart = {"type": "donut", "title": f"CR2 {n_cr2.p()}，其余 {ot.p()} 分散",
               "subtitle": "2025H1 全国奶酪市场品牌份额",
               "note": "「其他」未拆分，HHI 只给区间",
               "unit_meta": "份额（%）", "source": "S2（2025H1）",
               "refs": _ids(mk, yl, ot),
               "items": [{"label": "妙可蓝多", "value": mk.value},
                         {"label": "伊利", "value": yl.value},
                         {"label": "其他", "value": ot.value}],
               "series": [{"name": "份额", "values": [mk.value, yl.value, ot.value]}]}
    f.so_what = "不要正面打全国货架；用『原产地 + 区域公用品牌』做差异化，先进 B 端与礼盒。"
    f.boundary = "份额为全渠道零售口径，不含工业原料；『其他』未拆分，HHI 只能给上下界。"
    return f


# --------------------------------------------------------------------------- #
# 4. 单位经济
# --------------------------------------------------------------------------- #
@method("unit_econ", family="research", needs=["facts.cost"], produces="单位经济",
        tags=("research", "store"), priority=75,
        description="出厂价−原料−加工−渠道 → 净利、保本价、原料敏感性")
def m_unit_econ(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    xm_sales = _num(ctx, "xm_sales", "锡盟销售额", 2)
    xm_out = _num(ctx, "xm_output", "锡盟产量", 0)
    yld = _an(ctx, "yield_ratio", "出成率（kg 奶/kg 奶酪）", 1)
    raw = _an(ctx, "raw_price", "原料到场价", 2)
    proc = _an(ctx, "process_cost", "加工包装成本", 2)
    chan = _an(ctx, "channel_rate", "渠道扣点", 0)
    if not all([xm_sales, xm_out, yld, raw, proc, chan]):
        return None
    price = c.d("R20", f"{xm_sales.id}*1e8/({xm_out.id}*1000)",
                xm_sales.value * 1e8 / (xm_out.value * 1000), "出厂均价", "元/kg")
    cost = c.d("R21", f"{yld.id}*{raw.id}+{proc.id}",
               yld.value * raw.value + proc.value, "单位成本", "元/kg")
    net = c.d("R22", f"{price.id}*(1-{chan.id})-{cost.id}",
              price.value * (1 - chan.value) - cost.value, "渠道后净利", "元/kg")
    margin = c.d("R23", f"{net.id}/{price.id}", net.value / price.value,
                 "净利率", "%")
    be = c.d("R24", f"{cost.id}/(1-{chan.id})",
             cost.value / (1 - chan.value), "保本出厂价", "元/kg")
    raw2 = c.d("R25", f"({yld.id}*{raw.id}*1.2+{proc.id})/(1-{chan.id})",
               (yld.value * raw.value * 1.2 + proc.value) / (1 - chan.value),
               "原料涨20%后的保本价", "元/kg")
    net2 = c.d("R26", f"{price.id}*(1-{chan.id})-({yld.id}*{raw.id}*1.2+{proc.id})",
               price.value * (1 - chan.value) - (yld.value * raw.value * 1.2 + proc.value),
               "原料涨20%后的净利", "元/kg")
    title = (f"单位经济：出厂价 {price} {_u()}、成本 {cost} 元，"
             f"扣渠道净利 {net} 元（{margin.p()}），保本价 {be} 元")
    f = _finding("unit_econ", title,
                 "一公斤奶酪赚多少钱？原料涨价会不会直接打穿？", c, mark)
    f.assumptions = [yld.value, raw.value, proc.value, chan.value]
    f.add(f"出厂价按锡盟 {xm_sales} 亿元 ÷ {xm_out} 吨折算 {price} {_u()}；"
          f"成本 {cost} {_u()}（{yld} 公斤奶 × {raw} 元 + 加工 {proc} 元）。",
          _ids(price, cost, xm_sales, xm_out, yld, raw, proc))
    f.add(f"扣 {chan.p()} 渠道后净利 {net} {_u()}、净利率 {margin.p()}；"
          f"保本出厂价 {be} {_u()}——低于这个价，规模越大亏得越多。",
          _ids(chan, net, margin, be))
    f.add(f"原料涨 20%：保本价升到 {raw2} 元、净利降到 {net2} 元；"
          "这条业务对奶价高度敏感，必须先锁奶源或做价格联动条款。",
          _ids(raw2, net2))
    f.table = _table("单位经济（" + _u() + "）", ["项目", "数值", "说明"],
                     [["出厂价", str(price), "锡盟均价折算"],
                      ["原料成本", f"{yld.value * raw.value:.2f}", f"{yld}kg × {raw}元"],
                      ["加工包装", str(proc), "人工/能耗/包装"],
                      ["单位成本", str(cost), "原料+加工"],
                      ["渠道后净利", str(net), f"扣 {chan.p()}"],
                      ["净利率", margin.p(), "净利 ÷ 出厂价"],
                      ["保本出厂价", str(be), "低于即亏"]])
    f.chart = {"type": "hbar",
               "title": f"净利率 {margin.p()}，原料涨20%后只剩 {net2.value:.2f} {_u()}",
               "subtitle": "锡盟均价折算 · 每公斤 · 扣渠道后口径",
               "note": "不含折旧、固定人力与税",
               "unit_meta": "" + _u() + "", "source": "S1/S4 + 显式假设",
               "refs": _ids(price, cost, net, net2),
               "bars": [{"label": "出厂价", "value": round(price.value, 2)},
                        {"label": "单位成本", "value": round(cost.value, 2)},
                        {"label": "净利", "value": round(net.value, 2)},
                        {"label": "涨价后净利", "value": round(net2.value, 2)}]}
    f.so_what = ("出厂价低于 48 " + _u() + "不进；先签奶源或价格联动，再谈扩量。")
    f.boundary = ("出成率 8:1、奶价 3.0 " + _u() + "、加工 12 元、渠道 25% 均为 C 级假设，"
                  "未取得企业台账；净利不含设备折旧、人力固定成本与税。")
    f.actions = [
        {"do": "先锁奶源或签价格联动条款，再启动量产",
         "condition": f"到场奶价不高于 {raw} {_u()}，且能锁定 6 个月",
         "stop": f"原料涨 20% 后净利低于 {net2} {_u()}，即暂停扩量",
         "refs": _ids(raw, net2, be)},
        {"do": "出厂价按不低于保本价报价",
         "condition": f"出厂价 ≥ {be} {_u()}，且渠道扣点 ≤ {chan}%",
         "stop": "连续两个月出厂价低于保本价，停止接单",
         "refs": _ids(be, chan, price)},
    ]
    f.meta = {"price": price.value, "cost": cost.value, "net": net.value,
              "margin": margin.value, "breakeven": be.value, "net_up20": net2.value}
    ctx.memo["unit_econ"] = f.meta
    return f


# --------------------------------------------------------------------------- #
# 5. 进入闸门
# --------------------------------------------------------------------------- #
@method("entry_gate", family="research", needs=["facts.cost"], produces="进入闸门",
        tags=("research",), priority=85,
        description="三条杀死条件 + 两条进入条件（可判定）")
def m_entry_gate(ctx) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    eco = (ctx.memo or {}).get("unit_econ")
    sizing = (ctx.memo or {}).get("sizing")
    if not eco:
        return None
    price = c.n("出厂价", eco["price"], "元/kg")
    net = c.n("净利", eco["net"], "元/kg")
    be = c.n("保本价", eco["breakeven"], "元/kg")
    up = c.n("涨价后净利", eco["net_up20"], "元/kg")
    lo = c.n("可服务市场下限", (sizing or {}).get("lo", 0), "亿元")
    hi = c.n("可服务市场上限", (sizing or {}).get("hi", 0), "亿元")
    title = (f"闸门：出厂价 ≥ {be} {_u()}、原料涨幅 ≤ 20%、"
             f"可服务市场 ≥ {lo} 亿元，三条同时满足才进")
    f = _finding("entry_gate", title,
                 "什么条件下做、什么条件下不做？", c, mark)
    f.add(f"进入条件：可服务市场 {lo}—{hi} 亿元、出厂价 {price} 元、净利 {net} {_u()}；"
          "三者任一不成立，先做代工/贴牌验证，不建厂。", _ids(lo, hi, price, net))
    f.add(f"杀死条件：原料涨 20% 后净利只剩 {up} {_u()}；出厂价跌破 {be} {_u()}；"
          "连续两个月低于保本价——命中任一条立即停。", _ids(up, be))
    f.table = _table("进入与退出闸门", ["类型", "判据", "动作"],
                     [["进入", f"可服务市场 ≥ {lo.value:.0f} 亿元", "立项"],
                      ["进入", f"出厂价 ≥ {be.value:.1f} {_u()}", "报价"],
                      ["进入", f"净利率 ≥ {net.value / price.value * 100:.0f}%", "扩量"],
                      ["退出", f"原料涨 20% 后净利 < {up.value:.1f} 元", "暂停"],
                      ["退出", f"出厂价 < {be.value:.1f} 元", "停止接单"]])
    f.actions = [
        {"do": "先以代工/贴牌方式验证 B 端订单，不建厂",
         "condition": "拿到 3 家以上 B 端意向订单，合计年需求 ≥ 100 吨",
         "stop": "6 个月拿不到 100 吨意向，停止投入",
         "refs": _ids(lo, hi, price, net)},
        {"do": "与餐饮/烘焙客户签价格联动条款",
         "condition": "奶价波动 ±10% 时出厂价可同向调整",
         "stop": "客户拒绝联动且奶价上行，退出该客户",
         "refs": _ids(up, be, net)},
    ]
    f.so_what = "先验证再建厂：用代工跑通 B 端，把固定资产风险留到最后。"
    f.boundary = "闸门阈值来自本轮测算与假设，不是行业标准；执行前需用真实报价校准。"
    return f
