# -*- coding: utf-8 -*-
"""core/report_thesis —— 报告纲领：同一批证据，回答不同的问题。

为什么要有这一层：报告类型不是「模板」，是**问题的集合**。
`market_research` 问的是「这个盘子在怎么变」，`operations` 问的是
「每个品类到底赚不赚钱」，`remediation` 问的是「负毛利怎么关掉」。
三者用同一批 finding，但取哪几条、以什么顺序讲、结论压在哪一句，完全不同。

本模块只做选择与收口，不做计算：
    resolve(thesis, findings)   按纲领取节，缺的记缺口（不补形容词）
    standfirst(thesis, findings) 首段结论（必须带数字）
    summary(thesis, findings)    分条结论
    opening(thesis, ctx, findings) 开篇节（问题定义 / 经营结论 / 链路结论）
    actions(thesis, ctx, findings) 动作与停止条件（每条都有 stop）
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

THESES: Dict[str, Dict[str, Any]] = {
    "research": {
        "label": "市场调研",
        "doc_name": "市场调研报告",
        "doc_type": "市场调研报告",
        "order": ["structure", "momentum", "trajectory", "contribution",
                  "economics", "transmission", "arbitrage", "risk"],
        "opening": "调研结论",
        "ask": "这个盘子在怎么变，变在哪几个品类上？",
    },
    "operations": {
        "label": "经营诊断",
        "doc_name": "经营报告",
        "doc_type": "经营报告",
        "order": ["structure", "trajectory", "contribution", "economics", "momentum",
                  "transmission", "arbitrage", "breakeven", "risk", "sample"],
        "opening": "经营结论",
        "ask": "每个品类到底赚不赚钱，钱被哪一段吃掉？",
    },
    "remediation": {
        "label": "整改方案",
        "doc_name": "负毛利整改方案",
        "doc_type": "负毛利整改方案",
        "order": ["economics", "breakeven", "transmission", "contribution",
                  "risk"],
        "opening": "问题定义",
        "ask": "负毛利从哪来，怎么分阶段关掉？",
    },
    "chain": {
        "label": "链路优化",
        "doc_name": "链路优化报告",
        "doc_type": "链路优化报告",
        "order": ["transmission", "economics", "arbitrage", "contribution", "risk"],
        "opening": "链路结论",
        "ask": "链路利润被哪一段吃掉，哪里可以重构？",
    },
    "forecast": {
        "label": "趋势预测",
        "doc_name": "趋势预测报告",
        "doc_type": "趋势预测报告",
        "order": ["forecast", "trajectory", "momentum", "contribution",
                  "sample", "risk"],
        "opening": "预测结论",
        "ask": "按现在的斜率走下去，下个季度会在哪？",
    },
    # ---------------- 跨域纲领（v5）：同一套方法库，换问题 ---------------- #
    "growth": {
        "label": "增长诊断",
        "doc_name": "增长诊断报告",
        "doc_type": "增长诊断报告",
        "order": ["funnel", "retention", "rfm", "roi", "payment_mix", "reviews", "risk"],
        "opening": "增长结论",
        "ask": "增长卡在获客、转化还是留存？",
    },
    "product": {
        "label": "产品决策",
        "doc_name": "产品决策报告",
        "doc_type": "产品决策报告",
        "order": ["priority", "reviews", "retention", "funnel", "risk"],
        "opening": "产品结论",
        "ask": "先做哪一条需求，依据是什么？",
    },
    "support": {
        "label": "客户体验",
        "doc_name": "客户体验报告",
        "doc_type": "客户体验报告",
        "order": ["sla", "reviews", "retention", "capacity", "risk"],
        "opening": "体验结论",
        "ask": "体验的短板在履约、商品还是响应？",
    },
    "people": {
        "label": "组织与人效",
        "doc_name": "组织人效报告",
        "doc_type": "组织人效报告",
        "order": ["headcount", "capacity", "priority", "risk"],
        "opening": "组织结论",
        "ask": "人是招不进来，还是进来了不够用？",
    },
    "sre": {
        "label": "稳定性复盘",
        "doc_name": "稳定性复盘报告",
        "doc_type": "稳定性复盘报告",
        "order": ["incidents", "capacity", "risk"],
        "opening": "稳定性结论",
        "ask": "稳定性够不够，故障集中在哪？",
    },
    "marketing": {
        "label": "营销效率",
        "doc_name": "营销效率报告",
        "doc_type": "营销效率报告",
        "order": ["roi", "funnel", "reviews", "rfm", "risk"],
        "opening": "营销结论",
        "ask": "钱花在哪个环节最有效？",
    },
    "sku": {
        "label": "商品结构",
        "doc_name": "商品结构报告",
        "doc_type": "商品结构报告",
        "order": ["sku", "store", "forecast", "risk"],
        "opening": "商品结论",
        "ask": "该上什么、该下什么？",
    },
    "store": {
        "label": "单店模型",
        "doc_name": "单店模型报告",
        "doc_type": "单店模型报告",
        "order": ["store", "sku", "economics", "risk"],
        "opening": "单店结论",
        "ask": "这家店赚不赚钱，能不能复制？",
    },
    "market_entry": {
        "label": "新业务研究",
        "doc_name": "新业务可行性研究报告",
        "doc_type": "新业务可行性研究报告",
        "order": ["sizing_multi", "growth", "concentration", "unit_econ",
                  "entry_gate"],
        "opening": "研究结论",
        "ask": "这个新业务能不能做、从哪进、什么条件下停？",
    },
    # v7：区域消费市场深度调研（带来源事实表驱动，不是价格线的换序）
    "market": {
        "label": "市场调研",
        "doc_name": "市场调研报告",
        "doc_type": "市场调研报告",
        "order": ["size", "demand", "trend", "mix", "volume", "channel",
                  "region", "supply", "policy", "consistency", "coverage"],
        "opening": "调研结论",
        "ask": "这个市场有多大、结构怎么变、钱在哪、该做哪一段？",
    },
    # v8：奶酪零食（特色乳制品零食）五类报告 —— 与家居百货/肉禽蛋不共用一套问题链
    "cheese_market": {
        "label": "市场调研",
        "doc_name": "市场调研报告",
        "doc_type": "市场调研报告",
        "order": ["cheese_size", "cheese_growth", "cheese_structure", "cheese_channel",
                  "cheese_supply", "cheese_region", "cheese_policy", "cheese_coverage"],
        "opening": "调研结论",
        "ask": "这个奶酪零食市场有多大、结构怎么变、钱在哪个渠道、该做哪一段？",
    },
    "cheese_ops": {
        "label": "经营测算",
        "doc_name": "经营测算报告",
        "doc_type": "经营测算报告",
        "order": ["cheese_unit_econ", "cheese_structure", "cheese_chain", "cheese_coverage"],
        "opening": "经营结论",
        "ask": "每个品类赚不赚钱、一公斤奶酪净利多少、原料涨价会不会打穿？",
    },
    "cheese_chain": {
        "label": "链路优化",
        "doc_name": "链路优化报告",
        "doc_type": "链路优化报告",
        "order": ["cheese_chain", "cheese_unit_econ", "cheese_region", "cheese_coverage"],
        "opening": "链路结论",
        "ask": "奶源到零售的利润被哪一段吃掉、哪里可以重构？",
    },
    "cheese_content": {
        "label": "营销与内容增长",
        "doc_name": "营销与内容增长方案",
        "doc_type": "营销与内容增长方案",
        "order": ["cheese_channel", "cheese_content", "cheese_unit_econ", "cheese_coverage"],
        "opening": "增长结论",
        "ask": "内容与礼盒怎么把散装奶酪做成高溢价的零食？",
    },
    "cheese_fix": {
        "label": "成本与止损整改",
        "doc_name": "成本与止损整改方案",
        "doc_type": "成本与止损整改方案",
        "order": ["cheese_unit_econ", "cheese_chain", "cheese_policy", "cheese_coverage"],
        "opening": "问题定义",
        "ask": "单位经济哪里最薄、原料涨价与渠道扣点哪个先打穿、怎么分阶段止血？",
    },
    # v8：数据分析报告 —— 价格序列与价差为主证据，规模/结构/渠道为对照
    "cheese_data": {
        "label": "市场调研与数据分析",
        "doc_name": "市场调研与数据分析报告",
        "doc_type": "市场调研与数据分析报告",
        "order": ["cheese_size", "cheese_growth", "cheese_structure", "cheese_price",
                  "cheese_region", "cheese_channel", "cheese_coverage"],
        "opening": "分析结论",
        "ask": "四个品类的量与价怎么变、涨在哪个环节、数据支持哪些结论？",
    },
    # v9：通用专业分析 —— 不绑定业务，按五模块（问题/数据/推导/风险/动作）装配
    "analysis": {
        "label": "专业分析",
        "doc_name": "专业分析报告",
        "doc_type": "专业分析报告",
        "order": [
            "size", "growth", "structure", "demand", "volume", "channel", "region",
            "supply", "policy", "consistency", "coverage",
            "momentum", "trajectory", "contribution", "economics", "transmission",
            "arbitrage", "breakeven", "forecast", "risk", "sample",
            "concentration", "unit_econ", "entry_gate",
            "cheese_size", "cheese_growth", "cheese_structure", "cheese_price",
            "cheese_channel", "cheese_supply", "cheese_region", "cheese_policy",
            "cheese_unit_econ", "cheese_chain", "cheese_content", "cheese_coverage",
            "funnel", "retention", "rfm", "roi", "payment_mix", "reviews",
            "priority", "sla", "capacity", "headcount", "incidents", "sku", "store",
        ],
        "opening": "分析结论",
        "ask": "这份分析回答什么、数据支持哪些判断、哪些不能下、下一步做什么？",
    },
}

GENERIC_THESES = ("growth", "product", "support", "people", "sre", "marketing",
                  "sku", "store", "market_entry", "cheese_market", "cheese_ops",
                  "cheese_chain", "cheese_content", "cheese_fix", "cheese_data",
                  "analysis")

# P5：22 个业务纲领收敛为 1 个 analysis + lens。
# 旧名字保留为“兼容标签”，只用于把老调用映射到 lens，不再有自己的章节/帧。
LEGACY_LENS: Dict[str, Optional[str]] = {
    "research": "market", "operations": "ops", "remediation": "fix",
    "chain": "chain", "forecast": "ops", "growth": "ops",
    "product": "market", "support": "ops", "people": "ops", "sre": "ops",
    "marketing": "market", "sku": "market", "store": "ops",
    "market_entry": "market", "market": "market",
    "cheese_market": "market", "cheese_ops": "ops", "cheese_chain": "chain",
    "cheese_content": "market", "cheese_fix": "fix", "cheese_data": "market",
    "analysis": None,
}

# P5：唯一纲领。旧业务纲领的 order/opening/actions 不再作为独立报告类型。
_ANALYSIS_SPEC = THESES["analysis"]
THESES = {"analysis": _ANALYSIS_SPEC}

# 每类纲领的「主证据」：主证据一个都没命中，就不许出这类报告（避免用次要节硬凑）
PRIMARY: Dict[str, List[str]] = {
    "research": ["structure", "economics"],
    "operations": ["economics"],
    "remediation": ["economics"],
    "chain": ["transmission"],
    "forecast": ["forecast"],
    "growth": ["funnel", "retention"],
    "product": ["priority", "reviews"],
    "support": ["sla", "reviews"],
    "people": ["headcount", "capacity"],
    "sre": ["incidents", "capacity"],
    "marketing": ["roi", "funnel"],
    "sku": ["sku"],
    "store": ["store"],
    "market_entry": ["sizing_multi", "unit_econ"],
    "market": ["size", "mix"],
    "cheese_market": ["cheese_size", "cheese_structure"],
    "cheese_ops": ["cheese_unit_econ"],
    "cheese_chain": ["cheese_chain"],
    "cheese_content": ["cheese_channel", "cheese_content"],
    "cheese_fix": ["cheese_unit_econ"],
    "cheese_data": ["cheese_price", "cheese_size"],
    "analysis": [],   # 通用分析不设主证据，有任何可复算判断即可出报告
}
DEFAULT_THESIS = "research"


def infer(intent: str, profile: Dict[str, Any]) -> str:
    """意图 → 纲领。显式关键词优先，其次看数据能力，最后落到调研。"""
    s = str(intent or "")
    # v9：显式要「通用/标准化/专业分析」→ 走五模块框架（不为业务定制）
    if any(w in s for w in ("通用分析", "标准化分析", "专业分析", "分析框架",
                            "全维度分析", "五模块", "方法论")):
        return "analysis"
    # v8：奶酪零食关键词 → 按意图路由到奶酪五类纲领（不与家居百货/肉禽蛋共用）
    if any(w in s for w in ("奶酪", "奶豆腐", "奶皮子", "奶条", "奶食", "乳制品零食", "特色乳制品")):
        if any(w in s for w in ("整改", "负毛利", "止损", "降本", "成本")):
            return "cheese_fix"
        if any(w in s for w in ("链路", "供应链", "断点", "传导", "重构")):
            return "cheese_chain"
        if any(w in s for w in ("营销", "内容", "种草", "礼盒", "增长")):
            return "cheese_content"
        if any(w in s for w in ("经营", "毛利", "单位经济", "测算", "采购", "定价")):
            return "cheese_ops"
        if any(w in s for w in ("数据分析", "价格分析", "采价", "价差", "加价", "同比")):
            return "cheese_data"
        return "cheese_market"
    # v7：有带来源的事实表 + 调研意图 → 走深度市场调研（不是价格线的换序）
    if profile.get("facts", 0) >= 20 and any(
            w in s for w in ("市场调研", "市场研究", "消费市场", "行业研究", "区域市场")):
        return "market"
    rules = (
        ("remediation", ("整改", "负毛利", "亏损", "止损", "降本")),
        ("market_entry", ("新业务", "可行性", "能不能做", "进入", "立项", "赛道")),
        ("support", ("客服", "工单", "满意度", "体验", "履约", "voc", "VOC", "续约")),
        ("sre", ("稳定性", "可用性", "故障", "事故", "slo", "SLO", "复盘")),
        ("people", ("招聘", "人效", "编制", "组织", "人力")),
        ("product", ("产品", "需求", "prd", "PRD", "优先级", "rice", "RICE")),
        ("growth", ("增长", "漏斗", "留存", "复购", "获客", "转化", "投放")),
        ("marketing", ("营销", "内容", "渠道", "投放 roi", "ROI")),
        ("sku", ("商品结构", "sku", "SKU", "上架", "淘汰", "动销")),
        ("store", ("单店", "坪效", "开店", "门店模型")),
        ("operations", ("经营", "毛利", "采购", "定价", "单位经济", "配额")),
        ("chain", ("链路", "供应链", "断点", "传导", "重构")),
        ("forecast", ("预测", "趋势", "下季度", "情景")),
        ("research", ("调研", "市场", "行情", "结构")),
    )
    for key, words in rules:
        if any(w in s for w in words):
            return key
    # v9：没有命中任何业务纲领、但确实是在做「分析/评估/诊断」→ 走通用五模块框架
    if any(w in s for w in ("分析", "评估", "诊断", "复盘", "洞察", "研究")):
        return "analysis"
    # 没有关键词时按数据能力：有价格批发就做经营，有订单/评价就做增长/体验
    if profile.get("channels", {}).get("wholesale"):
        return "operations"
    kinds = profile.get("kinds", {}) or {}
    if kinds.get("long_panel") and profile.get("channels", {}).get("retail"):
        return "research"
    return "growth" if profile.get("tables", 0) else "research"


def resolve(thesis: str, findings: Dict[str, Any]) -> Tuple[List[Any], List[str]]:
    spec = THESES.get(thesis) or THESES[DEFAULT_THESIS]
    picked, missing = [], []
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
    """v7：claim 驱动的 finding 把量化标签放在 meta['claim'].tags。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    return (getattr(cl, "tags", None) or {}) if cl is not None else {}


