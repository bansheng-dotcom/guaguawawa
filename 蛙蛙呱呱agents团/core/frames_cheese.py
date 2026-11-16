# -*- coding: utf-8 -*-
"""core/frames_cheese —— 奶酪零食「成本与止损整改」的问题链帧（v8）。

参考稿（肉禽蛋「负毛利整改」）的整改方案不是把 finding 平铺，而是按问题链走：

    负在哪（根因拆解）→ 分几段（止血/转正/加固）→ 每类怎么治（分品类动作）→
    治完账怎么算（整改后账）→ 什么时候验收（里程碑）→ 谁拍板、什么不做。

本模块对奶酪零食做同一套问题链，但把「活畜/屠宰/冷链」换成奶酪零食的
「奶价/出成率/渠道扣点/礼盒化」。数据仍来自 `core/methods/cheese` 的 finding，
数字仍是已登记的 Num，不新算一套；推导阈值写进 `section.assumptions`。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.analysis_methods import Finding, Num, _ids, _table
from core.claims import to_section as _claim_section


def _f(v: Any) -> float:
    return float(getattr(v, "value", v) or 0.0)


def _sec(title: str, question: str, reading: List[Dict[str, Any]],
         refs: List[str], table=None, boundary: str = "",
         assumptions: Optional[List[float]] = None) -> Dict[str, Any]:
    sec = {"title": title, "question": question, "reading": reading,
           "refs": list(dict.fromkeys(refs)), "assumptions": list(assumptions or [])}
    if table:
        sec["table"] = table
    if boundary:
        sec["boundary"] = boundary
    return sec


def _r(text: str, refs: List[str], strong: str = "") -> Dict[str, Any]:
    return {"text": text, "refs": list(refs), "strong": strong}


def _tags(f: Optional[Finding]) -> Dict[str, Any]:
    cl = (getattr(f, "meta", None) or {}).get("claim")
    return (getattr(cl, "tags", None) or {}) if cl is not None else {}


def build_cheese_fix(ctx, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    eco = findings.get("cheese_unit_econ")
    chn = findings.get("cheese_chain")
    pol = findings.get("cheese_policy")
    if not eco:
        return []
    c = ctx.cite
    t = _tags(eco)
    price = t.get("price", 0.0)
    cost = t.get("cost", 0.0)
    net = t.get("net", 0.0)
    be = t.get("breakeven", 0.0)
    channel = t.get("channel", 0.0)
    raw_cost = t.get("raw", 0.0)
    # 从 unit_econ 的机制里取原料/加工（用事实表的出成率与奶价重算，保证可复算）
    ass = {a.get("metric"): a for a in (ctx.desk.assumptions or [])}
    yield_r = float((ass.get("yield_ratio") or {}).get("value", 8.0))
    proc = float((ass.get("process_cost") or {}).get("value", 12.0))
    raw = float((ass.get("raw_price") or {}).get("value", 3.0))
    raw_cost = yield_r * raw
    secs: List[Dict[str, Any]] = []

    # 1. 根因拆解：成本栈三项占比
    n_price = c.n("出厂价（整改）", price, "元/公斤")
    n_raw = c.n("原料成本（整改）", raw_cost, "元/公斤")
    n_proc = c.n("加工包装（整改）", proc, "元/公斤")
    n_chan = c.n("渠道扣点金额（整改）", channel, "元/公斤")
    n_net = c.n("净利（整改）", net, "元/公斤")
    n_be = c.n("保本价（整改）", be, "元/公斤")
    parts = [("原料（奶价×出成率）", raw_cost, raw_cost / price * 100),
             ("加工与包装", proc, proc / price * 100),
             ("渠道扣点", channel, channel / price * 100)]
    parts.sort(key=lambda x: x[1], reverse=True)
    main = parts[0]
    refs = _ids(n_price, n_raw, n_proc, n_chan, n_net)
    secs.append(_sec(
        f"根因：出厂价 {price:.1f} 元里，{main[0]}占 {main[2]:.0f}% 是最大成本项，"
        f"渠道扣点吃掉 {channel/price*100:.0f}% 后净利只剩 {net:.2f} 元",
        "奶酪零食的薄利是奶价、加工还是渠道造成的？",
        [
            _r(f"把出厂价 {n_price} 元/公斤拆成三项：原料 {n_raw} 元（奶价 {raw:.1f} 元 × "
               f"出成率 {yield_r:.0f}:1）、加工 {n_proc} 元、渠道 {n_chan} 元；"
               f"{main[0]} 占比最高（{main[2]:.0f}%），是薄利的第一来源。",
               refs, "成本栈　"),
            _r(f"渠道扣点按 25% 算要 {n_chan} 元/公斤，比加工 {n_proc} 元还高；"
               "渠道是第二块隐形成本，且不像原料可以锁价——它随平台与达人佣金波动。",
               _ids(n_chan, n_proc), "对照　"),
            _r(f"净利 {n_net} 元/公斤、保本价 {n_be} 元/公斤：低于保本价，规模越大亏得越多。",
               _ids(n_net, n_be), "判断　"),
        ],
        refs,
        table=_table("成本栈拆解（元/公斤）", ["成本项", "金额", "占出厂价"],
                     [[p[0], f"{p[1]:.2f}", f"{p[2]:.0f}%"] for p in parts]),
        boundary="成本栈按 C 级假设（出成率 8:1、奶价 3.0 元、加工 12 元、渠道 25%）测算，未含设备折旧与税。",
        assumptions=[yield_r, raw, proc, 25.0]))

    # 2. 三段目标：止血/转正/加固
    gain = max(0.5, abs(net) * 0.5 + 0.3)
    n_now = c.n("净利现状（整改）", net, "元/公斤")
    n_2w = c.n("2周目标", net + gain * 0.4, "元/公斤")
    n_6w = c.n("6周目标", net + gain * 0.8, "元/公斤")
    n_12w = c.n("12周目标", net + gain, "元/公斤")
    refs2 = _ids(n_now, n_be, n_2w, n_6w, n_12w)
    secs.append(_sec(
        f"目标：净利从 {net:+.2f} 元/公斤，2 周止血、6 周转正、12 周加固到 {net+gain:+.2f} 元",
        "整改分几段，每段唯一目标是什么？",
        [
            _r(f"净利现状 {n_now} 元/公斤，低于保本价 {n_be} 元的安全线，"
               "三段目标不能合并：动作会互相掩盖、归因会失真。2 周先止血（锁奶价、压渠道扣点），"
               "6 周做到净利不再恶化，12 周才谈加固（礼盒化、直供）。",
               refs2, "判断　"),
            _r(f"每段只允许一个目标：2 周目标 {n_2w} 元、6 周 {n_6w} 元、12 周 {n_12w} 元，"
               f"每段都比上一段高 {gain*0.4:+.2f} 元，避免『既降本又提价又换渠道』同时上。",
               refs2, "分段　"),
            _r("6 周仍未改善，说明根因判错，停止叠加动作回到根因重判，不继续加动作。",
               refs2, "止损　"),
        ],
        refs2,
        table=_table("三段目标（元/公斤）", ["节点", "目标净利", "唯一动作"],
                     [["T+2 周", f"{net + gain*0.4:+.2f}", "锁奶价/压渠道扣点"],
                      ["T+6 周", f"{net + gain*0.8:+.2f}", "净利不再恶化"],
                      ["T+12 周", f"{net + gain:+.2f}", "礼盒化/直供"]]),
        assumptions=[2, 6, 12, round(gain, 2)]))

    # 3. 分品类动作：奶豆腐压渠道段、奶条保品牌
    if chn:
        ct = _tags(chn)
        secs.append(_sec(
            f"分品类动作：奶豆腐压渠道段（扣点 {channel/price*100:.0f}%）、奶条保内容溢价，两套动作不能混",
            "奶豆腐与奶条各自怎么治？",
            [
                _r("奶豆腐是传统硬奶酪，加价率比零食化品类低，加价集中在出厂到零售的渠道段，"
                   "动作是直供/店中店压渠道扣点，不碰品牌；",
                   _ids(n_chan), "奶豆腐　"),
                _r("奶条是零食化品类，批发到零售加价率高于奶豆腐，利润在礼盒与场景溢价，"
                   "动作是保内容与品牌、不参与散装价格战；",
                   [n_net.id], "奶条　"),
                _r("两类不能共用一套考核：奶豆腐考渠道扣点与保本价（相对价格），"
                   "奶条考礼盒溢价与复购（相对动销）。",
                   [n_be.id], "落点　"),
            ],
            _ids(n_chan, n_net, n_be),
            boundary="品类动作按当前加价率与成本结构反推，执行前需用真实渠道扣点与礼盒动销校准。"))
    else:
        secs.append(_sec(
            f"分品类动作：先压渠道段（扣点 {channel/price*100:.0f}%），再做礼盒化",
            "品类动作怎么排？",
            [_r("渠道扣点比加工还高，先压渠道段（直供/店中店），再谈礼盒化溢价。",
                _ids(n_chan), "判断　")],
            _ids(n_chan),
            assumptions=[25.0]))

    # 4. 整改后账：每千斤改善
    n_cur = c.n("每千斤现状净利", net * 1000, "元")
    n_aft = c.n("每千斤改善后净利", (net + gain) * 1000, "元")
    n_gain = c.n("每千斤改善额", gain * 1000, "元")
    refs4 = _ids(n_cur, n_aft, n_gain)
    secs.append(_sec(
        f"整改后账：每千斤改善 {gain*1000:.0f} 元，主要来自压渠道扣点与锁奶价",
        "整改到底能挽回多少，值不值得做？",
        [
            _r(f"按每千斤算：现状净利 {n_cur} 元、12 周后 {n_aft} 元、改善 {n_gain} 元，"
               "改善后比现状多出近一倍；改善主要来自渠道扣点与奶价，不是提价。",
               refs4, "判断　"),
            _r("改善额要扣整改投入（询价、直供谈判、礼盒打样）；扣完仍为正，才值得做——"
               "整改投入高于改善额时，说明这段链路不值得重构。", refs4, "落点　"),
        ],
        refs4,
        table=_table("整改后账（元/千斤）", ["项目", "金额", "主要来源"],
                     [["现状净利", f"{net*1000:+.0f}", "出厂价−成本−渠道"],
                      ["12 周后", f"{(net+gain)*1000:+.0f}", "压渠道+锁奶价"],
                      ["改善额", f"{gain*1000:+.0f}", "渠道扣点/奶价"]]),
        assumptions=[1000, 12, round(gain, 2)]))

    # 5. 里程碑 + 拍板 + 不做清单（合并为「验收与拍板」）
    secs.append(_sec(
        "90 天里程碑：2 周止血、6 周转正、12 周加固，每段一个验收口",
        "90 天怎么排，谁在什么时候验收？",
        [
            _r(f"T+2 周：锁奶源/价格联动、压渠道扣点到 20%（比当前 25% 低 5 个点），"
               "验收口是净利不再扩大；", _ids(n_2w, n_chan), "第 1 段　"),
            _r("T+6 周：直供/店中店跑通，净利不再恶化；验收口是渠道扣点与保本价，"
               "相对第 1 段只看渠道扣点是否真降；", _ids(n_6w, n_be), "第 2 段　"),
            _r("T+12 周：礼盒化与直供落地，净利回到目标线；未达标的品类退出或改引流，"
               "相对前两段开始看礼盒溢价与复购。", _ids(n_12w), "第 3 段　"),
        ],
        _ids(n_2w, n_6w, n_12w),
        table=_table("90 天里程碑", ["节点", "动作", "验收口"],
                     [["T+2 周", "锁奶价/压渠道扣点", "净利不再扩大"],
                      ["T+6 周", "直供/店中店跑通", "渠道扣点/保本价"],
                      ["T+12 周", "礼盒化/直供落地", "净利回目标线"]]),
        assumptions=[2, 6, 12, 20]))

    secs.append(_sec(
        "拍板与不做：3 件事必须创始人签字，4 件事现在不做",
        "哪些超出执行层权限、哪些不能做？",
        [
            _r("① 是否签年度奶源协议（预付/账期涉及资金占用，预付比账期更便宜但要占现金流）；"
               "② 直供是否允许现结（现结通常比账期再降 1—2 个点）；"
               "③ 是否把奶条从毛利考核改为礼盒溢价 + 复购考核（相对散装走量）。",
               _ids(n_be), "拍板　"),
            _r("不自建奶酪工厂（重资产、资质周期长，收益低于代工）；不给奶豆腐散装提价（会丢客流）；"
               "不为单个品类新建冷链（装载率相对共用更低）；不做全品类自营（低毛利品类继续批发）。",
               _ids(n_chan), "不做　"),
        ],
        _ids(n_be, n_chan),
        boundary="拍板事项涉及资金与合同，按公司治理必须创始人签字，报告只给建议。"))

    # 6. 数据缺口（整改结论受哪些 C 级假设约束，一并写进整改方案）
    cov = findings.get("cheese_coverage")
    if cov is not None:
        cl = (getattr(cov, "meta", None) or {}).get("claim")
        if cl is not None:
            secs.append(_claim_section(cl, cov.question))
    return secs


FRAMES: Dict[str, Any] = {"cheese_fix": build_cheese_fix}


def build(thesis: str, ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    fn = FRAMES.get(thesis)
    if not fn:
        return None
    try:
        return fn(ctx, findings)
    except Exception:  # noqa: BLE001
        return None
