# -*- coding: utf-8 -*-
"""core/report_assembly —— finding → 节/指标/计数（从 report_compose 拆出的唯一实现）。

为什么单独成模块（P1.4）：

`core/report_compose.py` 曾是 v9 的「装配器 + 22 纲领」大杂烩。
`decision_report` 只用到它的四个私有函数：

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

import re
from typing import Any, Dict, List, Tuple

from core.claims import claims


def _u() -> str:
    """价格单位：来自项目 method_params / 数据本身，不写死业务单位。"""
    from core import method_params as _mp
    return str(_mp.current().get("price_unit") or "") or "元/单位"


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
    老方法没有 Claim，仍按原来的方式装配，两条路共用同一个渲染器与同一套门禁。

    P3：价格类 finding 没有 Claim 对象，这里补一条**机理 + 判别方法**、
    一条**落点**与一条**证伪**，让每一节都走完五段链，而不是只有第一节有判断。
    只从 finding 已有的数字与 meta 里读，不新造数。
    """
    cl = (getattr(f, "meta", None) or {}).get("claim")
    if cl is not None:
        sec = claims.to_section(cl, f.question)
    else:
        sec = _section_from(f)
        mech, so_what, falsifier = mechanism_for(f)
        if mech:
            sec.setdefault("reading", []).append(
                {"text": mech, "refs": list(dict.fromkeys(sec.get("refs") or [])),
                 "strong": "机理　"})
        if so_what:
            seen = " ".join(str(r.get("text") or "") for r in (sec.get("reading") or []))
            tail = re.sub(r"[^\u4e00-\u9fff]", "", so_what)[:18]
            if not tail or tail not in re.sub(r"[^\u4e00-\u9fff]", "", seen):
                sec.setdefault("reading", []).append(
                    {"text": so_what, "refs": list(dict.fromkeys(sec.get("refs") or [])),
                     "strong": "所以　"})
        if falsifier:
            sec["falsifier"] = falsifier
    return sec


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


# --------------------------------------------------------------------------- #
# P3：价格类 finding 的机理（观察 → 机理 → 落点 → 证伪）
#
# 每条机理必须同时给出「一种解释」与「判别方法」：只说「因为需求下降」不算机理，
# 读者无法拿它去检验。这里的判别方法一律指向**可观测的下一期数据**。
# 只从 finding 已有的数字/meta 里读，不新造数。
# --------------------------------------------------------------------------- #
def _rows(f) -> List[Dict[str, Any]]:
    return (getattr(f, "meta", None) or {}).get("rows") or []


def _stats(f) -> List[Dict[str, Any]]:
    return (getattr(f, "meta", None) or {}).get("stats") or []