def _refs(f) -> List[str]:
    """取本节可用的证据 id：claim 的 refs 优先（已含本节全部登记数字）。"""
    cl = (getattr(f, "meta", None) or {}).get("claim")
    if cl is not None and getattr(cl, "refs", None):
        return list(cl.refs)
    return list(getattr(f, "refs", None) or [])


def standfirst(thesis: str, findings: Dict[str, Any]) -> str:
    if thesis == "market":
        sz, tr, mx = findings.get("size"), findings.get("trend"), findings.get("mix")
        parts = []
        if sz:
            parts.append(sz.title.split("：", 1)[-1])
        if tr:
            parts.append(tr.title.split("：", 1)[-1])
        if mx:
            parts.append(mx.title.split("：", 1)[-1])
        body = "；".join(parts)
        return (body + "。所以这份调研的落点不是「总量还增不增」，"
                "而是「哪一段还在增、按什么口径做预算、什么条件下停」。")
    eco = findings.get("economics")
    tra = findings.get("transmission")
    mom = findings.get("momentum")
    arb = findings.get("arbitrage")
    be = findings.get("breakeven")
    st = findings.get("structure")
    if thesis in GENERIC_THESES:
        picked, _ = resolve(thesis, findings)
        if picked:
            head = picked[0].title
            tail = (f"；{picked[1].title.split('：', 1)[-1]}" if len(picked) > 1 else "")
            return f"{head}{tail}。"
        return "本轮没有命中可复算的判断，报告只保留缺口。"
    if thesis == "remediation" and eco and be:
        neg = [r for r in (_num(eco, "rows") or []) if r["v"] < 0]
        hard = min((_num(be, "rows") or [{"v": 0}]), key=lambda r: r["v"])
        return (f"{len(neg)} 个品类扣掉损耗与冷链后是负毛利，最轻的只要提价 "
                f"{hard.get('up').p() if hard.get('up') else '—'} 就能转正；"
                f"病因不是「卖贵了」，是加价率撑不住成本结构。")
    if thesis == "operations" and eco:
        rows = _num(eco, "rows") or []
        neg = [r for r in rows if r["v"] < 0]
        top = rows[0] if rows else None
        if top and top["margin"].value >= 0:
            return (f"{len(rows)} 个可测品类里 {len(neg)} 个净毛利为负、"
                    f"{len(rows) - len(neg)} 个为正；"
                    f"{top['cat']} 净利率 {top['margin'].p()} 最高，"
                    "其余品类要按引流品、结构品分角色考核。")
        hard = min(rows, key=lambda r: r["margin"].value) if rows else None
        return (f"{len(rows)} 个可测品类里 {len(neg)} 个净毛利为负；"
                f"{hard['cat']} 净利率 {hard['margin'].p()} 最深，"
                "病灶是加价率撑不住损耗与冷链，不是卖贵了。") if hard else eco.title
    if thesis == "chain" and tra:
        return (f"链路的问题不是「贵」，是错配：{tra.title.split('：', 1)[-1]}。"
                "加价集中在零售端，能压的只有上游与物流那一段。")
    if thesis == "forecast" and findings.get("forecast"):
        fc = findings["forecast"]
        return (f"{fc.title.split('：', 1)[-1]}；但样本只有个位数期次，"
                "预测只给方向与区间，不给点值。")
    # research / 默认：用结构 + 单位经济两句话收口
    if st and eco:
        rows = _num(eco, "rows") or []
        neg = [r for r in rows if r["v"] < 0]
        if rows:
            return (f"{len(neg)} 个品类扣完成本为负；"
                    f"{st.title.split('：', 1)[-1]}。结论不是「涨还是跌」，"
                    "而是加价率撑不住损耗与冷链。")
    parts = []
    if st:
        parts.append(st.title.split("：", 1)[-1])
    if eco:
        rows = _num(eco, "rows") or []
        neg = [r for r in rows if r["v"] < 0]
        if rows:
            parts.append(f"扣掉损耗与冷链后 {len(neg)} 个品类为负，"
                         f"{rows[0]['cat']} 净利率 {rows[0]['margin'].p()}")
    if arb:
        parts.append(f"跨市配额只对 {arb.title.split('：', 1)[-1].split('，')[0]} 成立")
    return "；".join(parts) + "。" if parts else (mom.title if mom else "本轮未产出可复算结论。")


