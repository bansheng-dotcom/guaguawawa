# -*- coding: utf-8 -*-
"""core/report_framework —— 通用专业分析框架（v9）。

解决的问题：v7/v8 的纲领是「按业务写死」的（家居百货、肉禽蛋、奶酪零食各一套）。
业务一换，就要再加一套方法、一套纲领、一套帧，报告质量依赖人工判断。

本模块把「专业分析报告」拆成与业务无关的五模块 + 一套可校验的标准：

    M1 问题定义与边界   这份报告回答什么、不回答什么、按什么口径
    M2 数据采集与校验   来源、可信度等级、交叉验证、缺口
    M3 结构化逻辑推导   MECE 维度分组，每个维度一条判断链
    M4 风险与局限       风险清单、假设敏感度、证伪条件
    M5 可落地结论       动作、责任人/时点、验收口、停止条件

场景自适应：输入分析主题后，`match()` 根据主题关键词 + 数据能力 + 已命中方法
自动选维度，不需要为每个业务写死章节。没有关键词时按数据能力选（数据驱动兜底）。

这个模块只做「框架与标准」，不生产数字；数字仍由 `core.methods` 的方法登记，
报告由 `core/frames_framework` 装配。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 1. 数据可信度等级（所有模块共用）
# --------------------------------------------------------------------------- #
CREDIBILITY: Dict[str, Dict[str, Any]] = {
    "A": {"name": "一手 / 官方", "examples": ("统计公报", "政府文件", "审计财报", "一手监测"),
          "rule": "可直接引用；口径、期次、地区必须写全，不做二次换算。"},
    "B": {"name": "行业 / 机构", "examples": ("行业协会", "企业公告", "券商研报"),
          "rule": "需注明机构、年份与口径；跨机构不可直接相加。"},
    "C": {"name": "平台 / 媒体", "examples": ("电商报价", "媒体报道", "抽样估算"),
          "rule": "只能做量级判断，不能与 A 级混算；进入报告需标 C。"},
    "D": {"name": "假设 / 判断", "examples": ("专家判断", "模型假设", "经验值"),
          "rule": "必须单列 assumptions，并给出敏感性区间，不能写成事实。"},
}
GRADE_ORDER = ("A", "B", "C", "D")


def grade_rank(g: str) -> int:
    g = str(g or "D").upper()[:1]
    return GRADE_ORDER.index(g) if g in GRADE_ORDER else 3


def grade_stats(desk) -> Dict[str, Any]:
    """数一份项目里的来源等级分布：A/B/C/D 各多少、最低等级是什么。"""
    grades: List[str] = []
    ft = getattr(desk, "ft", None)
    for f in (getattr(ft, "facts", None) or []):
        grades.append(str(getattr(f, "grade", "") or "C").upper()[:1])
    for f in (getattr(desk, "facts", None) or []):
        if isinstance(f, dict) and f.get("grade"):
            grades.append(str(f["grade"]).upper()[:1])
    for a in (getattr(desk, "assumptions", None) or []):
        grades.append(str(a.get("grade") or "C").upper()[:1])
    counts = {g: sum(1 for x in grades if x == g) for g in GRADE_ORDER}
    valid = [g for g in grades if g in GRADE_ORDER]
    return {
        "total": len(valid),
        "counts": counts,
        "lowest": max(valid, key=grade_rank) if valid else "—",
        "a_share": (counts["A"] / len(valid) * 100) if valid else 0.0,
    }


# --------------------------------------------------------------------------- #
# 2. MECE 维度库（与业务无关，按「问题」而不是「行业」定义）
# --------------------------------------------------------------------------- #
# group 必须互斥且穷尽（需求 / 供给 / 竞争与渠道 / 财务经营 / 风险执行）。
MECE_GROUPS: Dict[str, str] = {
    "demand": "需求侧",
    "supply": "供给侧",
    "competition": "竞争与渠道",
    "finance": "财务与经营",
    "risk": "风险与执行",
}

DIMENSIONS: List[Dict[str, Any]] = [
    # ---------------- 需求侧 ----------------
    {"key": "market_size", "name": "市场规模与空间", "group": "demand",
     "question": "这个市场有多大，用几条互不重叠的口径互证？",
     "methods": ["size", "sizing_multi", "cheese_size"],
     "keywords": ["规模", "空间", "体量", "总量", "TAM", "赛道", "市场有多大"],
     "standard": "至少两条独立口径互证，给区间与中位，不交单点值。"},
    {"key": "demand_structure", "name": "需求结构", "group": "demand",
     "question": "需求由哪些细分构成，结构在往哪边换？",
     "methods": ["structure", "mix", "demand", "contribution", "region", "cheese_structure"],
     "keywords": ["结构", "细分", "品类", "占比", "构成", "需求"],
     "standard": "细分必须互斥；给份额与变化方向，不罗列品类名。"},
    {"key": "growth", "name": "增长与趋势", "group": "demand",
     "question": "增长还在不在，引擎在哪一端？",
     "methods": ["growth", "momentum", "trajectory", "trend", "cheese_growth"],
     "keywords": ["增长", "增速", "趋势", "CAGR", "渗透", "下滑", "拐点", "行情"],
     "standard": "必须给时间序列或两期对照；区分总量增长与结构增长。"},
    {"key": "price", "name": "价格与量价", "group": "demand",
     "question": "价格怎么变，涨跌由量还是价驱动？",
     "methods": ["volume", "cheese_price", "structure", "cheese_quotes"],
     "keywords": ["价格", "量价", "价差", "涨价", "价格带", "客单", "采价"],
     "standard": "价格需有期次与单位；量价拆解要写出交叉项处理方式。"},
    {"key": "customer", "name": "客群与口碑", "group": "demand",
     "question": "谁在买、为什么复购、口碑短板在哪？",
     "methods": ["reviews", "rfm", "retention"],
     "keywords": ["用户", "客群", "人群", "复购", "口碑", "评价", "留存", "场景"],
     "standard": "人群需可定位；口碑要区分样本量与代表性。"},

    # ---------------- 供给侧 ----------------
    {"key": "supply", "name": "供给能力", "group": "supply",
     "question": "供给由谁提供，产能与主体密度够不够？",
     "methods": ["supply", "capacity", "cheese_supply"],
     "keywords": ["供给", "产能", "企业", "工厂", "作坊", "产量", "供应商"],
     "standard": "供给主体要能落到数量与地域；产能需区分规划与达产。"},
    {"key": "cost", "name": "成本结构", "group": "supply",
     "question": "成本由哪几项构成，哪一项最刚性？",
     "methods": ["cost", "unit_econ", "economics", "cheese_unit_econ"],
     "keywords": ["成本", "毛利", "净利", "单位经济", "保本", "出厂", "损耗"],
     "standard": "成本栈要逐项拆分；假设项单列并给敏感性。"},
    {"key": "chain", "name": "链路与传导", "group": "supply",
     "question": "从上游到终端，利润被哪一段吃掉？",
     "methods": ["transmission", "arbitrage", "spread", "chain", "cheese_chain"],
     "keywords": ["链路", "供应链", "传导", "加价", "批发", "零售", "物流", "断点"],
     "standard": "至少三段价差；每段给金额与占比，不只给加价率。"},

    # ---------------- 竞争与渠道 ----------------
    {"key": "competition", "name": "竞争格局", "group": "competition",
     "question": "市场集中在哪里，正面对打还是找缝隙？",
     "methods": ["concentration", "cheese_region"],
     "keywords": ["竞争", "集中度", "份额", "CR", "HHI", "格局", "对手", "头部"],
     "standard": "给 CR/HHI 或前几名份额；结论要落到进入成本。"},
    {"key": "channel", "name": "渠道与内容", "group": "competition",
     "question": "钱从哪个渠道流走，内容和货架怎么配合？",
     "methods": ["channel", "cheese_channel", "cheese_content"],
     "keywords": ["渠道", "电商", "抖音", "天猫", "线下", "内容", "种草", "礼盒", "营销"],
     "standard": "渠道要有份额或增速；内容动作要能落到选题与转化。"},
    {"key": "product", "name": "产品与商品结构", "group": "competition",
     "question": "先做哪个产品/单品，依据是什么？",
     "methods": ["priority", "sku", "store"],
     "keywords": ["产品", "SKU", "上架", "单品", "选品", "门店"],
     "standard": "排序要有统一打分维度（需求/能力/回报），不能凭感觉。"},

    # ---------------- 财务经营 ----------------
    {"key": "unit_economics", "name": "单位经济与保本", "group": "finance",
     "question": "一单位赚多少，低于什么价不能接？",
     "methods": ["unit_econ", "economics", "margin", "breakeven", "cheese_unit_econ"],
     "keywords": ["单位经济", "保本", "净利", "毛利", "报价", "定价", "成本"],
     "standard": "收入-成本-渠道-损耗逐项列；给保本价与安全垫。"},
    {"key": "capital_return", "name": "投入与回报", "group": "finance",
     "question": "投多少、多久回本、回报靠什么驱动？",
     "methods": ["roi", "payment_mix", "entry_gate", "forecast"],
     "keywords": ["投资", "回报", "ROI", "回本", "现金流", "预算", "预测"],
     "standard": "投入与回报同口径；给回收期或 ROI，并标敏感性。"},
    {"key": "store_ops", "name": "经营与周转", "group": "finance",
     "question": "库存、周转、损耗和门店模型撑不撑得住？",
     "methods": ["store", "sku"],
     "keywords": ["经营", "库存", "周转", "损耗", "门店", "坪效", "动销"],
     "standard": "周转与损耗要同期次；门店模型要能复制才给扩张结论。"},

    # ---------------- 风险与执行 ----------------
    {"key": "policy", "name": "政策与合规", "group": "risk",
     "question": "政策在推什么、哪条红线不能碰？",
     "methods": ["policy", "cheese_policy"],
     "keywords": ["政策", "补贴", "监管", "标准", "合规", "资质"],
     "standard": "政策要落到条款与金额；合规结论必须可执行（谁去办、办什么）。"},
    {"key": "risk", "name": "风险与数据缺口", "group": "risk",
     "question": "哪些结论现在不能下，什么会推翻它？",
     "methods": ["risk", "incidents", "sample", "consistency", "coverage", "cheese_coverage"],
     "keywords": ["风险", "缺口", "不确定", "假设", "回撤", "波动", "异常"],
     "standard": "风险要按概率×影响排序；缺口要写补数动作，不写「有待观察」。"},
    {"key": "execution", "name": "执行与组织", "group": "risk",
     "question": "谁来做、按什么节奏、什么算做完？",
     "methods": ["sla", "headcount", "capacity", "funnel", "retention", "rfm", "roi"],
     "keywords": ["执行", "组织", "人效", "交付", "落地", "增长", "转化", "留存"],
     "standard": "动作要有 owner、时点、验收口与停止条件；没有责任人的动作不算动作。"},
    # ---------------- P9：20 角色域扩展 ----------------
    {"key": "org", "name": "组织与编制", "group": "risk",
     "question": "组织、岗位与编制撑不撑得住这条业务？",
     "methods": ["headcount", "capacity"],
     "keywords": ["组织", "编制", "岗位", "人效", "招聘"],
     "standard": "组织结论要落到岗位/编制/人效；没有责任人的编制不算。"},
    {"key": "tech", "name": "技术交付", "group": "risk",
     "question": "技术规格、测试与回滚能不能兜住交付？",
     "methods": [],
     "keywords": ["技术", "规格", "测试", "回滚", "接口", "工程"],
     "standard": "技术交付要有规格、测试与回滚；没有回滚的交付不算完成。"},
    {"key": "reliability", "name": "可靠性", "group": "risk",
     "question": "SLO、故障与备份能不能兜住线上？",
     "methods": ["sla", "incidents"],
     "keywords": ["SLO", "故障", "备份", "演练", "告警", "可用性"],
     "standard": "可靠性要有 SLO/告警/演练；没有 RTO/RPO 的备份不算恢复。"},
    {"key": "transaction", "name": "交易与履约", "group": "supply",
     "question": "订单、支付、履约与退款是否闭合？",
     "methods": [],
     "keywords": ["订单", "支付", "履约", "退款", "对账", "交易"],
     "standard": "交易三态要互不矛盾；退款要有比例与前置状态。"},
    {"key": "content", "name": "内容与品牌", "group": "demand",
     "question": "内容、品牌与语调能不能被验证？",
     "methods": [],
     "keywords": ["内容", "品牌", "语调", "素材", "投放", "禁词"],
     "standard": "内容/品牌结论要有可核验素材；没有转化数据的只算定性。"},
    {"key": "data", "name": "数据与模型", "group": "risk",
     "question": "数据、模型与评测是否可复现、可发布？",
     "methods": [],
     "keywords": ["数据", "血缘", "质量", "模型", "评测", "回归"],
     "standard": "数据/模型结论要有血缘、质量与评测；没有回归的不发布。"},
]

DIM_BY_KEY: Dict[str, Dict[str, Any]] = {d["key"]: d for d in DIMENSIONS}

# 这两个维度的职责在 M4/M5（风险与动作），不重复进 M3 推导，避免同一件事说两遍。
M3_EXCLUDE = {"risk", "execution"}
METHOD_TO_DIM: Dict[str, str] = {}
for _d in DIMENSIONS:
    for _m in _d["methods"]:
        METHOD_TO_DIM.setdefault(_m, _d["key"])


# --------------------------------------------------------------------------- #
# 3. 五大模块与专业度标准
# --------------------------------------------------------------------------- #
MODULES: List[Dict[str, Any]] = [
    {
        "id": "M1", "name": "问题定义与边界界定",
        "answers": "这份报告回答什么、不回答什么、按什么口径",
        "required": ("结论先行（一句话含数字）", "适用范围", "不适用范围", "口径与期次"),
        "standards": (
            "标题即结论：首屏标题必须是一个带数字的判断，不是「某某分析」。",
            "边界三件事：适用对象、时间窗、口径；三者缺一，结论不能外推。",
            "问题树：顶层问题用 MECE 拆成 3—5 个子问题，子问题与后文章节一一对应。",
        ),
        "checkpoint": "M1 不过 → 停止生成，先补问题定义；不允许边写边想。",
    },
    {
        "id": "M2", "name": "多维度数据采集与校验",
        "answers": "数据从哪来、凭什么信、能不能互证、缺什么",
        "required": ("来源清单", "可信度等级 A/B/C/D", "交叉验证 ≥1 组", "缺口清单"),
        "standards": (
            "每条事实必须带来源（url/文件）、期次、单位、地区、等级；缺一项降一级。",
            "A 级可直接引用，B 级需注明口径，C 级只能做量级判断，D 级必须进 assumptions。",
            "至少一组交叉验证：多路径测算、两套口径、上下游对齐，三者任选其一。",
            "缺口必须写「缺什么 → 影响哪条结论 → 怎么补」，不写「有待进一步分析」。",
        ),
        "checkpoint": "M2 不过 → 结论降级为「待验证」，不得进入动作清单。",
    },
    {
        "id": "M3", "name": "结构化逻辑推导",
        "answers": "按 MECE 维度拆开，每个维度给出可复算的判断链",
        "required": ("维度覆盖 ≥3 个 MECE 组", "每维度 观察→对照→机理→落点→证伪", "每条结论有 refs"),
        "standards": (
            "维度分组必须 MECE：同一组内维度互斥，五组合起来覆盖需求/供给/竞争渠道/财务/风险。",
            "每个维度至少一条判断，判断必须带数字、带对照、带可观测的落点。",
            "机理不是套话：写清「因为 A 所以 B」的传导，且 A、B 都能在数据里找到。",
            "证伪条件必须可观测（阈值/时点/指标），不写「如果情况变化」。",
        ),
        "checkpoint": "M3 不过 → 该维度删除，不用估算补；报告节数宁可少，不可凑。",
    },
    {
        "id": "M4", "name": "风险与局限性说明",
        "answers": "哪些结论不能下、依赖什么假设、什么会推翻",
        "required": ("风险清单（概率×影响）", "假设敏感度", "证伪条件", "回退方案"),
        "standards": (
            "风险按概率×影响排序，给出触发指标与应对动作；不列「市场有风险」这类空话。",
            "每条 C/D 级假设都要有敏感度：假设变 1 个单位，结论变多少。",
            "每条核心结论配一条证伪条件；证伪条件与动作的停止条件一致。",
            "回退方案要写「回到哪一步、谁决定、多久内决定」。",
        ),
        "checkpoint": "M4 不过 → 报告不得发布；先补风险与回退。",
    },
    {
        "id": "M5", "name": "可落地结论输出",
        "answers": "做什么、谁做、什么时候做、什么算做完、什么时候停",
        "required": ("动作清单", "责任人与时点", "验收口", "停止条件", "不做清单"),
        "standards": (
            "每条动作四要素齐全：动作、owner、时点、验收口；缺 owner 的动作不算动作。",
            "每条动作配停止条件，且停止条件可观测（指标阈值或时点）。",
            "不做清单与动作清单同等重要：写清「现在不做什么、为什么」。",
            "结论按「先做什么、后做什么」排序，排序依据写出来（回报/风险/依赖）。",
        ),
        "checkpoint": "M5 不过 → 报告只能当分析稿，不能当决策稿。",
    },
]

MODULE_BY_ID = {m["id"]: m for m in MODULES}


# --------------------------------------------------------------------------- #
# 4. 场景自适应：主题 → 维度
# --------------------------------------------------------------------------- #
def _available_methods(findings: Optional[Dict[str, Any]]) -> set:
    return set((findings or {}).keys())


def guess_methods(profile: Optional[Dict[str, Any]]) -> set:
    """没有 findings 时（CLI 预览），按数据能力猜可用方法族。"""
    p = profile or {}
    ms: set = set()
    if p.get("facts"):
        ms |= {"size", "growth", "structure", "demand", "policy", "coverage",
               "concentration", "cheese_size", "cheese_growth", "cheese_structure"}
    ch = p.get("channels") or {}
    if (ch.get("retail") or 0) + (ch.get("wholesale") or 0) + (ch.get("origin") or 0) > 0:
        ms |= {"volume", "economics", "transmission", "arbitrage", "breakeven",
               "risk", "price", "cheese_price", "cheese_chain"}
    kinds = p.get("kinds") or {}
    if kinds and sum(kinds.values()) > 2:
        ms |= {"funnel", "retention", "roi", "priority", "store", "sku"}
    return ms


def match(topic: str, profile: Optional[Dict[str, Any]] = None,
          findings: Optional[Dict[str, Any]] = None,
          max_dims: int = 8) -> List[Dict[str, Any]]:
    """主题 + 数据能力 + 已命中方法 → 选中的分析维度。

    评分 = 关键词命中 ×10 + 可用方法 ×4 + 数据能力 ×1。
    没有任何关键词命中时，按「可用方法」兜底（数据驱动，不为场景定制）。
    """
    s = str(topic or "")
    prof = profile or {}
    avail = _available_methods(findings) or guess_methods(prof)
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for d in DIMENSIONS:
        if d["key"] in M3_EXCLUDE:
            continue
        kw = sum(1 for w in d["keywords"] if w and w in s)
        am = sum(1 for m in d["methods"] if m in avail)
        cap = 1 if (prof.get("facts") or prof.get("tables")
                    or (prof.get("channels") or {})) else 0
        score = kw * 10 + am * 4 + cap
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: (-x[0], DIM_BY_KEY[x[1]["key"]]["group"]))

    picked: List[Dict[str, Any]] = []
    groups: set = set()
    # 先保证 MECE 组覆盖：每组至少一个
    for score, d in scored:
        if d["group"] not in groups:
            picked.append(d)
            groups.add(d["group"])
        if len(groups) >= len(MECE_GROUPS):
            break
    # 再按分数补维度，同组最多 2 个，总数不超过 max_dims
    for score, d in scored:
        if len(picked) >= max_dims:
            break
        if d in picked:
            continue
        same = [p for p in picked if p["group"] == d["group"]]
        if len(same) >= 2:
            continue
        # 同组已有高度重叠的方法，不重复选
        if any(set(p["methods"]) & set(d["methods"]) for p in same):
            continue
        picked.append(d)
    return picked[:max_dims]


def mece_check(dims: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """MECE 自检：组覆盖数、同组维度是否重叠、维度是否有对应方法。"""
    ds = list(dims)
    groups = {d["group"] for d in ds}
    dup = []
    for i, a in enumerate(ds):
        for b in ds[i + 1:]:
            if a["group"] == b["group"] and set(a["methods"]) & set(b["methods"]):
                dup.append([a["key"], b["key"]])
    return {
        "groups": len(groups),
        "group_names": [MECE_GROUPS[g] for g in sorted(groups)],
        "dimensions": len(ds),
        "duplicates": dup,
        "ok": len(groups) >= 3 and not dup,
    }


def blueprint(topic: str, profile: Optional[Dict[str, Any]] = None,
              findings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """完整蓝图：五模块 + 选中维度 + 标准 + 质量节点。"""
    dims = match(topic, profile, findings)
    mece = mece_check(dims)
    avail = _available_methods(findings) or guess_methods(profile)
    return {
        "schema": "dsh.report_framework/v1",
        "topic": str(topic or ""),
        "modules": MODULES,
        "dimensions": [
            {"key": d["key"], "name": d["name"], "group": d["group"],
             "group_name": MECE_GROUPS[d["group"]], "question": d["question"],
             "methods": d["methods"], "available": [
                 m for m in d["methods"] if m in avail],
             "standard": d["standard"]}
            for d in dims
        ],
        "mece": mece,
        "execution": execution_flow(),
    }


def execution_flow() -> List[Dict[str, str]]:
    """执行流程：每一步的操作规范与质量校验节点。"""
    return [
        {"step": "S0 输入", "do": "读分析主题、项目数据、已有事实表；识别数据能力（事实表/价格表/业务表）",
         "out": "能力清单与缺口", "gate": "主题不能为空；数据目录必须可读"},
        {"step": "S1 问题定义", "do": "写清回答什么/不回答什么/口径；用 MECE 拆 3—5 个问题",
         "out": "M1 问题定义与边界", "gate": "M1：标题带数字、边界三件事齐、问题与章节一一对应"},
        {"step": "S2 数据采集", "do": "登记来源、期次、单位、地区、等级；C/D 级进假设表",
         "out": "M2 来源与等级表", "gate": "M2：无来源不登记；A/B/C/D 分布可查"},
        {"step": "S3 数据校验", "do": "多路径/两口径/上下游至少一组交叉验证；列缺口",
         "out": "M2 校验与缺口", "gate": "M2：至少 1 组交叉验证；缺口写补数动作"},
        {"step": "S4 维度匹配", "do": "按主题关键词 + 数据能力选维度，保证 ≥3 个 MECE 组",
         "out": "维度蓝图", "gate": "M3 预检：组覆盖 ≥3；同组不重叠"},
        {"step": "S5 结构化推导", "do": "每个维度走 观察→对照→机理→落点→证伪，数字全部登记",
         "out": "M3 各维度章节", "gate": "M3：每条结论有 refs；数字可由 refs 解释"},
        {"step": "S6 风险与局限", "do": "风险按概率×影响排序；C/D 假设给敏感度；写证伪与回退",
         "out": "M4 风险与局限", "gate": "M4：每条核心结论有证伪条件；有回退方案"},
        {"step": "S7 结论与动作", "do": "动作四要素（动作/owner/时点/验收口）+ 停止条件 + 不做清单",
         "out": "M5 结论与动作", "gate": "M5：无 owner 的动作剔除；停止条件可观测"},
        {"step": "S8 成稿门禁", "do": "跑深度门禁 + 成品门禁 + 专业标准门禁，不过不渲染",
         "out": "report.html / report.md", "gate": "Q1—Q7、F1—F9、M1—M5 全过"},
        {"step": "S9 复核", "do": "R04 独立评审：抽 3 条结论回溯到来源；抽 2 条动作查 owner",
         "out": "评审记录", "gate": "任一条回溯失败 → 退回 S3"},
    ]


def module_table() -> List[Dict[str, str]]:
    return [{"id": m["id"], "name": m["name"], "answers": m["answers"],
             "checkpoint": m["checkpoint"]} for m in MODULES]


def demo(topic: str, profile: Optional[Dict[str, Any]] = None,
         findings: Optional[Dict[str, Any]] = None) -> str:
    """给 CLI/文档用：打印蓝图摘要。"""
    bp = blueprint(topic, profile, findings)
    lines = [f"主题：{bp['topic']}",
             f"MECE：{bp['mece']['groups']} 组 / {bp['mece']['dimensions']} 维；"
             f"OK={bp['mece']['ok']}",
             "维度："]
    for d in bp["dimensions"]:
        lines.append(f"  - [{d['group_name']}] {d['name']}（{d['key']}）"
                     f" 可用方法：{', '.join(d['available']) or '无'}")
    lines.append("模块：")
    for m in bp["modules"]:
        lines.append(f"  {m['id']} {m['name']}：{m['answers']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="通用专业分析框架蓝图")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--dir", default=None, help="项目目录（可选，用来识别数据能力）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    prof = None
    if a.dir:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
        from core import analysis_desk
        desk = analysis_desk.scan(a.dir)
        prof = analysis_desk.profile(desk)
    if a.json:
        import json
        print(json.dumps(blueprint(a.topic, prof), ensure_ascii=False, indent=2))
    else:
        print(demo(a.topic, prof))