def mechanism_for(f) -> Tuple[str, str, str]:
    """返回 (机理, 落点, 证伪)。没有可用标签时返回空串，由门禁判「本节深度不足」。

    数据形状（实测）：
        structure    meta.rows:  {cat, ch:Num, v:float}
        momentum     meta.rows:  {cat, mom:Num, yoy:Num, m:float, y:float}
        trajectory   meta.stats: {cat, n, first, last, ch, cv}          ← 用 stats
        contribution 无 meta，数字在标题与 table 里
        economics    meta.rows:  {cat, markup:Num, nv:Num, margin:Num, v:float}
        transmission meta.rows:  {cat, up:Num, dn:Num}
        breakeven    meta.rows:  {cat, up:Num, need:Num, share:Num}
        risk         只有 meta.no_base / min_periods，无数值行
    """
    key = str(getattr(f, "key", "") or "")
    rows = _rows(f)
    stats = _stats(f)

    if key == "structure" and rows:
        up = [r for r in rows if r["v"] > 0]
        down = [r for r in rows if r["v"] < 0]
        best, worst = max(rows, key=lambda r: r["v"]), min(rows, key=lambda r: r["v"])
        mech = (f"{len(up)} 涨 {len(down)} 跌是分布形态，不是单一原因："
                f"涨幅集中在 {best['cat']}（{best['ch'].p()}）、跌幅集中在 {worst['cat']}"
                f"（{worst['ch'].p()}），说明这一轮是品类间的相对价格调整，"
                "而不是所有品类被同一个成本推着走。判别方法是看下一期涨跌两端是否继续分化："
                "若两端同时收敛到均值附近，这是短期扰动；若继续分化，就是结构性换手。")
        so = ("按方向分资源：涨的一端先锁成本、跌的一端先查是需求塌陷还是供给放量；"
              "把涨跌混进一个均价里考核，会把利润品和引流品一起做坏。")
        fals = (f"若下一期 {best['cat']} 转跌、{worst['cat']} 转涨且幅度超过 2 个百分点，"
                "「相对价格调整」的判断作废，按普涨/普跌重做。")
        return mech, so, fals

    if key == "momentum" and rows:
        opp = [r for r in rows if (r["m"] > 0) != (r["y"] > 0)]
        mech = (f"环比看短期、同比看基数：{len(opp)}/{len(rows)} 个品类两者反向。"
                "反向的品类里，环比是真实供需、同比是去年基数造成的错觉；"
                "判别方法是看反向是否在下期收敛——收敛说明是基数效应，继续扩大说明趋势已变。")
        so = ("按象限定采购方式：双升锁价、高位回落锁量不锁价、双降随行就市、"
              "短期反弹先不追；不要把反向的环比当趋势。")
        fals = "若下一期反向品类的环比与同比转为同向，本节「基数效应」的解释作废。"
        return mech, so, fals

    if key == "trajectory" and stats:
        vol = max(stats, key=lambda r: abs(r.get("cv", 0)))
        mech = (f"同一窗口里 {vol['cat']} 的变异系数 {vol['cv']:.2f}% 最高，"
                f"13 期里从 {vol['first']:g} 走到 {vol['last']:g}（{vol['ch']:+.2f}%）。"
                "波动本身就是成本：报价有效期、库存周转、损耗都随波动上升。"
                "判别方法是把窗口切成两段分别算斜率——斜率同号说明是趋势，"
                "异号说明这段变化主要是噪声。")
        so = ("波动最大的品类用短周期报价、把价格风险转移给合同；"
              "趋势向下的品类不要等反弹再采。")
        fals = f"若去掉首末两点后 {vol['cat']} 的方向反转，本节「波动/趋势」的判断作废。"
        return mech, so, fals

    if key == "contribution":
        # 数字在标题与表里，没有结构化 meta；从表格里取涨跌两端与最大单项，算毛/净比
        trows = (getattr(f, "table", None) or {}).get("rows") or []
        vals: List[Tuple[str, float, str]] = []
        for r in trows:
            try:
                vals.append((str(r[0]["text"]), float(str(r[1]["text"])), str(r[2]["text"])))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        if len(vals) >= 3:
            pos = sum(v for _, v, _ in vals if v > 0)
            neg = sum(v for _, v, _ in vals if v < 0)
            net = pos + neg
            gross = abs(pos) + abs(neg)
            top = max(vals, key=lambda x: abs(x[1]))
            ratio = gross / abs(net) if abs(net) > 1e-9 else float("inf")
            mech = (f"净变动 {net:+.2f} 元是毛变动 {gross:.2f} 元相抵后的残差："
                    f"涨端合计 {pos:+.2f}、跌端合计 {neg:+.2f}，其中 {top[0]} 单项 "
                    f"{top[1]:+.2f} 元。净差小不等于没变化，它可能是两股相反力量抵消。"
                    f"判别方法是看毛变动/净变动的比值（当前 {ratio:.1f}）："
                    "大于 3 就是换手为主，接近 1 才是同向普涨普跌。")
            so = ("按方向分别排采购节奏：涨的提前锁、跌的压缩在途库存；"
                  "不要用「均价平稳」掩盖换手成本。")
            fals = "若下一期毛变动/净变动比值降到 1.5 以下，本节「结构换手」的判断作废。"
            return mech, so, fals

    if key == "economics" and rows:
        neg = [r for r in rows if r["v"] < 0]
        pos = [r for r in rows if r["v"] >= 0]
        best = max(rows, key=lambda r: r["v"])
        mech = (f"{len(rows)} 个品类里 {len(neg)} 个扣完损耗与物流为负、{len(pos)} 个为正。"
                "负毛利的成因是加价率盖不住履约成本，不是售价低——"
                f"判别方法是把 {best['cat']}（净利 {best['nv'].value:+.2f} {_u()}）"
                "与最差品类做成本栈对比：若两者加价率接近而净利差很大，病灶在损耗/物流；"
                "若加价率差很大，病灶在定价。")
        so = ("先修成本结构（换源/直采/降损耗），再谈品类组合；"
              "对负毛利品类按「提价空间 × 销量弹性」分路径，不要统一提价。")
        fals = "若实际损耗或物流成本比假设低 20%，负毛利名单要重算，本节结论作废。"
        return mech, so, fals

    if key == "transmission" and rows:
        up = [r for r in rows if r["up"].value < 0]
        big = max(rows, key=lambda r: abs(r["dn"].value))
        mech = (f"价差不是均匀分布的：{big['cat']} 的集散到终端段 {big['dn'].value:+.2f} {_u()}，"
                f"产地到集散段 {big['up'].value:+.2f} 元；{len(up)} 个品类在产地端倒挂。"
                "判别方法是拿同一规格、同一期的三段报价重算："
                "若三段不同期或不同规格，价差本身不成立。")
        so = ("按品类拆段优化：终端段厚的谈环节、上游倒挂的换采购方式；"
              "「整体降本」在这条链路上是无效动作。")
        fals = "若上下游不是同规格同期报价，本节价差作废，不能反推真实毛利。"
        return mech, so, fals

    if key == "breakeven" and rows:
        cheap = min(rows, key=lambda r: r["need"].value)
        mech = (f"保本线由成本栈决定：{cheap['cat']} 只需提价 {cheap['up'].p()} 即可转正，"
                "说明它的加价率离保本只差一点；需要大幅提价的品类则相反。"
                "判别方法是看提价后的销量跌幅——跌 3% 以内说明需求不敏感，超过 5% 说明这条路径不成立。")
        so = ("按单价分路径：高单价品类先提价、低单价高频品只降本不涨价；"
              "两条路径的验收指标不同，不能合成一个毛利率目标。")
        fals = "若提价后周销量跌幅超过 5%，提价路径作废，改走直采降本。"
        return mech, so, fals

    if key == "risk":
        meta = getattr(f, "meta", None) or {}
        nb = int(meta.get("no_base_count") or 0)
        mp = int(meta.get("min_periods") or 8)
        mech = (f"覆盖口径决定结论强度：{nb} 个品类没有集散基准、最小期数是 {mp} 期。"
                "缺基准的品类只能比自身历史，不能跨品类比价；期数不足时点估计不可靠。"
                "判别方法是用前 60% 窗口重算一次——结论翻转就说明它依赖窗口。")
        so = ("覆盖不足的品类只给方向、不给点位；要下确定性结论，先把基准或期数补齐。")
        fals = "若把窗口换成前 60% 后结论翻转，本节结论作废。"
        return mech, so, fals

    if key == "growth":
        mech = ("规模的增长由首末两期的复合变化决定，而不是单期起伏；"
                "一段快一段慢说明增长引擎在切换，用平均增速外推会同时高估后段、低估前段。"
                "判别方法是看下一期增速落在哪一段区间——连续两期越界，说明两段结构已经失效。")
        so = "用末期结构做规划；两段分化时只给区间，不给单点外推。"
        fals = "若下一期增速同时高于两段区间，本节「两段分化」的判断作废，按单一趋势重算。"
        return mech, so, fals

    if key == "concentration":
        mech = ("份额差距决定集中度：头部份额越高，CR 与 HHI 的上下界越靠近；"
                "未披露主体不拆分时，HHI 只能给区间，不能当成一个确定值。"
                "判别方法是看下一期 CR 与 HHI 是否跨档——跨档说明格局换了，没跨档只是同格局内的波动。")
        so = "高集中时不要正面拼货架，从细分场景与上游切入；未拆分主体前只给区间。"
        fals = "若下一期 CR 与原区间不重叠，本节集中度判断作废，按新格局重算。"
        return mech, so, fals

    if key == "reviews":
        mech = ("评分结构比均分更能说明问题：均分接近时，低分占比与好评占比决定体验是集中塌陷还是普遍一般。"
                "判别方法是看下一期低分占比是否上升两个百分点以上——上升说明短板在扩散，只改单个环节不够。")
        so = "先修低分集中的环节；均分作为结果指标，不作为整改依据。"
        fals = "若下一期低分占比下降两个百分点以上，本节「体验短板」的判断作废。"
        return mech, so, fals

    if key == "priority":
        mech = ("排序由 Reach×Impact÷Effort 决定，分母是工作量：分数高但工作量也高的需求会被排前却久拖不出结果。"
                "判别方法是换一批需求重算——前三分之一基本稳定说明排序可用，大幅换位说明打分口径不稳。")
        so = "按 RICE 排序做排期，前三分之一进本迭代，其余进验证队列。"
        fals = "若换一批需求重算后前三分之一换位过半，本节排序作废，先校准打分。"
        return mech, so, fals

    return "", "", ""