def summary(thesis: str, findings: Dict[str, Any]) -> List[str]:
    """分条结论：直接取每条 finding 的标题（标题即结论、带数字）。"""
    picked, _ = resolve(thesis, findings)
    out = [f.title for f in picked[:4]]
    if len(out) < 2:
        # 主证据只命中 1 条时，补一条不依赖新数字的判据句，避免开头只有一句结论
        out.append("经营上只看三件事：品类结构决定做不做，单位经济决定赚不赚，"
                   "链路分段决定钱被谁吃掉。")
    if not out:
        out = ["本轮没有命中任何可复算的结论，报告只保留缺口。"]
    return out


def opening(thesis: str, ctx, findings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """开篇节：把「这一份报告到底在回答什么」写成带数字的判断。"""
    spec = THESES.get(thesis) or THESES[DEFAULT_THESIS]
    c = ctx.cite
    eco = findings.get("economics")
    tra = findings.get("transmission")
    mom = findings.get("momentum")
    be = findings.get("breakeven")
    arb = findings.get("arbitrage")
    st = findings.get("structure")
    rows = _num(eco, "rows") or [] if eco else []
    neg = [r for r in rows if r["v"] < 0]
    top = rows[0] if rows else None

    sec: Dict[str, Any] = {"title": "", "question": "", "reading": [],
                           "refs": [], "assumptions": []}
    if thesis == "market":
        sz, tr, mx = findings.get("size"), findings.get("trend"), findings.get("mix")
        if not sz:
            return None
        st = _tags(sz)
        paths = st.get("paths") or []
        lo = min((p["lo"] for p in paths), default=0.0)
        hi = max((p["hi"] for p in paths), default=0.0)
        mid_v = (lo + hi) / 2
        retail = None
        try:
            retail = ctx.desk.ft.one("社会消费品零售总额", region="内蒙古",
                                     prefer_period="2025", exclude=("同比", "增速"))
        except Exception:  # noqa: BLE001
            retail = None
        n_mid = c.n("规模中位（开篇）", mid_v, "亿元", digits=1)
        n_lo = c.n("规模下限（开篇）", lo, "亿元", digits=1)
        n_hi = c.n("规模上限（开篇）", hi, "亿元", digits=1)
        sec["title"] = (f"调研结论：规模 {lo:.0f}—{hi:.0f} 亿元、增速下台阶、结构在换手，"
                        "三件事同时成立")
        sec["question"] = (THESES.get("market") or {}).get("ask", "")
        if retail:
            n_retail = c.n("内蒙古社零（开篇）", retail.value, "亿元", "2025", retail.id, digits=0)
            share = mid_v / retail.value
            n_share = c.n("规模占社零比重", share, "%")
            sec["reading"].append({
                "text": f"规模中位 {n_mid} 亿元，只相当于 2025 年社零 {n_retail} 亿元的 "
                        f"{n_share.p()}：家居百货是社零里的一个小口径，不是大盘本身。"
                        "按它做预算可以，按它判断消费强弱不行。",
                "refs": [n_mid.id, n_retail.id, n_share.id]})
        if tr:
            tt = _tags(tr)
            n_lg = c.n("最新增速（开篇）", (tt.get("last_growth") or 0) / 100, "%", digits=1)
            n_pg = c.n("上年增速（开篇）", (tt.get("prev_growth") or 0) / 100, "%", digits=1)
            sec["reading"].append({
                "text": f"增速从 {n_pg.p()} 退到 {n_lg.p()}，是下台阶不是波动；"
                        "同时结构里的最大背离超过 20 个百分点——总量在失速、结构在换手，"
                        "这两个方向同时成立，不能只看其中一个。",
                "refs": [n_lg.id, n_pg.id] + (list(mx.refs[:3]) if mx else [])})
        sec["reading"].append({
            "text": "所以先做存量替换与刚需品类，不追增量与大件；预算按收敛区间做，"
                    "不按天花板做；每季度用社零累计增速与结构背离复核一次，"
                    "任一指标连续两季反向，本报告的判断作废。",
            "refs": [n_lo.id, n_hi.id]})
        sec["refs"] = [n_mid.id, n_lo.id, n_hi.id] + (list(tr.refs[:4]) if tr else [])
        sec["boundary"] = ("开篇三个数分别来自规模多路径、社零序列与分品类对比；"
                           "它们不是同一口径，不能相互替代。")
        if not sec["reading"]:
            return None
        return sec
    if thesis == "remediation" and eco and be:
        brows = _num(be, "rows") or []
        worst = min(neg, key=lambda r: r["nv"].value) if neg else None
        easy = min(brows, key=lambda r: r["v"]) if brows else None
        n_neg = c.n("负毛利品类数", len(neg), "个", digits=0)
        sec["title"] = (f"问题定义：{n_neg} 个品类净毛利为负，"
                        f"{worst['cat'] if worst else '—'} "
                        f"{worst['nv'].value if worst else 0:+.2f} 元/斤最深")
        sec["question"] = "负毛利有几个、病因是否相同、先治哪一个？"
        if neg:
            ordered = sorted(neg, key=lambda r: r["nv"].value)
            names = "、".join(f"{r['cat']} {r['nv'].value:+.2f}" for r in ordered)
            deep = [r for r in neg if r["v"] <= -0.5]
            sec["reading"].append({
                "text": f"{len(neg)} 个负毛利按深度排序是 {names} 元/斤；"
                        + (f"其中 {len(deep)} 个是深亏（净利率低于 -0.5%），"
                           "其余只是擦线，整改力度不能一样。" if deep else
                           "它们都在盈亏平衡线附近，先控损耗就能拉回。"),
                "refs": [r["nv"].id for r in neg] + [n_neg.id]})
        if brows:
            easy = min(brows, key=lambda r: r["v"])
            hard = max(brows, key=lambda r: r["v"])
            sec["reading"].append({
                "text": f"先治谁看「转正难度」：{easy['cat']} 只要提 {easy['up'].p()} 就保本，"
                        f"而 {hard['cat']} 要提 {hard['up'].p()}；"
                        "难度差一个量级，不能一起排期。",
                "refs": [easy["up"].id, hard["up"].id]})
        if neg:
            b = neg[0]
            sec["reading"].append({
                "text": f"病因在成本结构：{b['cat']} 加价率 {b['markup'].p()}，"
                        f"扣 {b['loss'].p()} 损耗与 {b['cold']} 元/斤冷链后为负——"
                        "不是卖贵了，是加价撑不住损耗。",
                "refs": [b["markup"].id, b["loss"].id, b["cold"].id, b["nv"].id]})
        sec["refs"] = [x for r in rows[:3] for x in
                       [r["markup"].id, r["nv"].id, r["margin"].id]]
        sec["refs"] += [r["up"].id for r in brows[:3]] + [n_neg.id]
    elif thesis == "operations" and eco and top:
        sec["title"] = (f"经营结论：{len(rows)} 个品类里只有 {len(rows) - len(neg)} 个赚钱，"
                        f"{top['cat']} 净利率 {top['margin'].p()}")
        sec["question"] = "哪些品类是利润品、哪些只能做引流品？"
        good = [r for r in rows if r["v"] >= 0]
        if good:
            g = good[0]
            sec["reading"].append({
                "text": f"{g['cat']} 加价 {g['markup'].p()}、净毛利 "
                        f"{g['nv'].value:+.2f} 元/斤，是这批品类里唯一同时具备"
                        "高加价与低损耗的利润品。",
                "refs": [g["markup"].id, g["nv"].id, g["margin"].id]})
        if neg:
            b = min(neg, key=lambda r: r["v"])
            sec["reading"].append({
                "text": f"{b['cat']} 加价只有 {b['markup'].p()}，扣完成本 "
                        f"{b['nv'].value:+.2f} 元/斤；继续按销量考核它，只会越卖越亏。",
                "refs": [b["markup"].id, b["nv"].id]})
        if not good:
            sec["reading"].append({
                "text": f"这一轮没有一个品类净毛利为正，病灶不是单点："
                        f"{len(neg)} 个品类同时被损耗与冷链吃掉加价，"
                        "先修成本结构再谈品类组合。",
                "refs": [r["nv"].id for r in neg[:3]]})
        sec["refs"] = list({x for r in rows[:3] for x in
                            [r["markup"].id, r["nv"].id, r["margin"].id]})
    elif thesis == "chain" and tra:
        trows = _num(tra, "rows") or []
        inv = [r for r in trows if r["up"].value < 0]
        n_inv = c.n("产地倒挂品类数", len(inv), "个", digits=0)
        if trows:
            main = max(trows, key=lambda r: abs(r["dn"].value))
            share = main["dn"].value / main["r"].value * 100 if main["r"].value else 0
            n_share = c.n("批发到零售占零售价比重", share / 100, "%")
            sec["title"] = (f"链路结论：{n_inv} 个可比品类产地倒挂，"
                            f"利润集中在零售端（{main['cat']} 零售段占 {n_share.p()}）")
            sec["question"] = "这条链路的利润分布合理吗，该拆哪一段？"
            sec["reading"].append({
                "text": f"{main['cat']} 零售价 {main['r']} 元/斤，其中批发到零售这一段 "
                        f"{main['dn']} 元、占 {n_share.p()}；产地到批发 "
                        f"{main['up'].value:+.2f} 元，上游没有加价。",
                "refs": [main["r"].id, main["dn"].id, n_share.id, main["up"].id]})
            others = [r for r in trows if r["cat"] != main["cat"]]
            if others:
                b = others[0]
                if b["up"].value < 0:
                    sec["reading"].append({
                        "text": f"{b['cat']} 反过来：产地 {b['o']} 高于销地批发 {b['w']}，"
                                f"倒挂 {abs(b['up'].value):.2f} 元/斤。同一条链路里"
                                "两个品类的瓶颈方向相反，重构规则不能共用一套。",
                        "refs": [b["o"].id, b["w"].id, b["up"].id]})
                else:
                    sec["reading"].append({
                        "text": f"{b['cat']} 是另一条链：产地到批发 {b['up'].value:+.2f} 元，"
                                f"批发到零售只有 {b['dn'].value:+.2f} 元，"
                                "瓶颈在环节数量而不在零售加价——它要压的是批发那一层。",
                        "refs": [b["up"].id, b["dn"].id]})
            sec["reading"].append({
                "text": "所以链路优化的落点不是「整体降本」，"
                        "而是按品类拆段：零售段厚的谈环节，上游倒挂的换采购方式。",
                "refs": [n_inv.id]})
            sec["refs"] = list(tra.refs) + [n_inv.id, n_share.id]
    elif thesis == "forecast" and findings.get("forecast"):
        fc = findings["forecast"]
        sec["title"] = f"预测结论：{fc.title.split('：', 1)[-1]}"
        sec["question"] = "按现有斜率，下个季度会在什么位置？"
        sec["reading"] = [{"text": r["text"], "refs": r["refs"]}
                          for r in (fc.reading or [])[:3]]
        sec["refs"] = list(fc.refs)
        sec["assumptions"] = list(getattr(fc, "assumptions", []) or [])
        sec["boundary"] = "预测只给方向与区间：期数不足 12，不做季节调整，也不给点值。"
    elif thesis == "market_entry":
        sz = findings.get("sizing_multi")
        eco = findings.get("unit_econ")
        gate = findings.get("entry_gate")
        if not (sz and eco):
            return None
        lo, hi = (sz.meta or {}).get("lo", 0), (sz.meta or {}).get("hi", 0)
        em = eco.meta or {}
        n_lo = c.n("可服务市场下限", lo, "亿元")
        n_hi = c.n("可服务市场上限", hi, "亿元")
        n_net = c.n("单位净利", em.get("net", 0), "元/公斤")
        n_mg = c.n("净利率", em.get("margin", 0), "%")
        n_be = c.n("保本价", em.get("breakeven", 0), "元/公斤")
        sec["title"] = (f"研究结论：市场 {n_lo}—{n_hi} 亿元、单公斤净利 {n_net} 元"
                        f"（{n_mg.p()}），能做但只做 B 端")
        sec["question"] = spec["ask"]
        sec["reading"] = [
            {"text": f"规模取品牌法与人口法的收敛区间 {n_lo}—{n_hi} 亿元，"
                     "产值法含工业口径，只能当天花板，不能当预算。",
             "refs": [n_lo.id, n_hi.id]},
            {"text": f"单位经济：出厂价折算后净利 {n_net} 元/公斤、净利率 {n_mg.p()}，"
                     f"保本价 {n_be} 元/公斤；低于保本价不做。",
             "refs": [n_net.id, n_mg.id, n_be.id]},
            {"text": "C 端即食已被双寡头占据（CR2 过半），新进入者先做 B 端餐饮工业与礼盒，"
                     "用代工验证订单，不先建厂。",
             "refs": [n_lo.id]},
        ]
        sec["refs"] = [n_lo.id, n_hi.id, n_net.id, n_mg.id, n_be.id] + _refs(sz)
        sec["boundary"] = "结论依赖两条 C 级假设（奶酪零食占比、锡盟份额）与单位经济假设，执行前需用一手数据校准。"
    elif thesis in GENERIC_THESES:
        picked, _ = resolve(thesis, findings)
        if not picked:
            return None
        first = picked[0]
        sec["title"] = f"{spec['label']}结论：{first.title.split('：', 1)[-1]}"
        sec["question"] = spec["ask"]
        anchor = first.refs[0] if first.refs else ""
        n_hit = c.n("命中判断数", len(picked), "条", digits=0)
        anchor = first.refs[0] if first.refs else n_hit.id
        sec["reading"] = [
            {"text": f"这份报告只回答一个问题：{spec['ask']}", "refs": [anchor]},
            {"text": f"本轮命中 {n_hit} 条可复算判断，证据最强的是「"
                     f"{first.title.split('：')[0]}」；缺数据的判断列在末节缺口，不用估算补。",
             "refs": [n_hit.id, anchor]},
        ]
        sec["refs"] = [x for f in picked[:2] for x in f.refs] + [n_hit.id]
        sec["assumptions"] = [a for f in picked[:2] for a in (getattr(f, "assumptions", []) or [])]
    else:
        if not st or not (st.meta or {}).get("rows"):
            return None
        srows = st.meta["rows"]
        down = [r for r in srows if r["v"] < 0]
        n_all = c.n("可测品类数", len(srows), "个", digits=0)
        n_neg = c.n("负毛利品类数", len(neg), "个", digits=0)
        sec["title"] = (f"调研结论：{n_all} 个品类里 {n_neg} 个扣完成本为负，"
                        "涨跌只是表象")
        sec["question"] = spec["ask"]
        sec["reading"].append({
            "text": f"{len(down)} 个品类区间在跌；真正决定去留的是成本端——"
                    + (f"{n_neg} 个品类扣损耗冷链后为负。" if neg else "所有品类仍为正。"),
            "refs": [n_all.id, n_neg.id] + [r["nv"].id for r in neg[:2]]})
        if arb:
            arows = _num(arb, "rows") or []
            good = [r for r in arows if r["v"] > 0]
            if good:
                sec["reading"].append({
                    "text": f"跨市场仍有空间：{good[0]['cat']} 两地价差扣完成本还剩 "
                            f"{good[0]['nv'].value:+.2f} 元/斤，「在哪买」比「什么时候买」更值钱。",
                    "refs": [good[0]["nv"].id]})
        sec["reading"].append({
            "text": "所以这份调研的落点不是「哪个品类涨」，"
                    "而是「哪个品类值得继续做、哪个该换源、哪个只做引流」。",
            "refs": [n_all.id]})
        sec["refs"] = list({*st.refs, n_all.id, n_neg.id})
    if not sec["reading"]:
        return None
    if not sec.get("boundary"):
        sec["boundary"] = "开篇结论来自后文各节的实算，不是独立估计。"
    return sec


def actions(thesis: str, findings: Dict[str, Any]) -> List[Dict[str, str]]:
    """动作与停止条件：由数据触发，每条都带停止条件。"""
    out: List[Dict[str, str]] = []
    if thesis == "market":
        sz, mx = findings.get("size"), findings.get("mix")
        ch, rg = findings.get("channel"), findings.get("region")
        if sz:
            paths = _tags(sz).get("paths") or []
            lo = min((p["lo"] for p in paths), default=0.0)
            hi = max((p["hi"] for p in paths), default=0.0)
            out.append({
                "do": f"年度预算按 {lo:.1f}—{hi:.1f} 亿元做，不按 {hi:.1f} 亿元做",
                "condition": "确认占比假设与三条路径的收敛区间",
                "stop": "规模重算偏离 20% 以上，或社零累计增速连续两季为负",
                "refs": _refs(sz)})
        if mx:
            items = _tags(mx).get("items") or []
            if items:
                worst = min(items, key=lambda x: x["gap"])
                out.append({
                    "do": f"对{worst['cat']}单独立项：本地 {worst['nm']:+.1f}%、"
                          f"全国 {worst['cn']:+.1f}%，差 {worst['gap']:+.1f}pp",
                    "condition": "拿到本地渠道或需求的一手数据，能解释背离",
                    "stop": "下期回到全国方向，立即撤项，不追加投入",
                    "refs": _refs(mx)})
        if ch:
            ct = _tags(ch)
            out.append({
                "do": f"陈列与库存从{ct.get('lose', '百货')}迁到{ct.get('win', '超市')}与社区店，"
                      "先做 3 个月店中店验证",
                "condition": f"目标业态增速高于{ct.get('lose', '百货')} 5pp 以上",
                "stop": "目标业态家居品类增速转负，停止迁移并回撤",
                "refs": _refs(ch)})
        if rg:
            out.append({
                "do": "县域只做 1 个旗县样板，用现有商贸中心嵌入，不自建网络",
                "condition": "样板店 6 个月达到坪效与周转线",
                "stop": "6 个月未达线，停止县域扩张",
                "refs": _refs(rg)})
        cov = findings.get("coverage")
        if cov:
            out.append({
                "do": "先补 5 个缺失盟市社零与 2026 分品类，再定区域配额",
                "condition": "缺失项补齐并复跑通过",
                "stop": "补数两周仍未齐，暂停区域扩张",
                "refs": _refs(cov)})
        return out[:4]
    if thesis == "market_entry":
        for key in ("entry_gate", "unit_econ"):
            f = findings.get(key)
            for a in (getattr(f, "actions", None) or []):
                out.append(a)
        if out:
            return out[:4]
    if thesis.startswith("cheese_"):
        # 奶酪零食：动作由「单位经济 + 链路 + 内容」三条证据链触发，每条带停止条件
        eco = findings.get("cheese_unit_econ")
        chn = findings.get("cheese_chain")
        cnt = findings.get("cheese_content")
        sz = findings.get("cheese_size")
        if eco:
            em = (getattr(eco, "meta", None) or {}).get("claim") or {}
            be = (em.tags or {}).get("breakeven", 48.0)
            net = (em.tags or {}).get("net", 6.86)
            out.append({
                "do": "先锁奶源或签价格联动条款，再启动量产；用代工/贴牌验证 B 端订单，不先建厂",
                "condition": f"到场奶价不高于 3.0 元/公斤且能锁定 6 个月，出厂价 ≥ {be:.1f} 元/公斤",
                "stop": f"原料涨 20% 后净利跌破 {net*0.3:.2f} 元/公斤，或连续两月低于保本价，暂停扩量",
                "refs": _refs(eco)})
        if chn:
            out.append({
                "do": "奶豆腐主链压出厂到零售的渠道段（直供/店中店），奶条保品牌与内容不做价格战",
                "condition": "渠道扣点压到 20% 以内，零售加价率降 5 个百分点",
                "stop": "压渠道导致动销下滑或铺货成本反超直供收益，回撤到批发分销",
                "refs": _refs(chn)})
        if cnt:
            out.append({
                "do": "抖音种草 + 直播间转化 + 礼盒/年货场景 + 私域复购，不押天猫京东货架",
                "condition": "礼盒溢价 ≥30%、复购导入私域比例 ≥20%",
                "stop": "达人佣金吃掉毛利、自然流占比跌破三成，停止投流改私域",
                "refs": _refs(cnt)})
        if sz:
            out.append({
                "do": f"预算按收敛区间做，不按产值法天花板做",
                "condition": "拿到奶酪零食官方口径或一手占比数据，重算规模区间",
                "stop": "规模重算偏离 20% 以上，或社零/奶价连续两期反向，重做立项",
                "refs": _refs(sz)})
        if out:
            return out[:4]
    if thesis in GENERIC_THESES:
        picked, _ = resolve(thesis, findings)
        if picked:
            for i, f in enumerate(picked[:2], 1):
                out.append({
                    "do": f"按第 {i + 1} 节的结论做单点验证（{f.title.split('：')[0]}）",
                    "condition": "小范围样本达到同口径改善，且不劣化另一指标",
                    "stop": "连续两个周期未改善，停止扩面并复盘",
                    "refs": list(f.refs[:2])})
            return out
        return [{"do": "先补关键表再执行", "condition": "订单/评价/投放至少补齐一张",
                 "stop": "补数两周仍未齐，暂停本类报告"}]
    eco = findings.get("economics")
    rows = (_num(eco, "rows") or []) if eco else []
    neg = [r for r in rows if r["v"] < 0]
    arb = findings.get("arbitrage")
    be = findings.get("breakeven")
    mom = findings.get("momentum")

    if neg and be:
        brows = _num(be, "rows") or []
        # 按单价分路径：低单价高频品只降本（直采），高单价品才提价
        cheap = sorted([r for r in brows if r.get("share") is not None],
                       key=lambda r: r["w"].value)
        if cheap:
            r0 = cheap[0]
            out.append({"do": f"对{r0['cat']}启动产地直采，占比先做到 {r0['share'].p()}",
                        "condition": f"直采到店成本低于批发 {r0['w']} 元/斤",
                        "stop": "连续两周净毛利仍为负，或直采履约率低于九成五",
                        "refs": [r0["share"].id, r0["w"].id]})
        up = sorted([r for r in brows if r.get("up")
                     and (not cheap or r["cat"] != cheap[0]["cat"])],
                    key=lambda r: r["w"].value, reverse=True)
        if up:
            r1 = up[0]
            out.append({"do": f"{r1['cat']} 走提价路径，先提 {r1['up'].p()} 试单两周",
                        "condition": "提价后周销量跌幅小于 3%",
                        "stop": "销量跌幅超过 5%，立即回价并改走降本",
                        "refs": [r1["up"].id, r1["need"].id]})
    if arb:
        arows = _num(arb, "rows") or []
        good = [r for r in arows if r["v"] > 0]
        if good:
            g = good[0]
            out.append({"do": f"{g['cat']} 跨市配额提到四成（{g['buy_r']}→{g['sell_r']}）",
                        "condition": f"两地价差大于 {g['spread']:.2f} 元/斤",
                        "stop": "价差回落到 3 元/斤以下，或到店损耗超过 2%",
                        "refs": [g["nsp"].id, g["net"].id, g["mg"].id]})
        if len(good) < len(arows):
            bad = [r for r in arows if r["v"] <= 0]
            out.append({"do": f"关闭{_join([r['cat'] for r in bad])}的跨市调运",
                        "condition": "本地批发可满足日销",
                        "stop": "本地缺货且价差扩大一倍时再评估",
                        "refs": [r["net"].id for r in bad]})
    if mom:
        mrows = (_num(mom, "rows") or []) if _num(mom, "rows") else []
        tense = [r for r in mrows if "高位回落" in str(r.get("q", ""))]
        if tense:
            t = tense[0]
            out.append({"do": f"{t['cat']} 改「锁量不锁价」：保底收购量、结算随周度指数浮动",
                        "condition": f"环比连续两期为负（当前 {t['mom'].p()}）",
                        "stop": "出场价跌破成本线 5% 时暂停锁量",
                        "refs": [t["mom"].id, t["yoy"].id]})
    if not out:
        out.append({"do": "本轮不动采购结构，先把缺口数据补齐", "condition": "缺口补齐且复跑通过",
                    "stop": "复跑仍无稳定结论，停止扩量", "refs": []})
    return out


def _join(items: List[str], limit: int = 3) -> str:
    items = [x for x in items if x]
    return "、".join(items[:limit]) + ("等" if len(items) > limit else "")
