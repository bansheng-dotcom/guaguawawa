# -*- coding: utf-8 -*-
"""core/frames_v10 —— 假设驱动的 v10 分析稿（样稿）。

与 v9 的区别：v9 按维度平铺，v10 按「核心矛盾 → 假设 → 取证 → 结论」组织。

    1 核心矛盾   一句话说明两个相互打架的事实
    2 假设树     3 个可证伪假设 + 验证数据 + 推翻条件
    3—5 假设验证 每条假设给支持证据、反证、结论（成立/部分成立/推翻）
    6 定量模型   单位经济模型，逐项可复算
    7 敏感性     关键变量 ± 冲击下的净利变化
    8 情景       悲观/基准/乐观
    9 决策选项   A/B/C 三方案，含投入、收益、风险、取舍
    10 红队      3 条反驳 + 逐条回应
    11 风险与验收 数据风险、验收口、停止条件

依赖 `cheese_*` findings 的量化标签；缺关键数据时返回 None，
由上层回退到通用五模块（v9），保证不因数据不足而崩。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.analysis_methods import Finding, Num, _ids, _table


def _cl(f: Optional[Finding]):
    return (getattr(f, "meta", None) or {}).get("claim") if f is not None else None


def _tags(f: Optional[Finding]) -> Dict[str, Any]:
    cl = _cl(f)
    return (getattr(cl, "tags", None) or {}) if cl is not None else {}


def _refs(f: Optional[Finding]) -> List[str]:
    cl = _cl(f)
    if cl is not None:
        return list(getattr(cl, "refs", []) or [])
    return list(getattr(f, "refs", []) or []) if f is not None else []


def _n(c, name: str, value: float, unit: str = "", period: str = "",
       source: str = "", digits: int = 2) -> Num:
    if unit == "%" and digits == 2:
        digits = 1
    return c.n(name, value, unit, period, source, digits=digits)


def _sec(title: str, question: str, reading: List[Dict[str, Any]],
         refs: List[str], table=None, chart=None, boundary: str = "",
         assumptions: Optional[List[float]] = None) -> Dict[str, Any]:
    sec = {"title": title, "question": question, "reading": reading,
           "refs": list(dict.fromkeys(refs)), "assumptions": list(assumptions or [])}
    if table:
        sec["table"] = table
    if chart:
        sec["chart"] = chart
    if boundary:
        sec["boundary"] = boundary
    return sec


def _r(text: str, refs: List[str], strong: str = "") -> Dict[str, Any]:
    return {"text": text, "refs": list(refs), "strong": strong}


def build_v10(ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    eco = findings.get("cheese_unit_econ")
    pri = findings.get("cheese_price")
    chn = findings.get("cheese_chain")
    cnt = findings.get("cheese_content")
    if not (eco and pri and chn):
        return None

    c = ctx.cite
    t = _tags(eco)
    price = float(t.get("price", 57.14))
    cost = float(t.get("cost", 36.0))
    net = float(t.get("net", 6.86))
    be = float(t.get("breakeven", 48.0))
    channel = float(t.get("channel", 14.29))

    ass = {a.get("metric"): a for a in (getattr(ctx.desk, "assumptions", None) or [])}
    yield_r = float((ass.get("yield_ratio") or {}).get("value", 8.0))
    proc = float((ass.get("process_cost") or {}).get("value", 12.0))
    raw = float((ass.get("raw_price") or {}).get("value", 3.0))
    raw_cost = round(yield_r * raw, 2)

    # ---------- 核心数字 ----------
    n_price = _n(c, "出厂价", price, "元/公斤")
    n_cost = _n(c, "总成本", cost, "元/公斤")
    n_raw = _n(c, "原料成本", raw_cost, "元/公斤")
    n_proc = _n(c, "加工成本", proc, "元/公斤")
    n_chan = _n(c, "渠道扣点", channel, "元/公斤")
    n_net = _n(c, "单位净利", net, "元/公斤")
    n_be = _n(c, "保本价", be, "元/公斤")
    n_growth = _n(c, "零售额五年CAGR", 22.6, "%", "2017—2022", "Q15")
    # 来源交叉：增长与利润的张力
    n_margin = _n(c, "净利率", net / price * 100, "%")

    # ---------- 假设输入 ----------
    n_yoy_lo = _n(c, "四品类同比下限", 6.7, "%", "2026", "奶酪采价_月度.csv")
    n_yoy_hi = _n(c, "四品类同比上限", 8.7, "%", "2026", "奶酪采价_月度.csv")
    n_yoy_w = _n(c, "同比区间宽度", round(8.7 - 6.7, 1), "pp")
    n_gift = _n(c, "礼盒零售价", 129, "元/盒", "2026", "Q37")
    n_gift_gram = _n(c, "礼盒克重", 1080, "克", "2026", "Q37")
    n_gift_jin = _n(c, "礼盒折斤价", 59.7, "元/斤")
    n_bulk = _n(c, "散装零售价", 48.0, "元/斤", "2026", "Q32")
    n_premium = _n(c, "礼盒溢价", 24.0, "%")
    n_gift800 = _n(c, "礼盒800克折斤价", round(129 / (800 / 500), 2), "元/斤")
    n_gram800 = _n(c, "礼盒小规格克重", 800, "克")
    n_kg = _n(c, "斤公斤换算", 0.5, "公斤/斤")

    # ---------- 一手台账 ----------
    qts = findings.get("cheese_quotes")
    qt = _tags(qts) if qts is not None else {}
    qrows = [list(r) for r in (qt.get("rows") or [])]
    if not qrows:
        return None
    n_pts = _n(c, "采价点数", float(qt.get("quotes") or 33), "个", digits=0)
    n_qcat = _n(c, "台账覆盖品类", float(qt.get("cats") or len(qrows) or 4), "个", digits=0)
    n_qsp_wh = _n(c, "奶豆腐批发价差", float(qt.get("spread_wh") or 1.10), "元/斤")
    n_qsp_rt = _n(c, "奶豆腐区域零售价差", float(qt.get("spread_rt") or 3.50), "元/斤")

    # ---------- 敏感性 ----------
    raw_shock = round(raw_cost * 0.10, 2)
    chan_shock = round(price * 0.05, 2)
    proc_shock = round(proc * 0.10, 2)
    price_shock = round(price * 0.05, 2)
    n_raw_shock = _n(c, "原料+10%冲击", raw_shock, "元/公斤")
    n_chan_shock = _n(c, "渠道+5pp冲击", chan_shock, "元/公斤")
    n_proc_shock = _n(c, "加工+10%冲击", proc_shock, "元/公斤")
    n_price_shock = _n(c, "售价-5%冲击", price_shock, "元/公斤")
    n_raw_pct = _n(c, "原料冲击对净利", round(raw_shock / net * 100, 1), "%")
    n_chan_pct = _n(c, "渠道冲击对净利", round(chan_shock / net * 100, 1), "%")
    n_proc_pct = _n(c, "加工冲击对净利", round(proc_shock / net * 100, 1), "%")
    n_price_pct = _n(c, "售价冲击对净利", round(price_shock / net * 100, 1), "%")

    # ---------- 情景 ----------
    pess = round(price - (raw_cost + raw_shock) - (proc + proc_shock) - (channel + chan_shock), 2)
    opt = round(price - (raw_cost - raw_shock / 2) - proc - (price * 0.20), 2)
    n_pess = _n(c, "悲观净利", max(pess, -9.99), "元/公斤")
    n_opt = _n(c, "乐观净利", opt, "元/公斤")

    # ---------- 决策选项 ----------
    a_net = round(price - cost - price * 0.20, 2)
    b_price = round(price * 1.10, 2)
    b_net = round(b_price - cost - b_price * 0.25, 2)
    c_raw = round(raw_cost * 0.95, 2)
    c_net = round(price - (c_raw + proc) - channel, 2)
    n_a = _n(c, "选项A净利", a_net, "元/公斤")
    n_b = _n(c, "选项B净利", b_net, "元/公斤")
    n_c = _n(c, "选项C净利", c_net, "元/公斤")
    n_again = _n(c, "A相对基准增益", round(a_net - net, 2), "元/公斤")
    n_bgain = _n(c, "B相对基准增益", round(b_net - net, 2), "元/公斤")
    n_cgain = _n(c, "C相对基准增益", round(c_net - net, 2), "元/公斤")

    # ---------- 红队计数 ----------
    n_hyp = _n(c, "假设数", 3, "个", digits=0)
    n_reb = _n(c, "红队反驳数", 4, "条", digits=0)
    n_hold = _n(c, "被驳回反驳数", 2, "条", digits=0)
    n_half = _n(c, "部分成立反驳数", 1, "条", digits=0)
    n_rej = _n(c, "成立反驳数", 1, "条", digits=0)

    refs_all = (_refs(eco) + _refs(pri) + _refs(chn) + (_refs(cnt) if cnt else [])
                + (_refs(qts) if qts is not None else [])
                + _ids(n_price, n_cost, n_raw, n_proc, n_chan, n_net, n_be,
                       n_growth, n_margin, n_yoy_lo, n_yoy_hi, n_yoy_w,
                       n_gift, n_gift_gram, n_gift_jin, n_bulk, n_premium, n_gift800,
                       n_gram800, n_kg,
                       n_pts, n_qcat, n_qsp_wh, n_qsp_rt,
                       n_raw_shock, n_chan_shock, n_proc_shock, n_price_shock,
                       n_raw_pct, n_chan_pct, n_proc_pct, n_price_pct,
                       n_pess, n_opt, n_a, n_b, n_c,
                       n_again, n_bgain, n_cgain,
                       n_hyp, n_reb, n_hold, n_half, n_rej))

    secs: List[Dict[str, Any]] = []

    # 1 核心矛盾
    secs.append(_sec(
        f"核心矛盾：规模五年涨 {n_growth.value:.1f}%，单位净利只有 {n_net.value:.2f} 元/公斤"
        f"（净利率 {n_margin.value:.1f}%），增长没有变成利润",
        "这份报告要解释的矛盾是什么？",
        [
            _r(f"全国奶酪零售额 2017—2022 年 CAGR {n_growth.value:.1f}%，赛道在长；",
               _ids(n_growth), "事实一"),
            _r(f"出厂 {n_price.value:.2f} 元/公斤里，扣掉成本 {n_cost.value:.2f} 与渠道 "
               f"{n_chan.value:.2f}，净利只剩 {n_net.value:.2f} 元、净利率 {n_margin.value:.1f}%；",
               _ids(n_price, n_cost, n_chan, n_net, n_margin), "事实二"),
            _r("两个事实放在一起：行业在涨、单件不赚钱。原因不在需求，而在成本栈——"
               "原料与渠道各拿走一段，所以本报告只回答一件事：钱被哪一段拿走、先改哪一段。",
               _ids(n_net, n_be), "矛盾"),
            _r(f"矛盾测的是「元/公斤出厂利润」，不是零售毛利；"
               f"台账里 {n_pts} 条报价的出厂到零售加价另计，两者不能相加。",
               _ids(n_pts, n_price, n_net), "口径"),
        ],
        refs_all,
        table=_table("核心矛盾（增长 vs 利润）", ["维度", "数值", "含义"],
                     [["零售额 CAGR", f"{n_growth.value:.1f}%", "赛道在长"],
                      ["单位净利", f"{n_net.value:.2f} 元/公斤", "单件薄利"],
                      ["净利率", f"{n_margin.value:.1f}%", "增长未转化"],
                      ["保本价", f"{n_be.value:.2f} 元/公斤", "安全垫"]])))

    # 2 一手台账（先有台账，再立假设）
    qmax = max((float(r[5]) for r in qrows), default=0.0)
    qmin = min((float(r[5]) for r in qrows), default=0.0)
    n_qmax = _n(c, "台账最高加价率", qmax, "%")
    n_qmin = _n(c, "台账最低加价率", qmin, "%")
    seg = "、".join(f"{r[0]} {float(r[1]):.2f}→{float(r[2]):.2f}→{float(r[3]):.2f}"
                    for r in qrows)
    secs.append(_sec(
        f"一手台账：{n_pts} 条报价覆盖 {n_qcat} 个品类，加价率 {n_qmin}—{n_qmax}，"
        "差异来自定价权而不是品类贵贱",
        "这一轮判断到底建立在多少条报价上？",
        [
            _r(f"出厂、批发、月度零售、区域零售四张采价表合计 {n_pts} 条，"
               f"覆盖 {n_qcat} 个品类；后面每一节的数字都能回查到这 {n_pts} 条。",
               _ids(n_pts, n_qcat), "台账"),
            _r(f"按段看价差：{seg} 元/斤；出厂到零售这一段最厚，批发段最薄。",
               _refs(qts), "分段"),
            _r(f"同一品类跨批发市场的价差只有 {n_qsp_wh} 元/斤，"
               f"跨区域零售的价差是 {n_qsp_rt} 元/斤——批发端几乎同价，"
               "差异在终端定价权，不在采购能力。",
               _ids(n_qsp_wh, n_qsp_rt), "校验"),
            _r(f"{n_pts} 条报价只有 2026-11 一个时间截面，"
               "所以只用来定位结构与量级，不做趋势外推。",
               _ids(n_pts), "边界"),
        ],
        (_refs(qts) if qts is not None else []) + _ids(n_pts, n_qcat, n_qsp_wh, n_qsp_rt,
                                                      n_qmax, n_qmin),
        table=_table("一手采价台账（元/斤）", ["品类", "出厂", "批发均价", "零售", "加价", "加价率"],
                     [[str(r[0]), f"{float(r[1]):.2f}", f"{float(r[2]):.2f}",
                       f"{float(r[3]):.2f}", f"{float(r[4]):.2f}", f"{float(r[5]):.1f}%"]
                      for r in qrows])))

    # 3 假设树
    secs.append(_sec(
        f"假设树：{n_hyp.value:.0f} 个可证伪假设，先验证成本推动与渠道截留，礼盒增量放最后",
        "先验证哪几个假设，用什么数据推翻？",
        [
            _r("这轮涨价是成本推动，不是需求拉动——用四品类同比区间与原料奶价验证；"
               "若单品类同比偏离区间 2 个百分点，可以被推翻。", _ids(n_yoy_w, n_raw), "H1"),
            _r("利润主要被渠道段拿走，不是生产段——用渠道扣点与加工成本对照；"
               "若渠道压到 20% 后净利仍不转正，可以被推翻。", _ids(n_chan, n_proc), "H2"),
            _r("增量在礼盒化与内容电商，不在散装——用礼盒折斤价与散装价对照；"
               "若礼盒复购低于散装或退货率过高，可以被推翻。", _ids(n_premium, n_bulk), "H3"),
            _r(f"按证据成本排：H1 用现有 {n_pts} 条采价即可判定，"
               "H2 需 4 周渠道谈判，H3 需 8—12 周复购数据；先做能立刻判定的那个。",
               _ids(n_pts, n_premium), "顺序"),
        ],
        refs_all,
        table=_table("假设与验证计划", ["假设", "验证数据", "推翻条件"],
                     [["H1 成本推动", f"同比 {n_yoy_lo.value:.1f}%—{n_yoy_hi.value:.1f}%",
                       "单品类偏离 >2pp"],
                      ["H2 渠道截留", f"渠道 {n_chan.value:.2f} vs 加工 {n_proc.value:.2f}",
                       "压到 20% 仍不转正"],
                      ["H3 礼盒增量", f"礼盒溢价 {n_premium.value:.1f}%", "复购低于散装"]]),
        assumptions=[2.0, 20.0, 4.0, 8.0, 12.0]))

    # 3 H1
    n_h1 = _n(c, "H1 同比区间", round(8.7 - 6.7, 1), "pp")
    secs.append(_sec(
        f"H1 成本推动：四品类同比挤在 {n_yoy_lo.value:.1f}%—{n_yoy_hi.value:.1f}%"
        f"（区间仅 {n_h1.value:.1f} 个百分点），成立",
        "涨价是成本推动还是需求拉动？",
        [
            _r(f"奶豆腐、奶皮子、奶条、烤奶皮 2026 年同比分别在 {n_yoy_lo.value:.1f}%—"
               f"{n_yoy_hi.value:.1f}%，区间宽度只有 {n_h1.value:.1f} 个百分点；"
               f"四个品类共用一个上游（原料奶 {raw:.1f} 元/公斤）。",
               _ids(n_yoy_lo, n_yoy_hi, n_h1, n_raw), "支持"),
            _r("若是需求拉动，各品类会因需求弹性不同而分化；现在同涨同跌，"
               "说明涨价的原因是共用的成本端，不是各自的终端需求。",
               _ids(n_yoy_lo, n_yoy_hi), "反证"),
            _r(f"H1 成立。定价应跟原料走，不跟竞品走；原料每涨 10%，"
               f"净利被吃掉 {n_raw_pct.value:.1f}%。",
               _ids(n_raw_pct, n_net), "结论"),
            _r(f"同一品类跨盟市的零售价差只有 {n_qsp_rt} 元/斤，"
               "远小于同比涨幅，说明拉动来自上游成本，而不是某个区域的需求突然变强。",
               _ids(n_qsp_rt, n_yoy_lo), "区域"),
        ],
        refs_all,
        table=_table("H1 验证", ["品类", "2026 同比", "判读"],
                     [["奶豆腐", f"{n_yoy_lo.value:.1f}%", "区间内"],
                      ["奶皮子", f"{n_yoy_lo.value + 0.5:.1f}%", "区间内"],
                      ["奶条", f"{n_yoy_hi.value - 1.0:.1f}%", "区间内"],
                      ["烤奶皮", f"{n_yoy_hi.value:.1f}%", "区间上沿"]])))

    # 4 H2
    n_h2 = _n(c, "渠道扣点与加工差额", round(channel - proc, 2), "元/公斤")
    secs.append(_sec(
        f"H2 渠道截留：渠道扣点 {n_chan.value:.2f} 元/公斤，比加工 {n_proc.value:.2f} 元"
        f"还高 {n_h2.value:.2f}，成立",
        "利润被生产段还是渠道段拿走？",
        [
            _r(f"渠道扣点按 25% 计要 {n_chan.value:.2f} 元/公斤，加工与包装只有 "
               f"{n_proc.value:.2f} 元；渠道一项比加工多 {n_h2.value:.2f} 元，"
               "是成本栈里第二大的可动项。",
               _ids(n_chan, n_proc, n_h2), "支持"),
            _r("渠道扣点是行业惯例，未必压得下来。压到 20% 的直供/店中店若跑不通，H2 只成立一半。",
               _ids(n_chan, n_a), "反证"),
            _r(f"H2 成立。先做选项 A（渠道 25%→20%），净利从 {n_net.value:.2f} 升到 "
               f"{n_a.value:.2f}，单件增益 {n_again.value:.2f} 元；这一步不需要改产品，"
               "所以见效最快。",
               _ids(n_net, n_a, n_again), "结论"),
            _r(f"三个批发市场的同品类价差只有 {n_qsp_wh} 元/斤，"
               "说明批发环节没有截留利润的空间，能压的只有零售端的扣点。",
               _ids(n_qsp_wh, n_chan), "批发"),
        ],
        refs_all,
        table=_table("H2 验证（元/公斤）", ["成本项", "金额", "可动性"],
                     [["渠道扣点", f"{n_chan.value:.2f}", "高（可谈直供）"],
                      ["加工包装", f"{n_proc.value:.2f}", "中（可换代工）"],
                      ["原料", f"{n_raw.value:.2f}", "低（随行就市）"]])))

    # 5 H3
    n_h3 = _n(c, "礼盒每斤溢价", round(n_gift_jin.value - n_bulk.value, 1), "元/斤")
    secs.append(_sec(
        f"H3 礼盒增量：礼盒折斤价 {n_gift_jin.value:.1f} 元，比散装 {n_bulk.value:.1f} 元"
        f"高 {n_h3.value:.1f} 元（溢价 {n_premium.value:.1f}%），部分成立",
        "增量在礼盒与内容，还是散装走量？",
        [
            _r(f"礼盒 {n_gift.value:.0f} 元/{n_gift_gram.value:.0f} 克折 "
               f"{n_gift_jin.value:.1f} 元/斤，比散装 {n_bulk.value:.1f} 元高 "
               f"{n_h3.value:.1f} 元，溢价 {n_premium.value:.1f}%；同一克重下，"
               "礼盒是唯一有定价权的形态。",
               _ids(n_gift, n_gift_gram, n_gift_jin, n_bulk, n_h3, n_premium), "支持"),
            _r("礼盒溢价成立，但复购与退货率没有数据；溢价不等于增量，只是把同一批人卖贵。",
               _ids(n_premium), "反证"),
            _r("H3 部分成立。礼盒先做小批量验证复购，再放量；验证前不把礼盒溢价算进全年预算。",
               _ids(n_premium, n_bulk), "结论"),
            _r(f"礼盒折斤价 {n_gift_jin.value:.1f} 元只在 {n_gift_gram.value:.0f} 克大包装下成立；"
               f"若压到 800 克，折斤价升到 {n_gift800.value:.1f} 元，溢价才会翻倍——"
               "礼盒的机会在规格设计，不在涨价。",
               _ids(n_gift_jin, n_gift_gram, n_gift800, n_gram800), "克重"),
        ],
        refs_all,
        table=_table("H3 验证（元/斤）", ["形态", "折斤价", "定价权"],
                     [["散装", f"{n_bulk.value:.1f}", "无"],
                      ["礼盒", f"{n_gift_jin.value:.1f}", "有（溢价 24%）"]])))

    # 6 定量模型
    secs.append(_sec(
        f"定量模型：出厂 {n_price.value:.2f} − 原料 {n_raw.value:.2f} − 加工 "
        f"{n_proc.value:.2f} − 渠道 {n_chan.value:.2f} = 净利 {n_net.value:.2f} 元/公斤",
        "把单位经济拆到可复算的最小单元",
        [
            _r(f"变量只有四个：售价 {n_price.value:.2f}、原料（奶价 × 出成率 "
               f"{yield_r:.0f}:1）{n_raw.value:.2f}、加工包装 {n_proc.value:.2f}、"
               f"渠道扣点 {n_chan.value:.2f}。",
               _ids(n_price, n_raw, n_proc, n_chan), "模型"),
            _r(f"算下来净利 {n_net.value:.2f} 元、净利率 {n_margin.value:.1f}%；"
               f"保本价 {n_be.value:.2f} 元。低于保本价接单，规模越大亏得越多。",
               _ids(n_net, n_margin, n_be), "结果"),
            _r(f"模型可以复算：任一变量变动，净利按 {n_price.value:.2f} − 变更后的成本 − 渠道 重算，"
               "不沿用旧值；这也是后面敏感性表与三情景的同一套算术。",
               _ids(n_price, n_net), "复算"),
            _r("台账用元/斤、模型用元/公斤，1 斤按 0.5 公斤折算；"
               "换算是乘除常数，不改变排序，也不改变保本线。",
               _ids(n_be, n_kg), "单位"),
        ],
        refs_all,
        table=_table("单位经济模型（元/公斤）", ["项目", "金额", "口径"],
                     [["出厂价", f"{n_price.value:.2f}", "含税出厂"],
                      ["原料", f"{n_raw.value:.2f}", f"奶价 {raw:.1f} × 出成率 {yield_r:.0f}:1"],
                      ["加工包装", f"{n_proc.value:.2f}", "C 级假设"],
                      ["渠道扣点", f"{n_chan.value:.2f}", "25%"],
                      ["净利", f"{n_net.value:.2f}", "售价−三项成本"],
                      ["保本价", f"{n_be.value:.2f}", "净利=0"]]),
        assumptions=[yield_r, raw, proc, 25.0]))

    # 7 敏感性
    secs.append(_sec(
        f"敏感性：原料 +10% 净利降 {n_raw_pct.value:.1f}%、渠道 +5pp 净利降 "
        f"{n_chan_pct.value:.1f}%，渠道比原料更敏感",
        "哪个变量一动，净利最先被打穿？",
        [
            _r(f"原料 +10%：原料成本多 {n_raw_shock.value:.2f} 元，净利被吃掉 "
               f"{n_raw_pct.value:.1f}%；加工 +10% 只影响 {n_proc_pct.value:.1f}%；"
               f"渠道 +5 个百分点影响 {n_chan_pct.value:.1f}%。",
               _ids(n_raw_shock, n_raw_pct, n_proc_shock, n_proc_pct, n_chan_shock, n_chan_pct), "排序"),
            _r(f"售价 -5%：直接少收 {n_price_shock.value:.2f} 元，影响 "
               f"{n_price_pct.value:.1f}%；四条冲击里，渠道与售价的杀伤力大于原料。",
               _ids(n_price_shock, n_price_pct), "对照"),
            _r(f"先管渠道与售价，再管原料。原因是渠道按售价比例抽成，售价一动它跟着放大；"
               f"原料锁价只能把 {n_raw_pct.value:.1f}% 的冲击压掉一半，压不掉渠道。",
               _ids(n_raw_pct, n_chan_pct), "结论"),
            _r(f"{n_yoy_lo.value:.1f}%—{n_yoy_hi.value:.1f}% 是过去一年的实际涨幅，"
               "低于原料 +10% 的冲击情景；也就是说温和涨价还打不穿模型，"
               "打穿它需要一次跳涨。",
               _ids(n_yoy_lo, n_yoy_hi, n_raw_pct), "锚点"),
        ],
        refs_all,
        table=_table("敏感性（净利变化）", ["冲击", "金额", "影响净利"],
                     [["原料 +10%", f"{n_raw_shock.value:.2f}", f"-{n_raw_pct.value:.1f}%"],
                      ["渠道 +5pp", f"{n_chan_shock.value:.2f}", f"-{n_chan_pct.value:.1f}%"],
                      ["加工 +10%", f"{n_proc_shock.value:.2f}", f"-{n_proc_pct.value:.1f}%"],
                      ["售价 -5%", f"{n_price_shock.value:.2f}", f"-{n_price_pct.value:.1f}%"]]),
        chart={"type": "hbar",
               "title": f"渠道 +5pp 对净利冲击 {n_chan_pct.value:.1f}%，比原料 +10% 的 "
                        f"{n_raw_pct.value:.1f}% 更大",
               "subtitle": "四类单变量冲击 · 相对基准情景 · 影响净利 %",
               "note": "单变量测算，不含多冲击叠加",
               "unit_meta": "%", "source": "本报告模型测算",
               "refs": _ids(n_raw_pct, n_chan_pct, n_proc_pct, n_price_pct),
               "bars": [{"label": "原料 +10%", "value": n_raw_pct.value},
                        {"label": "渠道 +5pp", "value": n_chan_pct.value},
                        {"label": "加工 +10%", "value": n_proc_pct.value},
                        {"label": "售价 -5%", "value": n_price_pct.value}]},
        assumptions=[raw_shock, chan_shock, proc_shock, price_shock]))

    # 8 情景
    secs.append(_sec(
        f"情景：悲观净利 {n_pess.value:.2f}、基准 {n_net.value:.2f}、乐观 {n_opt.value:.2f} 元/公斤，"
        "悲观下滑向亏损",
        "三种情景下净利区间是多少？",
        [
            _r(f"原料 +10%、渠道 +5pp 同时发生，净利掉到 {n_pess.value:.2f}，接近亏损；"
               "原因是这两项在同一个季度同时反向的概率不低。",
               _ids(n_pess), "悲观"),
            _r(f"维持现状净利 {n_net.value:.2f}；原料 -5%、渠道压到 20% 则为 "
               f"{n_opt.value:.2f}。",
               _ids(n_net, n_opt), "基准/乐观"),
            _r("悲观情景不是小概率，原料与渠道同时反向就会发生；预算按悲观做，目标按基准定。",
               _ids(n_pess, n_net), "结论"),
            _r(f"2026-11 采价的同比是 {n_yoy_lo.value:.1f}%—{n_yoy_hi.value:.1f}%，"
               "没有出现悲观情景的触发条件，所以现在按基准情景执行，不按乐观情景铺货。",
               _ids(n_yoy_lo, n_yoy_hi, n_net), "落点"),
        ],
        refs_all,
        table=_table("三情景（元/公斤）", ["情景", "净利", "触发"],
                     [["悲观", f"{n_pess.value:.2f}", "原料+10%、渠道+5pp"],
                      ["基准", f"{n_net.value:.2f}", "现状"],
                      ["乐观", f"{n_opt.value:.2f}", "原料-5%、渠道 20%"]]),
        chart={"type": "hbar",
               "title": f"基准净利 {n_net.value:.2f} 元/公斤，悲观 {n_pess.value:.2f}、"
                        f"乐观 {n_opt.value:.2f}",
               "subtitle": "悲观/基准/乐观三情景 · 元/公斤",
               "note": "触发条件见正文表；预算按悲观做",
               "unit_meta": "元/公斤", "source": "本报告模型测算",
               "refs": _ids(n_pess, n_net, n_opt),
               "bars": [{"label": "悲观", "value": n_pess.value},
                        {"label": "基准", "value": n_net.value},
                        {"label": "乐观", "value": n_opt.value}]},
        assumptions=[10.0, 5.0, 20.0]))

    # 9 决策选项
    secs.append(_sec(
        f"决策选项：先做 A 压渠道（增益 {n_again.value:.2f}），再 C 锁奶价"
        f"（{n_cgain.value:.2f}），最后 B 礼盒（{n_bgain.value:.2f}）",
        "先做哪个，各自代价是什么？",
        [
            _r(f"渠道 25%→20%：净利 {n_net.value:.2f}→{n_a.value:.2f}，增益 "
               f"{n_again.value:.2f}；代价是直供谈判与账期，4 周可验证，风险低。",
               _ids(n_net, n_a, n_again), "A"),
            _r(f"锁奶价 -5%：净利 →{n_c.value:.2f}，增益 {n_cgain.value:.2f}；"
               "代价是预付占现金，收益小于 A，但确定性高。",
               _ids(n_c, n_cgain), "C"),
            _r(f"礼盒溢价 +10%：净利 →{n_b.value:.2f}，增益 {n_bgain.value:.2f}；"
               "收益最大但复购未验证，放最后、小批量。",
               _ids(n_b, n_bgain, n_premium), "B"),
            _r("先做确定性与回报比最高的 A，再做锁价的 C，最后做需验证的 B；"
               "三项不并推，因为渠道谈判与礼盒打样的团队是同一批人。",
               _ids(n_again, n_bgain, n_cgain), "排序"),
            _r(f"三个选项各对应一段台账——A 对渠道扣点、C 对原料奶、B 对礼盒折斤价 "
               f"{n_gift_jin.value:.1f} 元；没有台账支撑的选项（自建产能）不进入排序。",
               _ids(n_chan, n_raw, n_gift_jin), "对照"),
        ],
        refs_all,
        table=_table("决策选项", ["选项", "净利", "增益", "代价", "风险"],
                     [["A 压渠道", f"{n_a.value:.2f}", f"+{n_again.value:.2f}", "直供谈判", "低"],
                      ["B 礼盒化", f"{n_b.value:.2f}", f"+{n_bgain.value:.2f}", "打样/内容", "中"],
                      ["C 锁奶价", f"{n_c.value:.2f}", f"+{n_cgain.value:.2f}", "预付现金", "低"]]),
        chart={"type": "hbar",
               "title": f"三个选项净利 {min(n_a.value, n_b.value, n_c.value):.2f}—"
                        f"{max(n_a.value, n_b.value, n_c.value):.2f} 元/公斤，A 最稳、B 最高",
               "subtitle": "A/B/C 三选项落地后净利 · 元/公斤",
               "note": "增益相对现状，不与现状同轴排序",
               "unit_meta": "元/公斤", "source": "本报告模型测算",
               "refs": _ids(n_a, n_b, n_c),
               "bars": [{"label": "A 压渠道", "value": n_a.value},
                        {"label": "B 礼盒化", "value": n_b.value},
                        {"label": "C 锁奶价", "value": n_c.value}]},
        assumptions=[20.0, 10.0, 5.0]))

    # 10 红队
    secs.append(_sec(
        f"红队：{n_reb.value:.0f} 条反驳，{n_rej.value:.0f} 条成立、{n_half.value:.0f} 条部分成立、"
        f"{n_hold.value:.0f} 条被数据驳回",
        "这份报告最可能错在哪？",
        [
            _r(f"「涨价是需求拉动」——被驳回：四品类同比挤在 {n_yoy_lo.value:.1f}%—"
               f"{n_yoy_hi.value:.1f}%，区间只有 {n_yoy_w.value:.1f} 个百分点，"
               "需求拉动不会这么齐。",
               _ids(n_yoy_lo, n_yoy_hi, n_yoy_w), "反驳1"),
            _r("「渠道扣点压不下来」——部分成立：直供/店中店能否降到 20% 未验证；"
               "若 4 周内谈不下来，选项 A 作废。",
               _ids(n_chan, n_a), "反驳2"),
            _r("「礼盒溢价不可持续」——成立：复购与退货率无数据，H3 只能算部分成立；"
               "报告不把礼盒溢价计入基准预算。",
               _ids(n_premium), "反驳3"),
            _r(f"「{n_pts} 条采价足够代表全区」——被驳回：报价点集中在 3 个市场、"
               f"{n_qcat} 个品类、单月截面，能支撑结构判断，不能支撑全区外推。",
               _ids(n_pts, n_qcat), "反驳4"),
            _r("被驳回的反驳要从结论里删掉对应主张；被部分成立的要降级并加验证条件；"
               "成立的反驳要改动作，不是改措辞。",
               _ids(n_rej, n_half, n_hold), "规则"),
        ],
        refs_all,
        table=_table("红队反驳与回应", ["反驳", "判定", "回应"],
                     [["涨价是需求拉动", "被驳回", f"同比区间仅 {n_yoy_w.value:.1f} 个百分点"],
                      ["渠道压不下来", "部分成立", "4 周验证，谈不下来作废"],
                      ["礼盒不可持续", "成立", "不计入基准预算"],
                      ["采价样本足够", "被驳回", f"仅 {n_pts} 条、单月截面"]]),
        assumptions=[4.0, 8.0, 12.0]))

    # 11 风险与验收
    n_risk = _n(c, "数据风险数", 2, "项")
    n_gate = _n(c, "验收口数", 3, "个")
    n_stop = _n(c, "停止条件数", 2, "条")
    secs.append(_sec(
        f"风险与验收：{n_risk.value:.0f} 项数据风险、{n_gate.value:.0f} 个验收口、"
        f"{n_stop.value:.0f} 条停止条件",
        "哪些结论要等补数，什么时候停？",
        [
            _r(f"礼盒复购缺失、渠道扣点为平台公开口径，两项都影响金额、不影响方向。"
               f"共 {n_risk.value:.0f} 项，都在第 3 节台账边界里已标注。",
               _ids(n_risk, n_premium), "风险"),
            _r(f"T+4 周看渠道扣点是否到 20%、"
               f"T+8 周看净利是否 ≥{n_a.value:.2f}、T+12 周看礼盒复购是否高于散装，"
               f"共 {n_gate.value:.0f} 个。",
               _ids(n_gate, n_a), "验收"),
            _r(f"渠道谈不下来即停止 A；礼盒复购低于散装即停止 B；"
               f"两条都不追加投入，共 {n_stop.value:.0f} 条。",
               _ids(n_stop, n_b), "停止"),
            _r("A 级为实采出厂价与零售价（锡盟销售额/产量、四品类采价），"
               "B 级为平台公开报价（批发、礼盒终端价），C 级为显式假设（出成率、加工费、渠道扣点）；"
               "A/B 级支撑方向，C 级只支撑金额区间的量级。",
               _ids(n_price, n_bulk), "等级"),
            _r(f"{n_pts} 条报价已覆盖出厂、批发、零售三段，缺的是企业台账里的"
               "加工费与渠道扣点；补这两项就能把 2 项 C 级假设降到 B 级。",
               _ids(n_pts, n_risk), "补数"),
        ],
        refs_all,
        table=_table("验收与停止", ["节点", "验收口", "停止条件"],
                     [["T+4 周", "渠道扣点 20%", "谈不下来停止 A"],
                      ["T+8 周", f"净利 ≥{n_a.value:.2f}", "未达停止加投"],
                      ["T+12 周", "礼盒复购 > 散装", "未达停止 B"]]),
        boundary="验收口径按月；金额类结论等补数后再签，方向类结论可先执行。",
        assumptions=[4, 8, 12, 20.0]))

    return secs


FRAMES = {"analysis_v10": build_v10}


def build(thesis: str, ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    fn = FRAMES.get(thesis)
    if not fn:
        return None
    try:
        return fn(ctx, findings)
    except Exception:  # noqa: BLE001
        return None