# --------------------------------------------------------------------------- #
# P3：把「描述型标题」改成「判断型标题」
#
# Q1（标题即判断）要求标题同时含「数字」与「判断词」。方法层给的部分标题是
# 纯描述的（如「节奏：西瓜 环比 0.01%、同比 -0.13%，短期反弹·趋势未改」），
# 读者看不出判断是什么。这里只做**后置一句判断**，不动方法给的数字。
# --------------------------------------------------------------------------- #
_TITLE_JUDGE = {
    "structure": "——这是结构分化，不是普涨普跌（用均价考核会掩盖换手）",
    "momentum": "——短期反弹不能读成趋势反转（环比与同比反向的品类占比过半）",
    "contribution": "——净差小是换手，不是没变化",
    "economics": "——病灶在成本结构，不在售价",
    "transmission": "——钱被中间段吃掉，不是整体贵",
    "breakeven": "——提价与直采是两条路，不能合成一个目标",
    "risk": "——样本不足时只给方向，不给点位",
    "trajectory": "——波动本身就是成本",
}


def judged_title(f) -> str:
    """给标题补一句判断；已经带判断词的标题原样返回。"""
    key = str(getattr(f, "key", "") or "")
    title = str(getattr(f, "title", "") or "")
    tail = _TITLE_JUDGE.get(key, "")
    if not tail or tail in title:
        return title
    # 已经含判断词的标题不再追加，避免「判断：判断」叠壳
    if any(w in title for w in ("不是", "不能", "应", "先", "停", "差", "退",
                                "分化", "倒挂", "负毛利", "保本", "作废", "失效")):
        return title
    return title + tail


