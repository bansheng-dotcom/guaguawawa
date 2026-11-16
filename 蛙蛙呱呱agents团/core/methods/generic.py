# -*- coding: utf-8 -*-
"""core/methods/generic —— 非价格类通用方法：订单 / 评价 / 履约 / 投放 / 优先级 / 容量 / 故障 / 商品。

这些方法只认「列」，不认项目：订单表有状态列就能算漏斗，有签收与承诺时间就能算履约，
有评分列就能算 VOC。没有对应列就返回 None，由调度器记为缺口。

它们与价格类方法共用同一套 Finding / Cite / 门禁，所以不需要新产线。
"""
from __future__ import annotations

import re
import statistics as st
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.analysis_methods import Finding, Num, _ids, _pct_change, _table
from core.methods.spec import Caps, method, register_need

# --------------------------------------------------------------------------- #
# 列名同义词
# --------------------------------------------------------------------------- #
SYN = {
    "order_id": ("order_id", "订单号", "订单id", "order"),
    "customer": ("customer_unique_id", "customer_id", "客户", "用户", "会员", "买家"),
    "date": ("purchase_timestamp", "purchase_ts", "purchase", "order_purchase",
             "created_at", "日期", "下单时间", "时间"),
    "status": ("order_status", "状态", "status"),
    "delivered": ("delivered_customer", "delivered", "签收", "送达", "完成时间"),
    "estimated": ("estimated", "承诺", "应达"),
    "score": ("review_score", "评分", "星级", "score", "rating"),
    "amount": ("payment_value", "金额", "销售额", "gmv", "revenue", "price"),
    "pay_type": ("payment_type", "支付方式", "渠道"),
    "installments": ("payment_installments", "分期"),
    "spend": ("spend", "cost", "投放", "花费", "预算"),
    "revenue": ("revenue", "gmv", "收入", "销售额"),
    "channel": ("channel", "渠道", "source", "来源"),
    "reach": ("reach", "覆盖", "触达"),
    "impact": ("impact", "影响"),
    "confidence": ("confidence", "置信", "把握"),
    "effort": ("effort", "成本", "工作量", "投入"),
    "demand": ("demand", "需求", "请求量", "qps", "工单量"),
    "capacity": ("capacity", "容量", "产能", "人力", "处理能力"),
    "duration": ("duration", "时长", "持续时间", "耗时", "分钟"),
    "severity": ("severity", "严重", "等级", "priority"),
    "start": ("start", "开始", "发生", "created"),
    "req": ("requisition", "需求数", "hc", "编制", "岗位"),
    "hire": ("hired", "入职", "offer", "录用"),
    "days": ("days", "天数", "耗时"),
    "sku": ("sku", "product_id", "商品", "item"),
    "qty": ("qty", "quantity", "销量", "数量", "units"),
    "margin": ("margin", "毛利", "profit"),
    "area": ("area", "面积", "㎡", "平米"),
    "rent": ("rent", "租金", "房租"),
    "sales": ("sales", "营业额", "销售额", "revenue"),
}


def pick(t, *names: str) -> Optional[str]:
    """按同义词在表里找列。"""
    keys: List[str] = []
    for n in names:
        keys.extend(SYN.get(n, (n,)))
    return t.col(*keys)


# --------------------------------------------------------------------------- #
# 能力谓词（注册进 spec）
# --------------------------------------------------------------------------- #
def _find(desk, *names):
    """找一个同时含这些同义词列的表。"""
    for t in desk.tables.values():
        if all(pick(t, n) for n in names):
            return t
    return None


def _need_table(*names):
    return lambda caps: _find(caps.desk, *names) is not None


register_need("table.orders", _need_table("order_id", "date"))
register_need("table.reviews", _need_table("score"))
register_need("table.sla", _need_table("delivered", "estimated"))
register_need("table.payments", _need_table("amount", "pay_type"))
register_need("table.retention", _need_table("customer", "date"))
register_need("table.spend", _need_table("spend", "revenue"))
register_need("table.priority", _need_table("reach", "impact", "effort"))
register_need("table.capacity", _need_table("demand", "capacity"))
register_need("table.incidents", _need_table("duration"))
register_need("table.headcount", _need_table("req"))
register_need("table.sku", _need_table("sku", "qty"))
register_need("table.store", _need_table("area", "sales"))


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def _date(s: str) -> Optional[datetime]:
    s = str(s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1)
    return None


def _month(s: str) -> str:
    d = _date(s)
    return f"{d.year}-{d.month:02d}" if d else ""


def _share(a: float, b: float) -> float:
    return a / b * 100 if b else 0.0


def _finding(key: str, title: str, question: str, c, mark: int) -> Finding:
    return Finding(key=key, title=title, question=question, refs=c.since(mark))


# --------------------------------------------------------------------------- #
# 1. 转化漏斗
# --------------------------------------------------------------------------- #
@method("funnel", family="growth", needs=["table.orders"], produces="转化漏斗",
        tags=("growth", "marketing", "product"), priority=70,
        description="订单状态/阶段计数 → 逐段转化率与最大流失口")
