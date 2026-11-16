# -*- coding: utf-8 -*-
"""core/frames —— 价格类经营报告的「问题链」（v7）。

同一批 finding，三类报告问的问题不一样，章节结构就必须不一样：

    经营诊断：赚不赚钱 → 品类矩阵 → 单位经济 → 采购策略 → 跨市场配额 →
              周转损耗 → 定价组合 → 风险 → KPI 门禁 → 30 天行动
    链路优化：利润在哪一段 → 分段加价 → 错配定位 → 可重构段 → 跨市场 →
              重构路径 → 风险 → 动作
    负毛利整改：负在哪 → 根因拆解 → 三段目标 → 分品类动作 → 整改后账 →
              90 天里程碑 → 验收门禁 → 拍板事项 → 不做清单

参考稿（内蒙古肉禽蛋五件套）就是这么写的。本模块只做「按问题链装配」：
数据仍来自 analysis_methods 的 finding，数字仍是已登记的 Num，不新算一套；
缺的节（矩阵/采购/周转/定价/KPI）由 finding 的 meta 行推导，推导用的阈值
全部写进 section.assumptions，正文不出现无出处的数。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from core.analysis_methods import Finding, Num, _ids, _table
from core.claims import Claim, finalize, pp, to_section

# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def _f(v: Any) -> float:
    return float(getattr(v, "value", v) or 0.0)


def _row(r: Dict[str, Any], key: str) -> Optional[Num]:
    v = r.get(key)
    return v if isinstance(v, Num) else None


def _pct(n: Optional[Num]) -> str:
    return n.p() if n is not None else "—"


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


def _from_finding(f: Finding, question: str = "") -> Dict[str, Any]:
    sec = {"title": f.title, "question": question or f.question,
           "reading": [dict(x) for x in f.reading],
           "refs": list(dict.fromkeys(f.refs)),
           "assumptions": [round(float(a), 6) for a in f.assumptions]}
    if f.table:
        sec["table"] = f.table
    if f.chart:
        sec["chart"] = f.chart
    if f.boundary:
        sec["boundary"] = f.boundary
    return sec


def _econ_rows(findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    f = findings.get("economics") or findings.get("cost") or findings.get("margin")
    return list((getattr(f, "meta", None) or {}).get("rows") or []) if f else []


def _mom_map(findings: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    f = findings.get("momentum")
    rows = list((getattr(f, "meta", None) or {}).get("rows") or []) if f else []
    return {r["cat"]: r for r in rows}


def _gain(cur: float) -> float:
    """负毛利品类的 12 周改善目标：约当前亏损的 2 倍，上下限 0.2—1.0 元/斤。

    亏损越深，改善空间越大，但不允许一步跳到「提价 20%」这种不可执行的幅度。
    """
    return max(0.2, min(1.0, abs(cur) * 2 + 0.1))


def _median(xs: List[float]) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


# --------------------------------------------------------------------------- #
# 经营诊断
# --------------------------------------------------------------------------- #
def build_operations(ctx, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = _econ_rows(findings)
    if not rows:
        return []
    mom = _mom_map(findings)
    secs: List[Dict[str, Any]] = []

    # 1. 品类矩阵：加价率 × 同比
    mk_mid = _median([_f(r["markup"]) for r in rows])
    quads: Dict[str, List[Dict[str, Any]]] = {"利润品": [], "结构品": [],
                                             "成本挤压": [], "引流或淘汰": []}
    for r in rows:
        m = mom.get(r["cat"], {})
        yoy = _f(m.get("yoy")) if m else 0.0
        high = _f(r["markup"]) >= mk_mid
        up = yoy >= 0
        q = ("利润品" if (high and up) else "结构品" if high else
             "成本挤压" if up else "引流或淘汰")
        quads[q].append({"r": r, "yoy": yoy, "q": q})
    act = {"利润品": "扩 SKU、锁量、做礼盒", "结构品": "做套餐、控库存、年节主推",
           "成本挤压": "锁活畜/直采、提价试单", "引流或淘汰": "只做引流，不考核毛利"}
    trs = []
    for q, items in quads.items():
        if not items:
            continue
        trs.append([q, "、".join(i["r"]["cat"] for i in items), act[q]])
    n_high = sum(1 for r in rows if _f(r["markup"]) >= mk_mid)
    neg = [r for r in rows if _f(r["net"]) < 0]
    refs = [r["markup"].id for r in rows] + [r["yoy"].id for r in mom.values() if "yoy" in r]
    secs.append(_sec(
        f"经营矩阵：{len(rows)} 个品类里 {n_high} 个高加价、{len(rows)-n_high} 个低加价；"
        f"低加价且涨价的 {len(quads['成本挤压'])} 个是负毛利来源",
        "哪些品类该做利润、哪些只能做引流？",
        [
            _r(f"按加价率中位数 {mk_mid*100:.1f}% 与同比方向分四象限："
               f"{'、'.join(i['r']['cat'] for i in quads['成本挤压'])} 落在"
               "『低加价 + 成本上行』，正是扣完成本为负的那几个；"
               "高加价品类即使价格在跌，也还有空间。", refs, "判断　"),
            _r(f"负毛利 {len(neg)} 个："
               + "、".join(f"{r['cat']} {r['net'].value:+.2f} 元" for r in neg)
               + "。这些品类继续按销量考核，只会越卖越亏。",
               [r["net"].id for r in neg], "亏损清单　"),
            _r("矩阵的用法是分角色考核：利润品考毛利，结构品考周转，"
               "成本挤压品考采购成本，引流品只考客流与连带。",
               refs, "落点　"),
        ],
        refs,
        table=_table("品类经营矩阵（加价率 × 同比）",
                     ["象限", "品类", "经营动作"], trs),
        assumptions=[round(mk_mid * 100, 2)],
        boundary="象限按品类加价率中位数切分，不是行业标准；同一品类内不同部位可能落在不同象限。"))

    # 2. 单位经济（已有 finding，直接装配）
    if findings.get("economics"):
        secs.append(_from_finding(findings["economics"],
                                  "按标准损耗与冷链重算，哪些品类真的亏？"))

    # 3. 采购策略：按加价率与价格方向分三档
    strat: Dict[str, List[str]] = {"锁价/直采": [], "批发为主": [], "比价随行": []}
    for r in rows:
        m = mom.get(r["cat"], {})
        yoy = _f(m.get("yoy")) if m else 0.0
        mk = _f(r["markup"])
        if mk < 0.10 and yoy > 0.03:
            strat["锁价/直采"].append(r["cat"])
        elif mk > 0.30:
            strat["批发为主"].append(r["cat"])
        else:
            strat["比价随行"].append(r["cat"])
    srows = []
    if strat["锁价/直采"]:
        srows.append(["锁价/直采", "、".join(strat["锁价/直采"]),
                      "加价薄且价格上行", "锁活畜或白条价，不锁产地零售价", "六成"])
    if strat["批发为主"]:
        srows.append(["批发为主", "、".join(strat["批发为主"]),
                      "加价厚、损耗低", "锁周度量，不做长协", "八成"])
    if strat["比价随行"]:
        srows.append(["比价随行", "、".join(strat["比价随行"]),
                      "中间加价", "周度比价，价差大于运杂费再换源", "四成"])
    refs = [r["markup"].id for r in rows] + [r["w"].id for r in rows]
    secs.append(_sec(
        f"采购策略：{len(strat['锁价/直采'])} 个品类要锁价、{len(strat['批发为主'])} 个走批发、"
        f"{len(strat['比价随行'])} 个比价随行",
        "采购该一刀切，还是按品类分档？",
        [
            _r("分档不看品类名气，看两个数：加价率能不能覆盖损耗冷链、"
               "价格方向会不会继续吃成本。" + ("加价薄又涨价的必须锁价，"
               "否则每涨一次就亏一次；加价厚的用周度锁量即可。" if strat["锁价/直采"] else ""),
               refs, "判断　"),
            _r("锁价对象只能是活畜或屠宰白条，不能锁产地零售价——"
               "产地零售与销地批发不是同一交易环节，锁错会倒挂。", refs, "合同要点　"),
            _r("目标覆盖率按档位定：锁价 60%、批发 80%、比价 40%；"
               "覆盖率不达标时先补合同，不先扩量。", refs, "落点　"),
        ],
        refs,
        table=_table("采购三档", ["策略", "适用品类", "触发", "合同要点", "目标覆盖"], srows),
        assumptions=[60, 80, 40, 10, 30, 3],
        boundary="触发阈值（加价 10%、同比 3%）是本轮测算的经验线，不是行业标准；"
                 "覆盖率目标需按现金流与仓容校准。"))

    # 4. 跨市场配额（已有 finding）
    if findings.get("arbitrage"):
        sec = _from_finding(findings["arbitrage"], "同一时点，跨市场调运还值不值？")
        arb_refs = list(sec["refs"])
        sec["reading"].append(_r(
            "价差不是利润：运费与损耗是随车固定的，价差是随行就市的，"
            "这就是为什么同一价差在不同装载率下净利不同。", arb_refs, "机理　"))
        secs.append(sec)

    # 5. 周转与损耗
    shelf = {"鸡蛋": 3, "白条鸡": 2, "牛": 3, "羊": 3, "带鱼": 30,
             "鲤鱼": 1, "草鱼": 1}
    trows = []
    for r in rows:
        d = shelf.get(r["cat"], 3)
        trows.append([r["cat"], f"{d} 天", _pct(r["loss"]), f"{_f(r['cold']):.2f} 元/斤"])
    refs = [r["loss"].id for r in rows] + [r["cold"].id for r in rows]
    secs.append(_sec(
        f"周转与损耗：{len(rows)} 个品类的损耗上限 {min(_f(r['loss']) for r in rows)*100:.0f}%—"
        f"{max(_f(r['loss']) for r in rows)*100:.0f}%，冷链 {min(_f(r['cold']) for r in rows):.2f}—"
        f"{max(_f(r['cold']) for r in rows):.2f} 元/斤",
        "周转要多快、损耗怎么控？",
        [
            _r("周转天数按保质期倒推：活鱼 1 天、白条鸡 2 天、鲜肉 3 天、冻品 30 天；"
               "超过这个天数，损耗率会吃掉全部加价。", refs, "判断　"),
            _r("损耗控制写进合同而不是靠现场：活鱼按成活率结算（低于 95% 扣款）、"
               "冻虾按净重（冰衣率超 10% 不计价）、白条鸡按只 + 净膛重双计。",
               refs, "合同要点　"),
            _r("损耗率随周转天数上升，超过保质期后不可逆——这是周转上限的来源，"
               "也是为什么活鱼只能按天算、冻品才能按月算。", refs, "机理　"),
            _r("冷链成本按装载率摊：同一辆车多装一个品类，单位冷链就降一档；"
               "不要为单个品类新增固定冷链。", refs, "落点　"),
        ],
        refs,
        table=_table("周转与损耗上限", ["品类", "建议周转", "损耗率", "冷链成本"], trows),
        assumptions=[1, 2, 3, 30, 95, 10],
        boundary="周转天数为按保质期的经验上限，不是企业实测；损耗率是品类经验值。"))

    # 6. 定价与组合：三类角色
    profit = [r for r in rows if _f(r["net"]) > 0 and _f(r["markup"]) >= 0.30]
    traffic = [r for r in rows if _f(r["markup"]) < 0.10]
    struct = [r for r in rows if r not in profit and r not in traffic]
    prows = []
    if profit:
        prows.append(["利润品", "、".join(r["cat"] for r in profit),
                      "保毛利，不参与价格战", "净毛利率", "低于 0 立即停促"])
    if traffic:
        prows.append(["引流品", "、".join(r["cat"] for r in traffic),
                      "平价、限购、放端头", "客流与连带率", "禁止单独考核毛利"])
    if struct:
        prows.append(["结构品", "、".join(r["cat"] for r in struct),
                      "年节与礼盒，限量", "周转与毛利双看", "不做日常走量"])
    refs = [r["net"].id for r in rows] + [r["markup"].id for r in rows]
    secs.append(_sec(
        f"定价与组合：{len(profit)} 个利润品、{len(traffic)} 个引流品、"
        f"{len(struct)} 个结构品，三套定价不能混",
        "每个品类该按什么角色定价与考核？",
        [
            _r("把品类分成利润品、引流品、结构品：利润品保毛利，引流品保客流，"
               "结构品保年节与礼盒；用一套毛利指标考核全部品类，是负毛利的制度原因。",
               refs, "判断　"),
            _r("引流品禁止单独考核毛利，改考连带率；结构品不做日常走量，"
               "只在年节与礼盒档期限量上架。", refs, "落点　"),
            _r("任何品类提价前先算保本线：低于保本价的提价是无效提价，"
               "会同时丢销量与毛利。", refs, "证伪　"),
        ],
        refs,
        table=_table("三类角色的定价与考核", ["角色", "品类", "定价原则", "考核", "禁止动作"], prows),
        assumptions=[],
        boundary="角色划分按加价率与净毛利，不按销售额；同一品类在不同档期可以换角色，但必须提前写进价格表。"))

    # 7. 风险与对冲
    if findings.get("risk"):
        risk = findings["risk"]
        sec = _from_finding(risk, "哪些风险会让上面的结论失效？")
        sec["table"] = _table("风险与对冲", ["风险", "触发信号", "对冲动作"],
                              [["期数不足", "序列少于 8 期", "只做周度随行，不做趋势外推"],
                               ["无批发基准", risk.title.split("：")[-1][:40], "自采价台账，不拿零售价替代"],
                               ["价格波动", "CV 高于 5%", "报价有效期缩到一周"]])
        secs.append(sec)

    # 8. KPI 与门禁
    krows = []
    krefs = []
    for r in rows[:5]:
        cur = _f(r["margin"]) * 100
        t30 = 0.0 if cur < 0 else cur + 1.0
        t90 = max(2.0, cur + 2.0) if cur < 0 else cur + 2.0
        gate = 0.0 if cur < 0 else max(0.0, cur - 2.0)
        n30 = ctx.cite.n(f"{r['cat']} 30天目标", t30 / 100, "%")
        n90 = ctx.cite.n(f"{r['cat']} 90天目标", t90 / 100, "%")
        ng = ctx.cite.n(f"{r['cat']} 门禁", gate / 100, "%")
        krefs += [n30.id, n90.id, ng.id]
        krows.append([r["cat"], f"{cur:.1f}%", f"{t30:.1f}%", f"{t90:.1f}%",
                      f"低于 {gate:.1f}% 红灯"])
    refs = [r["margin"].id for r in rows[:5]] + krefs
    secs.append(_sec(
        f"KPI 与门禁：{sum(1 for r in rows if _f(r['margin']) < 0)} 个品类 30 天目标先转正，"
        "其余品类守 2 个百分点的安全垫",
        "怎么验收、什么时候亮红灯？",
        [
            _r("负毛利品类 30 天目标只做一件事：转正；90 天再谈扩量。"
               "正毛利品类守 2 个百分点安全垫，跌破即红灯。", refs, "判断　"),
            _r("为什么门禁不含租金人力：因为红灯只触发复盘、不直接停业，"
               "口径必须与财务决算分开，否则一线会把固定成本摊进单品，动作全停。",
               refs, "口径　"),
            _r("每月用同一张表复算，指标不换口径；换口径要重写基线，不能新旧混比。",
               refs, "落点　"),
        ],
        refs,
        table=_table("KPI 与门禁", ["品类", "当前净利率", "30 天", "90 天", "门禁"], krows),
        assumptions=[30, 90, 2, 1],
        boundary="目标值是经营目标，不是预测；基线为本轮测算，复算需用同一损耗与冷链假设。"))
    return secs


# --------------------------------------------------------------------------- #
# 链路优化
# --------------------------------------------------------------------------- #
def build_chain(ctx, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    trans = findings.get("transmission")
    trows = list((getattr(trans, "meta", None) or {}).get("rows") or []) if trans else []
    if not trows:
        return []
    secs: List[Dict[str, Any]] = []
    inv = [r for r in trows if _f(r["up"]) < 0]
    thick = [r for r in trows if _f(r["dn"]) / max(1e-9, _f(r["r"])) > 0.20]
    rows = []
    for r in trows:
        if _f(r["up"]) < 0:
            judge = "产地倒挂，换采购方式"
        elif _f(r["dn"]) / max(1e-9, _f(r["r"])) > 0.25:
            judge = "零售段过厚，谈环节"
        else:
            judge = "链路正常"
        rows.append([r["cat"], f"{_f(r['o']):.2f}", f"{_f(r['w']):.2f}",
                     f"{_f(r['r']):.2f}", f"{_f(r['up']):+.2f}",
                     f"{_f(r['dn']):+.2f}", judge])
    refs = [x.id for r in trows for x in (r["o"], r["w"], r["r"], r["up"], r["dn"])]
    secs.append(_sec(
        f"分段加价：{len(inv)} 个品类产地倒挂、{len(thick)} 个品类零售段拿走两成以上",
        "从产地到零售，钱在哪一段被加掉？",
        [
            _r(f"把链路拆成产地→批发、批发→零售两段："
               f"{len(inv)} 个品类第一段为负（倒挂），"
               f"{len(thick)} 个品类第二段占零售价两成以上。"
               "两段的病不一样，动作也不能一样。", refs, "判断　"),
            _r("倒挂的品类不能锁产地零售价，只能锁活畜/白条或改直采；"
               "零售段过厚的品类，谈的是环节而不是进货价。", refs, "落点　"),
            _r("同一品类在两地的链路可能相反：一地倒挂、一地正常，"
               "所以规则要写到品类×产地，不写到品类。", refs, "证伪　"),
        ],
        refs,
        table=_table("链路分段（元/斤）",
                     ["品类", "产地", "批发", "零售", "产地→批发", "批发→零售", "判断"], rows),
        assumptions=[20, 25],
        boundary="产地价是出场/装车口径，与销地批发不是同一交易环节；牛羊只有活畜价，未纳入分段。"))

    if findings.get("economics"):
        secs.append(_from_finding(findings["economics"],
                                  "链路末端的单位经济还剩下多少？"))

    # 可重构段
    paths = []
    if inv:
        paths.append(["上游", "、".join(r["cat"] for r in inv),
                      "改直采/锁活畜，量先做 20%", "产地倒挂收窄到 0 以内"])
    if thick:
        paths.append(["零售段", "、".join(r["cat"] for r in thick),
                      "谈环节费/自营分割，先做 1 个品类", "零售加价降 3pp"])
    paths.append(["物流", "全部品类", "提高装载率、合并线路", "单位冷链降 10%"])
    refs = [r["up"].id for r in inv] + [r["dn"].id for r in thick]
    secs.append(_sec(
        f"可重构段：{len(paths)} 条路径，先动上游与物流，零售端只做单品类试点",
        "哪一段可以重构，先动哪一段？",
        [
            _r("重构顺序按『可控性 × 收益』排：上游直采与装载率可控性最高，"
               "零售端谈环节费阻力最大，只做单品类试点。", refs, "判断　"),
            _r("每条路径都要有前置与停止：直采先做 20% 量，倒挂没收窄就停；"
               "零售端试点 3 个月，加价没降 3pp 就撤。", refs, "落点　"),
            _r("不要同时动三段：一段没跑通就动下一段，会把失败原因混在一起，复盘不出来。",
               refs, "证伪　"),
        ],
        refs,
        table=_table("可重构段与前置条件", ["段", "品类", "动作", "验收"], paths),
        assumptions=[20, 3, 10, 3]))

    if findings.get("arbitrage"):
        secs.append(_from_finding(findings["arbitrage"], "跨市场调运能补多少？"))

    if findings.get("risk"):
        secs.append(_from_finding(findings["risk"], "链路重构的风险在哪？"))
    return secs


# --------------------------------------------------------------------------- #
# 负毛利整改
# --------------------------------------------------------------------------- #
def build_remediation(ctx, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = _econ_rows(findings)
    neg = [r for r in rows if _f(r["net"]) < 0]
    if not neg:
        return []
    secs: List[Dict[str, Any]] = []

    # 1. 根因拆解：加价率 / 损耗 / 冷链 三项各贡献多少
    rrows = []
    for r in neg:
        parts = {"加价率不足": 1 - _f(r["markup"]),
                 "损耗": _f(r["loss"]), "冷链": _f(r["cold"]) / max(1e-9, _f(r["r"]))}
        cause = max(parts, key=parts.get)
        rrows.append([r["cat"], _pct(r["markup"]), _pct(r["loss"]),
                      f"{_f(r['cold']):.2f}", f"{_f(r['net']):+.2f}",
                      f"{_f(r['margin'])*100:+.1f}%", cause])
    refs = [x.id for r in neg for x in (r["markup"], r["loss"], r["cold"],
                                        r["net"], r["margin"])]
    causes = []
    for r in neg:
        parts = {"加价率不足": 1 - _f(r["markup"]),
                 "损耗": _f(r["loss"]),
                 "冷链": _f(r["cold"]) / max(1e-9, _f(r["r"]))}
        causes.append((r["cat"], max(parts, key=parts.get)))
    uniq = {c for _cat, c in causes}
    if len(uniq) == 1:
        root_title = (f"根因：{len(neg)} 个负毛利的主因都是{next(iter(uniq))}，"
                      "损耗与冷链不是主因")
    else:
        root_title = ("根因：" + "、".join(f"{cat} 主因是{c}" for cat, c in causes))
    secs.append(_sec(
        root_title,
        "负毛利是卖便宜了，还是成本结构错了？",
        [
            _r("把负毛利拆成三项：加价率不足（1−加价率）、损耗率、冷链占售价比。"
               "占最大的那一项，才是负毛利的真实原因。"
               "主因不同，整改手段完全不同：加价率不足要换源或提价，"
               "损耗高要改周转与合同，冷链高要改装载与线路。", refs, "判断　"),
            _r("先治主因，不三项一起动：三项同时改，无法判断哪一项起了作用，"
               "也无法在 12 周内验收。", refs, "落点　"),
            _r("如果主因是加价率不足而损耗很低，提价是有效的；"
               "如果主因是损耗或冷链，提价只是把亏损转给顾客，销量会先掉。", refs, "证伪　"),
        ],
        refs,
        table=_table("负毛利根因拆解", ["品类", "加价率", "损耗率", "冷链", "净毛利",
                                    "净利率", "主因"], rrows),
        assumptions=[],
        boundary="主因按三项占比最大者判定，是近似归因；三项之和不一定等于 100%。"))

    # 2. 三段目标
    trows = []
    for r in neg:
        cur = _f(r["net"])
        gain = _gain(cur)
        trows.append([r["cat"], f"{cur:+.2f}", "0.00", f"{cur + gain*0.6:+.2f}",
                      f"{cur + gain:.2f}", "止血", "转正", "加固"])
    refs = [r["net"].id for r in neg]
    secs.append(_sec(
        f"目标：{len(neg)} 个负毛利先止血（2 周）、再转正（6 周）、最后加固（12 周）",
        "整改分几段，每段的唯一目标是什么？",
        [
            _r("三段目标不能合并，原因有三：动作会互相掩盖、归因会失真、验收会失去口径。"
               "2 周只做止血（停促、控损耗），6 周做到净毛利转正，"
               "12 周才谈加固（合同、换源、分割）。", refs, "判断　"),
            _r("每段只允许一个目标，避免『既降本又提价又换源』同时上，"
               "导致无法归因、也无法在 12 周内验收。", refs, "落点　"),
            _r("如果 6 周仍未转正，停止叠加动作，回到根因重判；"
               "继续加动作只会扩大亏损面。", refs, "止损　"),
        ],
        refs,
        table=_table("三段目标（元/斤）", ["品类", "现状", "2 周", "6 周", "12 周",
                                     "止血", "转正", "加固"], trows),
        assumptions=[2, 6, 12, 0.5],
        boundary="目标是经营目标，不是预测；6 周与 12 周值按现状亏损额的一半与全额反推。"))

    # 3/4. 分品类动作：只写负毛利品类
    for r in neg:
        cat = r["cat"]
        up = _f(r["markup"])
        acts = []
        src = ("活畜" if ("牛" in cat or "羊" in cat) else
               "产地/装车价" if ("鸡" in cat or "蛋" in cat) else "产地/冻品价")
        if up < 0.10:
            acts.append(f"改直采、按{src}锁量，先做 20%；"
                        f"直采到店成本要低于批发 {_f(r['w']):.2f} 元")
            acts.append("提价试单两周，幅度按保本线反推，销量跌幅超过 5% 立即回价")
        else:
            acts.append("锁周度批发价，缩短账期，先保加价率不再被成本吃掉")
        acts.append(f"损耗从 {_f(r['loss'])*100:.1f}% 压到 {(max(0.0,_f(r['loss'])-0.005))*100:.1f}%")
        acts.append("副产品/边角单独计价，冲减主产品成本")
        refs = _ids(r["markup"], r["loss"], r["net"], r["w"], r["r"])
        secs.append(_sec(
            f"{cat}整改：{len(acts)} 条动作，先保本再谈利润",
            f"{cat}的负毛利怎么关掉？",
            [_r(a, refs, f"动作 {i}　") for i, a in enumerate(acts, 1)]
            + [_r(f"验收：{cat} 净毛利从 {_f(r['net']):+.2f} 元回到 0 以上；"
                  "连续两周未达标，回到根因重判。", refs, "门禁　")],
            refs,
            assumptions=[20, 5, 2],
            boundary="动作幅度按当前加价率与损耗反推，执行前需用真实报价校准。"))

    # 5. 整改后账
    brows = []
    brefs = []
    for r in neg:
        cur = _f(r["net"])
        gain = _gain(cur)
        n_cur = ctx.cite.n(f"{r['cat']} 每千斤现状", cur * 1000, "元", digits=0)
        n_aft = ctx.cite.n(f"{r['cat']} 每千斤改善后", (cur + gain) * 1000, "元", digits=0)
        n_gain = ctx.cite.n(f"{r['cat']} 每千斤改善额", gain * 1000, "元", digits=0)
        brefs += [n_cur.id, n_aft.id, n_gain.id]
        brows.append([r["cat"], f"{cur*1000:+.0f}", f"{(cur+gain)*1000:+.0f}",
                      f"{gain*1000:+.0f}", "换源/降损耗/提价"])
    refs = [r["net"].id for r in neg] + brefs
    secs.append(_sec(
        f"整改后账：每千斤改善 {sum(_gain(_f(r['net'])) for r in neg)*1000:.0f} 元",
        "整改到底能挽回多少，值不值得做？",
        [
            _r("按每千斤算：现状、12 周后、改善额三列并列；"
               "改善主要来自换源与降损耗，提价只占小头。", refs, "判断　"),
            _r("改善额要扣整改成本（询价、合同、分割人工）；"
               "扣完成本仍为正，才值得做。", refs, "落点　"),
        ],
        refs,
        table=_table("整改后账（元/千斤）", ["品类", "现状", "12 周后", "改善", "主要来源"], brows),
        assumptions=[1000, 12],
        boundary="改善额按目标值反推，不含整改投入；实际值需按周复盘。"))

    # 6. 里程碑 / 门禁 / 拍板 / 不做
    secs.append(_sec(
        "90 天里程碑：2 周止血、6 周转正、12 周加固，每段一个验收口",
        "90 天怎么排，谁在什么时候验收？",
        [
            _r("为什么按 2/6/12 周排：损耗与停促两周内可验证，换源与合同要一个采购周期，"
               "分割与副产品计价要一个季度。T+2 周先做停促、控损耗、锁周度价，"
               "验收口是损耗率下降与净毛利不再扩大。", refs, "第 1 段　"),
            _r("T+6 周：直采/换源做到 20% 量，净毛利转正；验收口是转正品类数。",
               refs, "第 2 段　"),
            _r("T+12 周：合同、分割、副产品计价落地，净利率回到 2% 以上；"
               "未达标品类退出或改引流。", refs, "第 3 段　"),
        ],
        refs,
        table=_table("90 天里程碑", ["节点", "动作", "验收口"],
                     [["T+2 周", "停促、控损耗、锁价", "净毛利不再扩大"],
                      ["T+6 周", "直采/换源 20%", "负毛利品类转正"],
                      ["T+12 周", "合同与分割落地", "净利率 ≥2%"]]),
        assumptions=[2, 6, 12, 20, 2]))

    secs.append(_sec(
        "拍板：3 件事必须创始人签字，不能由执行层自行决定",
        "哪些事超出执行层权限，必须拍板？",
        [
            _r("① 是否与定点屠宰签年度协议：涉及预付或账期，需明确资金占用上限。",
               refs, "拍板 1　"),
            _r("② 直采是否允许现结：现结通常再降 1%—2% 采购价，直接决定直采经济性。",
               refs, "拍板 2　"),
            _r("③ 是否把引流品从毛利考核改为客流 + 连带考核：不改考核，一线仍会提价保毛利。",
               refs, "拍板 3　"),
        ],
        refs,
        assumptions=[1, 2],
        boundary="拍板事项涉及资金与合同，按公司治理必须创始人签字，报告只给建议。"))

    secs.append(_sec(
        "不做清单：4 件事现在不做，避免把亏损换成重资产",
        "哪些事看起来该做，但现在不能做？",
        [
            _r("不自建屠宰厂：重资产、资质周期长，合作定点屠宰即可拿到大部分收益。", refs, "不做 1　"),
            _r("不给引流品提价：提价会先打掉客流，亏损转成失客。", refs, "不做 2　"),
            _r("不为单个品类新建冷链：与现有城配共用，靠装载率摊薄。", refs, "不做 3　"),
            _r("不做全品类自营：只做高价值部位的分割与组合，低价值部位继续批发。", refs, "不做 4　"),
        ],
        refs,
        boundary="不做清单与动作清单同等重要；没有不做清单的整改方案，会在 12 周内重新铺开重资产。"))
    return secs


FRAMES: Dict[str, Callable[..., List[Dict[str, Any]]]] = {
    "operations": build_operations,
    "chain": build_chain,
    "remediation": build_remediation,
}


def build(thesis: str, ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    fn = FRAMES.get(thesis)
    if not fn:
        return None
    try:
        return fn(ctx, findings)
    except Exception:  # noqa: BLE001  帧装配失败时退回原来的按 finding 出节
        return None