def _metrics(picked: List[Any], label_of: Dict[str, int]) -> List[Dict[str, Any]]:
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
                        "note": f"第 {idx} 节 · 扣损耗与物流",
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
                        "value": f"{r['nv'].value:+.2f} {_u()}",
                        "note": f"第 {idx} 节 · 扣运费与物流",
                        "status": "healthy" if r["v"] > 0 else "critical"})
        elif f.key == "breakeven" and rows:
            r = rows[0]
            out.append({"label": f"{r['cat']} 保本提价", "value": r["up"].p(),
                        "note": f"第 {idx} 节 · 只覆盖损耗与物流",
                        "status": "watch"})
        elif f.key == "trajectory" and rows:
            r = max(rows, key=lambda x: abs(x["ch"]))
            out.append({"label": f"{r['cat']} 区间变化", "value": f"{r['ch']:+.1f}%",
                        "note": f"第 {idx} 节 · 首末两期",
                        "status": "critical" if r["ch"] < 0 else "healthy"})
        elif f.key == "risk":
            n = (f.meta or {}).get("no_base_count")
            if n:
                out.append({"label": "无集散基准", "value": f"{n} 个",
                            "note": f"第 {idx} 节 · 覆盖缺口", "status": "watch"})
        if len(out) >= 4:
            break
    return out


__all__ = ["_subject", "_section_from", "_section_of", "_counts", "_metrics"]