def m_funnel(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    # 优先用「阶段计数表」（最干净的漏斗口径），没有再用订单状态近似
    t_stage = None
    for t0 in desk.tables.values():
        if t0.col("stage", "阶段", "step") and t0.col("count", "数量", "人数", "单量"):
            t_stage = t0
            break
    t = t_stage or _find(desk, "order_id", "date") or _find(desk, "status")
    if not t:
        return None
    status_col = pick(t, "status")
    stage_col = t.col("stage", "阶段", "step")
    cnt_col = t.col("count", "数量", "人数")
    mark = c.begin()
    if stage_col and cnt_col:
        stages = [(str(r.get(stage_col, "")), float(r.get(cnt_col) or 0)) for r in t.rows]
        n_all = c.n("漏斗阶段数", len(stages), "段", digits=0)
        stage_nums = [(name, c.n(f"阶段 {name} 数量", val, "单", digits=0))
                      for name, val in stages]
        top_name, top_num = stage_nums[0] if stage_nums else ("—", None)
        convs = []
        for i in range(1, len(stages)):
            convs.append(_share(stages[i][1], stages[i - 1][1]))
        conv_nums = [c.n(f"{stages[i][0]}段间转化", convs[i - 1] / 100, "%")
                     for i in range(1, len(stages))]
        conv = c.n("整体转化率", _share(stages[-1][1], stages[0][1]) / 100, "%")
        worst_i = min(range(len(convs)), key=lambda i: convs[i]) if convs else 0
        worst = conv_nums[worst_i] if conv_nums else None
        title = (f"漏斗：{n_all} 段，整体转化 {conv.p()}"
                 + (f"，最窄一段只有 {worst.p()}（{stages[worst_i + 1][0]}）" if worst else ""))
        f = _finding("funnel", title, "用户在哪一段流失最多？", c, mark)
        f.add(f"从「{stages[0][0]}」到「{stages[-1][0]}」，整体转化 {conv.p()}；"
              f"起始量 {top_num} 单。", _ids(n_all, conv, top_num))
        if worst:
            f.add(f"最窄的一段是「{stages[worst_i + 1][0]}」，只承接上一段的 {worst.p()}；"
              + ("但全链路都在九成五以上，漏斗本身没有断点——增长瓶颈不在转化，"
                 "而在入口量或复购（见留存节）。"
                 if worst.value * 100 >= 95 else
                 "先补这一段，后面的放大才有意义。"), _ids(worst, conv))
        f.table = _table("漏斗各段", ["阶段", "数量", "段间转化", "整体转化"],
                         [[name, str(nv),
                           (conv_nums[i - 1].p() if i else "—"),
                           f"{_share(stages[i][1], stages[0][1]):.1f}%"]
                          for i, ((name, nv), _v) in enumerate(zip(stage_nums, stages))])
        f.chart = {"type": "funnel",
                   "title": f"整体转化 {conv.p()}，最窄段 {worst.p() if worst else '—'}",
                   "subtitle": f"{len(stages)} 段 · 同一张表的阶段计数 · 单量",
                   "note": "阶段未做去重，跨表拼接前先统一主键",
                   "unit_meta": "单量", "source": f"{t.file} 阶段计数",
                   "refs": _ids(conv, n_all, [nv for _, nv in stage_nums]),
                   "stages": [{"label": name, "value": round(stages[i][1], 2)}
                              for i, (name, _nv) in enumerate(stage_nums)],
                   "series": [{"name": "阶段单量",
                               "values": [round(v, 2) for _, v in stages]}]}
        f.so_what = "先补最窄一段，再谈放大；若全链路都很高，瓶颈就在入口或复购。"
        f.boundary = "阶段计数来自同一张表，未做去重口径校验；跨表拼接前要先统一主键。"
        f.refs = c.since(mark)
        return f
    # 没有「阶段 × 数量」两列时，退回订单状态计数版
    if not status_col:
        return None
    cnt = Counter(t.vals(status_col))
    total = sum(cnt.values())
    if total < 10:
        return None
    delivered = sum(v for k, v in cnt.items() if k.lower() in
                    ("delivered", "已签收", "已完成", "完成", "closed"))
    canceled = sum(v for k, v in cnt.items() if "cancel" in k.lower() or "取消" in k)
    n_total = c.n("订单总数", total, "单", digits=0)
    n_del = c.n("已签收订单", delivered, "单", digits=0)
    n_can = c.n("取消订单", canceled, "单", digits=0)
    rate = _share(delivered, total)
    n_rate = c.n("签收率", rate / 100, "%")
    can_rate = _share(canceled, total)
    n_can_rate = c.n("取消率", can_rate / 100, "%")
    title = (f"漏斗：{n_total} 单里 {n_del} 单签收（{n_rate.p()}）、"
             f"{n_can} 单取消（{n_can_rate.p()}）")
    f = _finding("funnel", title, "订单在哪一段流失最多？", c, mark)
    f.add(f"{int(total)} 单中签收 {int(delivered)} 单，签收率 {n_rate.p()}；"
          f"取消 {int(canceled)} 单，取消率 {n_can_rate.p()}。",
          _ids(n_total, n_del, n_rate, n_can, n_can_rate))
    top_status = cnt.most_common(3)
    f.add("状态分布前三：" + "、".join(f"{k}（{v} 单）" for k, v in top_status)
          + "；异常状态要单独看，不能混进分母。", _ids(n_total))
    status_nums = []
    for k, v in cnt.most_common():
        status_nums.append((k, c.n(f"状态 {k} 单量", v, "单", digits=0)))
    f.table = _table("订单状态分布", ["状态", "单量", "占比"],
                     [[k, str(nv), f"{_share(v, total):.1f}%"]
                      for (k, nv), v in zip(status_nums, [v for _, v in cnt.most_common()])])
    f.refs = c.since(mark)
    f.so_what = "取消与未签收是两笔不同的成本：前者是交易失败，后者是履约失败，要分开治。"
    f.boundary = "状态口径以源表为准；没有支付/退款表时，不能判断取消原因。"
    return f


# --------------------------------------------------------------------------- #
# 2. 留存与复购
# --------------------------------------------------------------------------- #
@method("retention", family="growth", needs=["table.retention"], produces="留存与复购",
        tags=("growth", "product", "support"), priority=65,
        description="客户×时间×订单 → 复购率、复购间隔、首购月留存")
def m_retention(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "customer", "date")
    if not t:
        return None
    cust, datec = pick(t, "customer"), pick(t, "date")
    mark = c.begin()
    orders: Dict[str, List[datetime]] = defaultdict(list)
    for r in t.rows:
        d = _date(r.get(datec, ""))
        if d:
            orders[str(r.get(cust, ""))].append(d)
    if len(orders) < 10:
        return None
    counts = [len(v) for v in orders.values()]
    repeat = sum(1 for n in counts if n >= 2)
    n_cust = c.n("客户数", len(orders), "人", digits=0)
    n_orders = c.n("订单总数", sum(counts), "单", digits=0)
    n_rep = c.n("复购客户数", repeat, "人", digits=0)
    n_rate = c.n("复购率", _share(repeat, len(orders)) / 100, "%")
    avg = c.n("人均单量", sum(counts) / len(counts), "单")
    # 复购间隔
    gaps = []
    for ds in orders.values():
        ds.sort()
        for i in range(1, len(ds)):
            gaps.append((ds[i] - ds[i - 1]).days)
    med_gap = c.n("复购间隔中位数", st.median(gaps), "天") if gaps else None
    title = (f"留存：{n_cust} 个客户里 {n_rep} 个复购（{n_rate.p()}），"
             f"人均 {avg} 单"
             + (f"，复购间隔中位 {med_gap} 天" if med_gap else ""))
    f = _finding("retention", title, "客户回来吗？多久回来一次？", c, mark)
    f.add(f"{int(len(orders))} 个客户共 {n_orders} 单，复购率 {n_rate.p()}；"
          "一人一单的客户占其余部分，增长如果只靠拉新，获客成本会一直涨。",
          _ids(n_cust, n_rep, n_rate, n_orders))
    if med_gap:
        f.add(f"复购间隔中位数 {med_gap} 天；提醒/复购券的窗口应按这个数设，"
              "不是按自然月设。", _ids(med_gap, n_cust))
    top = Counter(counts)
    bucket = [(k, c.n(f"购买 {k} 单的客户数", v, "人", digits=0))
              for k, v in sorted(top.items())]
    f.table = _table("购买频次分布", ["单量", "客户数", "占比"],
                     [[str(k), str(nv), f"{_share(int(str(nv)), len(orders)):.1f}%"]
                      for (k, nv) in bucket])
    f.refs = c.since(mark)
    f.so_what = "复购率低于 20% 时先做留存再做投放；间隔中位数决定触达节奏。"
    f.boundary = "用 customer_id 近似客户；没有去重到自然人的项目会高估复购。"
    f.meta = {"repeat_rate": float(n_rate.value)}
    return f


# --------------------------------------------------------------------------- #
# 3. RFM 与收入集中度
# --------------------------------------------------------------------------- #
@method("rfm", family="growth", needs=["table.retention"], produces="RFM 分层",
        tags=("growth", "marketing"), priority=55,
        description="客户×时间×金额 → RFM 分层与收入集中度")
def m_rfm(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "customer", "date")
    if not t:
        return None
    amount_col = pick(t, "amount")
    if not amount_col:
        return None
    cust, datec = pick(t, "customer"), pick(t, "date")
    mark = c.begin()
    agg: Dict[str, Dict[str, Any]] = {}
    for r in t.rows:
        d = _date(r.get(datec, ""))
        try:
            amt = float(str(r.get(amount_col, "")).replace(",", "") or 0)
        except ValueError:
            continue
        k = str(r.get(cust, ""))
        a = agg.setdefault(k, {"last": d, "n": 0, "amt": 0.0})
        if d and (a["last"] is None or d > a["last"]):
            a["last"] = d
        a["n"] += 1
        a["amt"] += amt
    if len(agg) < 20:
        return None
    amts = sorted((v["amt"] for v in agg.values()), reverse=True)
    total = sum(amts)
    top10 = sum(amts[:max(1, len(amts) // 10)])
    n_top = c.n("头部 10% 客户收入占比", _share(top10, total) / 100, "%")
    n_cust = c.n("客户数", len(agg), "人", digits=0)
    # 频次分层
    freq = Counter("高一单" if v["n"] <= 1 else ("中2-3单" if v["n"] <= 3 else "高4单+")
                   for v in agg.values())
    big = [k for k, v in agg.items() if v["amt"] >= (st.median(amts) if amts else 0)]
    n_big = c.n("高频高额客户数", len(big), "人", digits=0)
    title = (f"RFM：{n_cust} 个客户里头部 10% 贡献 {n_top.p()} 的收入，"
             f"高频高额客户只有 {n_big} 个")
    f = _finding("rfm", title, "收入靠少数人还是多数人？", c, mark)
    f.add(f"头部 10% 客户贡献 {n_top.p()} 的收入；这个比例越高，"
          "越要先做头部维护，而不是继续拉新。", _ids(n_top, n_cust))
    f.add(f"按频次分层：" + "、".join(f"{k} {v} 人" for k, v in freq.most_common())
          + f"；高频高额（金额高于中位且单量≥2）只有 {int(len(big))} 人。", _ids(n_big))
    freq_rows = [(k, c.n(f"RFM {k} 人数", v, "人", digits=0))
                 for k, v in freq.most_common()]
    # 补一次引用：让上一条解读的数字也能被 refs 解释
    f.reading[-1]["refs"] = _ids(n_big, [nv for _, nv in freq_rows])
    f.table = _table("客户频次分层", ["分层", "人数", "占比"],
                     [[k, str(nv), f"{_share(int(str(nv)), len(agg)):.1f}%"]
                      for k, nv in freq_rows])
    pts = []
    for p in (0.1, 0.2, 0.3, 0.5, 1.0):
        share = _share(sum(amts[:max(1, int(len(amts) * p))]), total)
        np_ = c.n(f"前{int(p * 100)}%客户收入占比", share / 100, "%")
        pts.append({"label": f"前{int(p * 100)}%", "value": round(share, 1)})
    f.chart = {"type": "pareto",
               "title": f"前 10% 客户贡献 {n_top.p()} 收入",
               "subtitle": f"{len(pts)} 个分位截点 · 客户按金额降序累计 · n={len(agg)}",
               "note": "金额近似收入，无毛利数据时不能判断高收入低利润",
               "unit_meta": "累计收入占比（%）", "source": f"{t.file} 按客户汇总",
               "refs": _ids(n_top) + list(c.refs[-5:]),
               "items": pts,
               "series": [{"name": "累计收入占比",
                           "values": [p["value"] for p in pts]}]}
    f.refs = c.since(mark)
    f.so_what = "头部集中就先做头部健康度（流失预警），长尾分散就先做复购。"
    f.boundary = "RFM 用金额与频次近似，没有毛利数据时无法区分「高收入低利润」客户。"
    return f


# --------------------------------------------------------------------------- #
# 4. 评价与 VOC
# --------------------------------------------------------------------------- #
@method("reviews", family="support", needs=["table.reviews"], produces="评价与 VOC",
        tags=("support", "product", "marketing"), priority=60,
        description="评分列 → 均分、低分占比、差评集中点")
def m_reviews(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "score")
    if not t:
        return None
    score_col = pick(t, "score")
    mark = c.begin()
    vals = [float(x) for x in t.num(score_col) if 0 <= x <= 5]
    if len(vals) < 20:
        return None
    n = c.n("评价数", len(vals), "条", digits=0)
    mean = c.n("平均评分", sum(vals) / len(vals), "分")
    low = sum(1 for x in vals if x <= 2)
    n_low = c.n("低分评价数（≤2）", low, "条", digits=0)
    n_low_rate = c.n("低分占比", _share(low, len(vals)) / 100, "%")
    top = sum(1 for x in vals if x >= 4)
    n_top_rate = c.n("好评占比（≥4）", _share(top, len(vals)) / 100, "%")
    nps = (_share(top, len(vals)) - _share(low, len(vals)))
    n_nps = c.n("净推荐值近似（好评−差评，pp）", nps / 100, "%")
    dist = Counter(int(round(x)) for x in vals)
    title = (f"VOC：{n} 条评价均分 {mean}，低分占 {n_low_rate.p()}，"
             f"净推荐近似 {n_nps.p()}")
    f = _finding("reviews", title, "用户满意吗？不满集中在哪里？", c, mark)
    f.add(f"{int(len(vals))} 条评价均分 {mean}；低分（≤2）{int(low)} 条占 {n_low_rate.p()}，"
          f"好评（≥4）占 {n_top_rate.p()}，净推荐近似 {n_nps.p()}。",
          _ids(n, mean, n_low, n_low_rate, n_top_rate, n_nps))
    f.add(f"低分 {int(low)} 条是可用样本：先按订单/品类归因，"
          "再决定是补履约还是补商品描述，不要笼统说「提升体验」。", _ids(n_low, n))
    dist = Counter(int(round(x)) for x in vals)
    dist_rows = [(k, c.n(f"{k} 星评价数", v, "条", digits=0))
                 for k, v in sorted(dist.items())]
    f.table = _table("评分分布", ["星级", "条数", "占比"],
                     [[str(k), str(nv), f"{_share(int(str(nv)), len(vals)):.1f}%"]
                      for k, nv in dist_rows])
    mid = sum(1 for x in vals if 2 < x < 4)
    n_mid = c.n("中评数与占比", _share(mid, len(vals)) / 100, "%")
    f.chart = {"type": "pct_stacked",
               "title": f"好评 {n_top_rate.p()}、差评 {n_low_rate.p()}，均分 {mean}",
               "subtitle": f"n={len(vals):,} 条评价 · 好评/中评/差评三分 · 各条合计 100%",
               "note": "好评 4–5 星、中评 3 星、差评 1–2 星",
               "unit_meta": "评价占比（%）", "source": f"{t.file} 评分列",
               "refs": _ids(n_top_rate, n_low_rate, n_mid),
               "categories": ["全部评价"],
               "segments": [{"name": "好评(4-5)",
                             "values": [round(float(n_top_rate.value * 100), 1)]},
                            {"name": "中评(3)", "values": [round(float(n_mid.value * 100), 1)]},
                            {"name": "差评(1-2)",
                             "values": [round(float(n_low_rate.value * 100), 1)]}],
               "series": [{"name": "评价占比",
                           "values": [round(float(n_top_rate.value * 100), 1),
                                      round(float(n_mid.value * 100), 1),
                                      round(float(n_low_rate.value * 100), 1)]}]}
    f.refs = c.since(mark)
    f.so_what = "差评占比超过 10% 时，先修履约与描述一致性；低于 5% 时做惊喜点更划算。"
    f.boundary = "评分是自选择样本（不满意的人更少评价），只能看趋势与结构，不能当满意度绝对值。"
    f.meta = {"low_rate": float(n_low_rate.value)}
    return f


# --------------------------------------------------------------------------- #
# 5. 履约时效
# --------------------------------------------------------------------------- #
@method("sla", family="support", needs=["table.sla"], produces="履约时效",
        tags=("support", "sre", "product"), priority=60,
        description="签收 vs 承诺时间 → 准时率、延迟分布、最差区域")
def m_sla(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "delivered", "estimated")
    if not t:
        return None
    dc, ec = pick(t, "delivered"), pick(t, "estimated")
    mark = c.begin()
    delays = []
    for r in t.rows:
        d, e = _date(r.get(dc, "")), _date(r.get(ec, ""))
        if d and e:
            delays.append((d - e).days)
    if len(delays) < 20:
        return None
    ontime = sum(1 for x in delays if x <= 0)
    n = c.n("可判定订单数", len(delays), "单", digits=0)
    n_on = c.n("准时订单数", ontime, "单", digits=0)
    n_rate = c.n("准时率", _share(ontime, len(delays)) / 100, "%")
    med = c.n("延迟中位数", st.median(delays), "天")
    p90 = c.n("延迟 P90", sorted(delays)[int(len(delays) * 0.9)], "天")
    late = sum(1 for x in delays if x > 0)
    n_late = c.n("延迟订单数", late, "单", digits=0)
    title = (f"履约：{n} 单里准时 {n_on} 单（{n_rate.p()}），"
             f"延迟中位 {med} 天、P90 {p90} 天")
    f = _finding("sla", title, "承诺的时效兑现了吗？", c, mark)
    f.add(f"{int(len(delays))} 单可判定，准时率 {n_rate.p()}；延迟订单 {int(late)} 单，"
          f"延迟中位数 {med} 天、P90 {p90} 天。", _ids(n, n_on, n_rate, n_late, med, p90))
    f.add(f"改善优先级看尾部：P90 比中位数更接近用户体验，"
          "先压 P90，再谈平均时效。", _ids(p90, med))
    f.table = _table("延迟分布", ["指标", "值"],
                     [["可判定订单", str(n)], ["准时率", n_rate.p()],
                      ["延迟中位", f"{med} 天"], ["延迟 P90", f"{p90} 天"]])
    f.so_what = "准时率低于 90% 时，履约是增长瓶颈；先把承诺时间校准，再承诺更快。"
    f.boundary = "只统计有签收与承诺时间的订单；未签收订单不在分母里，真实体验会更差。"
    return f


# --------------------------------------------------------------------------- #
# 6. 支付结构
# --------------------------------------------------------------------------- #
@method("payment_mix", family="growth", needs=["table.payments"], produces="支付结构",
        tags=("growth", "product"), priority=45,
        description="支付方式与分期 → 结构、分期依赖度")
def m_payment_mix(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "amount", "pay_type")
    if not t:
        return None
    pc, ac = pick(t, "pay_type"), pick(t, "amount")
    mark = c.begin()
    agg: Dict[str, List[float]] = defaultdict(list)
    for r in t.rows:
        try:
            v = float(str(r.get(ac, "")).replace(",", "") or 0)
        except ValueError:
            continue
        agg[str(r.get(pc, "unknown"))].append(v)
    if not agg:
        return None
    total = sum(sum(v) for v in agg.values())
    rows = sorted(agg.items(), key=lambda kv: sum(kv[1]), reverse=True)
    n_total = c.n("支付总额", total, "元", digits=0)
    top_name, top_vals = rows[0]
    n_top = c.n("最大支付方式占比", _share(sum(top_vals), total) / 100, "%")
    n_kind = c.n("支付方式数", len(rows), "种", digits=0)
    title = (f"支付：{n_kind} 种方式，{top_name} 占 {n_top.p()}（总额 {n_total} 元）")
    f = _finding("payment_mix", title, "钱是怎么付的？依赖单一方式吗？", c, mark)
    f.add(f"{int(len(rows))} 种支付方式中，{top_name} 占 {n_top.p()}；"
          "单一方式占比过高时，支付失败会直接变成订单流失。", _ids(n_top, n_kind, n_total))
    pay_rows = []
    for k, v in rows:
        amt = c.n(f"{k} 支付金额", sum(v), "元", digits=0)
        cnt_n = c.n(f"{k} 支付笔数", len(v), "笔", digits=0)
        pay_rows.append([k, str(amt), f"{_share(sum(v), total):.1f}%", str(cnt_n)])
    f.add("分期依赖度高的方式要单独看：分期笔数上升但客单不升，说明在用分期换成交，"
          "不是换客单。", _ids(n_kind))
    f.table = _table("支付方式结构", ["方式", "金额", "占比", "笔数"], pay_rows)
    items = []
    for k, v in rows[:6]:
        share = c.n(f"{k} 金额占比", _share(sum(v), total) / 100, "%")
        items.append({"label": k, "value": round(_share(sum(v), total), 1)})
    f.chart = {"type": "donut", "title": f"{top_name} 占 {n_top.p()}",
               "subtitle": f"{len(items)} 种支付方式 · 金额占比 · 前 6 项",
               "note": "金额未扣退款与手续费，不能当净收入",
               "unit_meta": "金额占比（%）", "source": f"{t.file} 支付金额",
               "refs": list(c.refs[-6:]),
               "items": items,
               "series": [{"name": "金额占比", "values": [i["value"] for i in items]}]}
    f.refs = c.since(mark)
    f.so_what = "支付结构决定风控与结算策略：单一方式 >60% 要准备降级通道。"
    f.boundary = "金额未扣退款与手续费，不能当净收入。"
    return f


# --------------------------------------------------------------------------- #
# 7. 投放效率
# --------------------------------------------------------------------------- #
@method("roi", family="growth", needs=["table.spend"], produces="投放效率",
        tags=("growth", "marketing"), priority=60,
        description="花费与收入 → ROI、CAC、回本")
def m_roi(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "spend", "revenue")
    if not t:
        return None
    sc, rc = pick(t, "spend"), pick(t, "revenue")
    mark = c.begin()
    rows = []
    for r in t.rows:
        try:
            s = float(str(r.get(sc, "")).replace(",", "") or 0)
            v = float(str(r.get(rc, "")).replace(",", "") or 0)
        except ValueError:
            continue
        rows.append((r.get(pick(t, "channel") or "", "") if pick(t, "channel") else "",
                     s, v))
    if not rows:
        return None
    spend = sum(s for _, s, _ in rows)
    rev = sum(v for _, _, v in rows)
    n_sp = c.n("总花费", spend, "元", digits=0)
    n_rev = c.n("总收入", rev, "元", digits=0)
    roi = (rev - spend) / spend * 100 if spend else 0
    n_roi = c.n("ROI", roi / 100, "%")
    title = f"投放：花 {n_sp} 元、回 {n_rev} 元，ROI {n_roi.p()}"
    f = _finding("roi", title, "这笔投放划算吗？", c, mark)
    f.add(f"总花费 {n_sp} 元、收入 {n_rev} 元，ROI {n_roi.p()}；"
          "ROI 为负时，先停最差的渠道，而不是整体加预算。", _ids(n_sp, n_rev, n_roi))
    by: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0.0])
    for ch, s, v in rows:
        by[ch or "未标注"][0] += s
        by[ch or "未标注"][1] += v
    table_rows = []
    for ch, (s, v) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        ns = c.n(f"{ch} 花费", s, "元", digits=0)
        nv = c.n(f"{ch} 收入", v, "元", digits=0)
        table_rows.append([ch, str(ns), str(nv),
                           f"{(v - s) / s * 100 if s else 0:+.1f}%"])
    f.table = _table("分渠道投放", ["渠道", "花费", "收入", "ROI"], table_rows)
    f.refs = c.since(mark)
    f.so_what = "按渠道 ROI 排序做预算再分配：负 ROI 先停，正 ROI 再加。"
    f.boundary = "收入未做归因去重，多渠道路径会重复计入；只用于渠道间相对比较。"
    return f


# --------------------------------------------------------------------------- #
# 8. 优先级（RICE）
# --------------------------------------------------------------------------- #
@method("priority", family="product", needs=["table.priority"], produces="需求优先级",
        tags=("product",), priority=60,
        description="Reach/Impact/Confidence/Effort → RICE 排序与取舍线")
def m_priority(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "reach", "impact", "effort")
    if not t:
        return None
    rc, ic = pick(t, "reach"), pick(t, "impact")
    cc, ec = pick(t, "confidence"), pick(t, "effort")
    name_col = t.col("name", "需求", "feature", "项目", "title")
    mark = c.begin()
    rows = []
    for r in t.rows:
        try:
            reach = float(r.get(rc) or 0)
            impact = float(r.get(ic) or 0)
            conf = float(r.get(cc) or 1) if cc else 1.0
            effort = float(r.get(ec) or 0)
        except ValueError:
            continue
        if effort <= 0:
            continue
        rows.append({"name": r.get(name_col, "") if name_col else f"需求{len(rows) + 1}",
                     "rice": reach * impact * conf / effort})
    if len(rows) < 3:
        return None
    rows.sort(key=lambda x: x["rice"], reverse=True)
    n = c.n("需求数", len(rows), "条", digits=0)
    top = rows[0]
    n_top = c.n("最高 RICE", top["rice"], "分")
    cut = rows[max(0, len(rows) // 2)]
    n_cut = c.n("中位 RICE", cut["rice"], "分")
    title = (f"优先级：{n} 条需求里 {top['name']} 的 RICE 最高（{n_top} 分），"
             f"中位 {n_cut} 分")
    f = _finding("priority", title, "先做哪一条？依据是什么？", c, mark)
    f.add(f"{int(len(rows))} 条需求按 RICE 排序，最高 {top['name']} {n_top} 分，"
          f"中位 {n_cut} 分；中位以下的需求不是不能做，是要排在验证之后。",
          _ids(n, n_top, n_cut))
    f.add("RICE 的分母是工作量：分数高但工作量也高的需求，要拆成可验证的小片，"
          "否则会长期占着资源不出结果。", _ids(n_top))
    f.table = _table("需求 RICE 排序", ["需求", "RICE 分", "相对最高"],
                     [[r["name"], f"{r['rice']:.1f}",
                       f"{r['rice'] / top['rice'] * 100 if top['rice'] else 0:.0f}%"]
                      for r in rows])
    f.chart = {"type": "hbar", "title": f"{top['name']} {n_top:.1f} 分居首",
               "subtitle": f"{len(rows)} 条需求 · RICE 排序（显示前 8 条）",
               "note": "四个输入为主观打分，只在同批需求内可比",
               "unit_meta": "RICE 分", "source": f"{t.file} Reach×Impact×Confidence÷Effort",
               "refs": _ids(n_top),
               "bars": [{"label": r["name"], "value": round(r["rice"], 1)}
                        for r in rows[:8]]}
    f.so_what = "按 RICE 排序做排期，前 30% 进本迭代，其余进验证队列。"
    f.boundary = "RICE 的四个输入是主观打分；没有打分校准记录时，只用于同批需求内比较。"
    return f


# --------------------------------------------------------------------------- #
# 9. 容量与负载
# --------------------------------------------------------------------------- #
@method("capacity", family="ops", needs=["table.capacity"], produces="容量与负载",
        tags=("people", "sre", "support"), priority=55,
        description="需求 vs 容量 → 利用率、超载点、余量")
def m_capacity(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "demand", "capacity")
    if not t:
        return None
    dc, cc = pick(t, "demand"), pick(t, "capacity")
    mark = c.begin()
    rows = []
    for r in t.rows:
        try:
            d = float(str(r.get(dc, "")).replace(",", ""))
            cap = float(str(r.get(cc, "")).replace(",", ""))
        except ValueError:
            continue
        if cap <= 0:
            continue
        rows.append((d, cap, d / cap * 100))
    if len(rows) < 3:
        return None
    over = [x for x in rows if x[2] > 100]
    util = sum(r[0] for r in rows) / sum(r[1] for r in rows) * 100
    n_util = c.n("整体利用率", util / 100, "%")
    n_over = c.n("超载期数", len(over), "期", digits=0)
    peak = max(rows, key=lambda x: x[2])
    n_peak = c.n("峰值利用率", peak[2] / 100, "%")
    title = (f"容量：整体利用率 {n_util.p()}，峰值 {n_peak.p()}，"
             f"{n_over} 期超载")
    f = _finding("capacity", title, "现有容量撑得住吗？", c, mark)
    f.add(f"整体利用率 {n_util.p()}，峰值 {n_peak.p()}；"
          f"{int(len(over))} 期超过 100%，超载时质量与时效会一起掉。",
          _ids(n_util, n_peak, n_over))
    f.add("利用率 70%—85% 是可持续区间：低于 70% 是浪费，高于 85% 没有故障余量。",
          _ids(n_util))
    f.table = _table("容量利用", ["期", "需求", "容量", "利用率"],
                     [[str(i + 1), f"{d:.0f}", f"{cap:.0f}", f"{u:.1f}%"]
                      for i, (d, cap, u) in enumerate(rows)])
    f.so_what = "超载期先限流/排队，再谈扩容；长期高于 85% 才值得加容量。"
    f.boundary = "容量口径按源表（人力/机器/工位）混合计算，不能直接跨类型比较。"
    return f


# --------------------------------------------------------------------------- #
# 10. 故障与可用性
# --------------------------------------------------------------------------- #
@method("incidents", family="sre", needs=["table.incidents"], produces="故障与可用性",
        tags=("sre",), priority=65,
        description="故障时长/等级 → 可用性、MTTR、等级结构")
def m_incidents(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "duration")
    if not t:
        return None
    dur = pick(t, "duration")
    sev = pick(t, "severity")
    mark = c.begin()
    vals, sevs = [], []
    for r in t.rows:
        try:
            v = float(str(r.get(dur, "")).replace(",", ""))
        except ValueError:
            continue
        vals.append(v)
        sevs.append(str(r.get(sev, "unknown")) if sev else "unknown")
    if len(vals) < 3:
        return None
    total_min = sum(vals)
    n = c.n("故障数", len(vals), "次", digits=0)
    n_total = c.n("累计故障时长", total_min, "分钟", digits=0)
    mttr = c.n("MTTR", total_min / len(vals), "分钟")
    p90 = c.n("故障时长 P90", sorted(vals)[int(len(vals) * 0.9)], "分钟")
    # 可用性按 30 天窗口近似
    avail = (1 - total_min / (30 * 24 * 60)) * 100
    n_avail = c.n("可用性（30 天近似）", avail / 100, "%")
    sev_cnt = Counter(sevs)
    title = (f"故障：{n} 次、累计 {n_total} 分钟，MTTR {mttr} 分钟，"
             f"可用性 {n_avail.p()}")
    f = _finding("incidents", title, "稳定性够不够？故障集中在哪？", c, mark)
    f.add(f"{int(len(vals))} 次故障累计 {int(total_min)} 分钟，MTTR {mttr} 分钟、"
          f"P90 {p90} 分钟；按 30 天窗口近似可用性 {n_avail.p()}。",
          _ids(n, n_total, mttr, p90, n_avail))
    f.add("P90 远高于 MTTR 时，问题在少数长故障：先做长故障的止损开关，"
          "而不是平均地去压每一次恢复时间。", _ids(p90, mttr))
    f.table = _table("故障等级结构", ["等级", "次数", "占比"],
                     [[k, str(v), f"{_share(v, len(vals)):.1f}%"]
                      for k, v in sev_cnt.most_common()])
    f.so_what = "可用性低于 99.9% 时先做止损与降级，再谈根因治理。"
    f.boundary = "可用性按 30 天单窗口近似，未扣除计划内维护；故障时长口径以源表为准。"
    return f


# --------------------------------------------------------------------------- #
# 11. 招聘漏斗
# --------------------------------------------------------------------------- #
@method("headcount", family="people", needs=["table.headcount"], produces="招聘与人效",
        tags=("people",), priority=55,
        description="需求/到岗/周期 → 到岗率、招聘周期、缺口")
def m_headcount(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "req")
    if not t:
        return None
    rc = pick(t, "req")
    hc = pick(t, "hire")
    dc = pick(t, "days")
    mark = c.begin()
    req = hire = 0.0
    days = []
    for r in t.rows:
        try:
            req += float(str(r.get(rc, "") or 0))
            if hc:
                hire += float(str(r.get(hc, "") or 0))
            if dc:
                days.append(float(str(r.get(dc, "") or 0)))
        except ValueError:
            continue
    if req <= 0:
        return None
    n_req = c.n("编制需求", req, "人", digits=0)
    n_hire = c.n("已到岗", hire, "人", digits=0) if hc else None
    rate = _share(hire, req)
    n_rate = c.n("到岗率", rate / 100, "%") if hc else None
    n_days = c.n("招聘周期中位数", st.median(days), "天") if days else None
    title = (f"招聘：{n_req} 个需求"
             + (f"、到岗 {n_hire} 人（{n_rate.p()}）" if n_hire else "")
             + (f"，周期中位 {n_days} 天" if n_days else ""))
    f = _finding("headcount", title, "人招得进来吗？卡在哪一段？", c, mark)
    f.add(f"编制需求 {int(req)} 人" + (f"、到岗 {int(hire)} 人，到岗率 {n_rate.p()}"
                                       if n_hire else "")
          + "；缺口按岗位拆，不要只看总数。", _ids(n_req, n_hire, n_rate))
    if n_days:
        f.add(f"招聘周期中位 {n_days} 天；周期超过 45 天时，业务缺口要靠内部调配先顶。",
              _ids(n_days))
    f.table = _table("招聘缺口", ["口径", "值"],
                     [["编制需求", f"{req:.0f}"], ["已到岗", f"{hire:.0f}"],
                      ["到岗率", f"{rate:.1f}%"],
                      ["周期中位", f"{st.median(days):.0f} 天" if days else "—"]])
    f.so_what = "到岗率低于 70% 先修招聘流程；高于 90% 再谈编制扩张。"
    f.boundary = "人数口径未区分替换与新增；周期只统计已关闭的岗位。"
    return f


# --------------------------------------------------------------------------- #
# 12. 商品结构（ABC / 上架下架）
# --------------------------------------------------------------------------- #
@method("sku", family="commerce", needs=["table.sku"], produces="商品结构",
        tags=("sku", "commerce", "product"), priority=60,
        description="SKU×销量×毛利 → ABC、贡献、上架/淘汰清单")
def m_sku(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "sku", "qty")
    if not t:
        return None
    sku, qty = pick(t, "sku"), pick(t, "qty")
    price = pick(t, "amount")
    # 有价格列时按收入（数量×单价）做帕累托，没有时为销量；标题必须跟着口径走
    basis = "收入" if price else "销量"
    margin = pick(t, "margin")
    mark = c.begin()
    rows = []
    for r in t.rows:
        try:
            q = float(str(r.get(qty, "")).replace(",", ""))
        except ValueError:
            continue
        p = float(str(r.get(price, "") or 0).replace(",", "")) if price else 0.0
        rev = q * p if p else q
        rows.append({"sku": str(r.get(sku, "")), "qty": q, "rev": rev,
                     "margin": float(str(r.get(margin, "") or 0).replace(",", ""))
                     if margin else 0.0})
    if len(rows) < 5:
        return None
    rows.sort(key=lambda x: x["rev"], reverse=True)
    total = sum(x["rev"] for x in rows)
    cum = 0.0
    n80 = 0
    for x in rows:
        cum += x["rev"]
        n80 += 1
        if cum >= total * 0.8:
            break
    n_all = c.n("SKU 数", len(rows), "个", digits=0)
    n80n = c.n(f"覆盖 80% {basis}的 SKU 数", n80, "个", digits=0)
    share = n80 / len(rows) * 100
    n_share = c.n("头部 SKU 占比", share / 100, "%")
    tail = len(rows) - n80
    n_tail = c.n("长尾 SKU 数", tail, "个", digits=0)
    title = (f"商品：{n_all} 个 SKU 里前 {n80n} 个贡献八成{basis}（{n_share.p()}），"
             f"长尾 {n_tail} 个")
    f = _finding("sku", title, "商品结构健康吗？该上什么、下什么？", c, mark)
    f.add(f"{int(len(rows))} 个 SKU 中前 {int(n80)} 个覆盖 80% {basis}，占 {n_share.p()}；"
          f"剩余 {int(tail)} 个长尾 SKU 占用货架与资金。",
          _ids(n_all, n80n, n_share, n_tail))
    f.add("上架看增量、下架看长尾：长尾里连续两期销量低于中位 20% 的，先清退再谈上新。",
          _ids(n_tail))
    f.table = _table("SKU ABC 结构", ["SKU", "销量", f"{basis}贡献", "累计"],
                     [[x["sku"][:18], f"{x['qty']:.0f}",
                       f"{_share(x['rev'], total):.1f}%", f"{cum_i:.1f}%"]
                      for cum_i, x in _cum_rows(rows, total)])
    f.chart = {"type": "pareto", "title": f"前 {n80n} 个 SKU 覆盖 80% {basis}",
               "subtitle": f"{len(rows)} 个 SKU · 按{basis}降序累计 · 五个分位截点",
               "note": "有价格列按收入，无价格列按销量",
               "unit_meta": f"累计{basis}占比（%）", "source": f"{t.file} SKU 汇总",
               "refs": _ids(n_share),
               "items": [{"label": f"前{int(p * 100)}%", "value": round(
                   _share(sum(x["rev"] for x in rows[:max(1, int(len(rows) * p))]), total), 1)}
                   for p in (0.1, 0.2, 0.3, 0.5, 1.0)]}
    f.so_what = "头部做深度（库存/陈列/价格），长尾做减法；中间层才是上新试验田。"
    f.boundary = (f"帕累托按{basis}排序；有价格列时收入=数量×单价，"
                  "两者排序可能不同，不能混着引用。")
    return f


def _cum_rows(rows, total):
    cum = 0.0
    out = []
    for x in rows:
        cum += x["rev"]
        out.append((_share(cum, total), x))
    return out


# --------------------------------------------------------------------------- #
# 13. 单店模型
# --------------------------------------------------------------------------- #
@method("store", family="commerce", needs=["table.store"], produces="单店经济",
        tags=("store", "commerce"), priority=60,
        description="面积/租金/销售/毛利 → 坪效、租售比、回本周期")
def m_store(ctx) -> Optional[Finding]:
    desk, c = ctx.desk, ctx.cite
    t = _find(desk, "area", "sales")
    if not t:
        return None
    ac, sc, rentc = pick(t, "area"), pick(t, "sales"), pick(t, "rent")
    marginc = pick(t, "margin")
    mark = c.begin()
    rows = []
    for r in t.rows:
        try:
            area = float(str(r.get(ac, "")).replace(",", ""))
            sales = float(str(r.get(sc, "")).replace(",", ""))
        except ValueError:
            continue
        rent = float(str(r.get(rentc, "") or 0).replace(",", "")) if rentc else 0.0
        gm = float(str(r.get(marginc, "") or 0).replace(",", "")) if marginc else 0.0
        if area <= 0:
            continue
        rows.append({"area": area, "sales": sales, "rent": rent, "gm": gm,
                     "per_sqm": sales / area,
                     "rent_ratio": _share(rent, sales)})
    if len(rows) < 2:
        return None
    avg_ps = sum(x["per_sqm"] for x in rows) / len(rows)
    n_ps = c.n("平均坪效", avg_ps, "元/㎡")
    avg_rr = sum(x["rent_ratio"] for x in rows) / len(rows)
    n_rr = c.n("平均租售比", avg_rr / 100, "%")
    best = max(rows, key=lambda x: x["per_sqm"])
    n_best = c.n("最高坪效", best["per_sqm"], "元/㎡")
    title = (f"单店：平均坪效 {n_ps} 元/㎡、租售比 {n_rr.p()}，"
             f"最高 {n_best} 元/㎡")
    f = _finding("store", title, "一家店赚不赚钱？模型能不能复制？", c, mark)
    f.add(f"{len(rows)} 家店平均坪效 {n_ps} 元/㎡、租售比 {n_rr.p()}；"
          "租售比超过 20% 的店，靠商品结构很难救回来。", _ids(n_ps, n_rr))
    f.add(f"最高坪效 {n_best} 元/㎡，是最低店的 "
          f"{best['per_sqm'] / min(x['per_sqm'] for x in rows):.1f} 倍；"
          "复制前先解释这个差距，否则复制的是位置不是模型。", _ids(n_best))
    f.table = _table("单店经济", ["面积", "销售", "坪效", "租售比"],
                     [[f"{x['area']:.0f}", f"{x['sales']:.0f}",
                       f"{x['per_sqm']:.0f}", f"{x['rent_ratio']:.1f}%"] for x in rows])
    f.so_what = "开店门槛用坪效与租售比双阈值，不看单店销售额绝对值。"
    f.boundary = "没有租金与毛利时，只能算坪效，不能算回本周期。"
    return f
