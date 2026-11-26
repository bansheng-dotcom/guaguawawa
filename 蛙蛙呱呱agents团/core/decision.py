# -*- coding: utf-8 -*-
"""core/decision —— 决策契约：报告的上游唯一对象。

第一性原理：一份报告的最小单位不是「一节文字」，而是
    决策 → 问题 → 对照 → 证据 → 编码

旧产线只有「证据」这一环：方法从数据里找能算的东西，问题由结果反推，
图是方法的默认装饰。于是出现三种失效：
- 意图不绑定（问招聘、答水果）；
- 覆盖度自证（用答过的问题算覆盖率，恒等于 1.0）；
- 图表装饰化（chart_spec 契约存在但从不执行，48 型只用 3 型）。

本模块把缺的那一环补上：
- DecisionContract：3–5 个必答问题，每个问题带决策、对照、图型、证伪条件；
- draft()：没有 data/decision.json 时，从数据能力起草（标 auto=true，不冒充决策稿）；
- validate()：问题必须能落到 finding，对照必须是可比较的，图型必须能表达该对照；
- chart_contract()：把图变成「证明某条判断」的规格，跑 core/chart_spec 的硬校验；
- bind()：declared（开工前问的） vs answered（报告真答的），算出诚实的覆盖率。

用法：
    python -m core.decision draft --intent "…" --dir <项目> --out decision.draft.json
    python -m core.decision check --decision decision.json
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.charts import chart_capabilities, chart_spec

SCHEMA = "dsh.decision/v1"
MIN_Q, MAX_Q = 3, 5

# --------------------------------------------------------------------------- #
# 图型选型：唯一出处是 configs/chart_by_relation.yaml
#
# 旧的 CHART_POLICY 是写死在代码里的第二份（与 chart_type_by_question.json 重复，
# 后者 0 引用）。v11 / P4 起改成「读配置」：
#   关系（deviation / ranking / ...） → allowed 图型列表
#   对照类型（compare_categories / ...） → 关系
# 这里保留 `CHART_POLICY` 这个名字与结构，外部调用方不用改。
# --------------------------------------------------------------------------- #
_ROOT = Path(__file__).resolve().parent.parent
_RELATION_FILE = _ROOT / "configs" / "chart_by_relation.yaml"

# 兜底：配置文件缺失时仍能跑（与 yaml 内容保持一致，避免两套语义）
_FALLBACK_POLICY: Dict[str, List[str]] = {
    "compare_categories": ["hbar", "vbar", "dot", "lollipop"],
    "compare_to_zero": ["vbar", "hbar", "dot"],
    "compare_two_points": ["grouped_bar", "dumbbell", "slope"],
    "change_over_time": ["line", "area"],
    "composition": ["stacked_bar", "pct_stacked"],
    "distribution": ["histogram", "box", "dot"],
    "relationship": ["scatter", "bubble"],
    "vs_threshold": ["bullet", "target_band", "vbar"],
}


def _load_policy() -> Tuple[Dict[str, List[str]], Dict[str, str], str]:
    """读 chart_by_relation.yaml → (对照类型→图型, 对照类型→关系, 来源)。"""
    if not _RELATION_FILE.exists():
        return dict(_FALLBACK_POLICY), {}, "fallback(no-file)"
    try:
        import yaml
        doc = yaml.safe_load(_RELATION_FILE.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001  配置坏了不能拖垮出报告
        return dict(_FALLBACK_POLICY), {}, "fallback(yaml-error)"
    rels = doc.get("relations") or {}
    mapping = doc.get("comparison_to_relation") or {}
    policy: Dict[str, List[str]] = {}
    for kind, rel in mapping.items():
        allowed = [t for t in ((rels.get(rel) or {}).get("allowed") or [])
                   if chart_capabilities.has_chart(t)]
        if allowed:
            policy[str(kind)] = allowed
    if not policy:
        return dict(_FALLBACK_POLICY), {}, "fallback(empty)"
    for k, v in _FALLBACK_POLICY.items():   # 配置漏了某类时补上，不让契约校验误伤
        policy.setdefault(k, v)
    return policy, {str(k): str(v) for k, v in mapping.items()}, str(_RELATION_FILE.name)


CHART_POLICY, COMPARISON_TO_RELATION, CHART_POLICY_SOURCE = _load_policy()

# 问题库：一个 finding 能回答的那个「决策问题」。
# priority 越小越先入选；问题由编排器决定，本表只决定「同一 finding 里先问哪一问」。
_BANK_LEGACY: List[Dict[str, Any]] = [
    {"id": "q.move", "finding": "structure", "priority": 10,
     "text": "哪些对象在变、变化多大？", "decision": "调整结构 / 资源投向",
     "comparison": {"kind": "compare_categories", "left": "对象", "right": "零线",
                    "metric": "区间变化率", "unit": "%"},
     "falsifier": "若多数对象变化方向与本节相反，本节作废。"},
    {"id": "q.trend", "finding": "trajectory", "priority": 20,
     "text": "这段变化是趋势还是单点噪声？", "decision": "是否按趋势定价 / 备货",
     "comparison": {"kind": "change_over_time", "left": "本期", "right": "期初",
                    "metric": "期间值", "unit": ""},
     "falsifier": "若去掉首末两点后方向反转，本节作废。"},
    {"id": "q.pace", "finding": "momentum", "priority": 30,
     "text": "短期与去年同期的方向是否一致？", "decision": "周度随行还是月度锁价",
     "comparison": {"kind": "compare_two_points", "left": "环比", "right": "同比",
                    "metric": "变化率", "unit": "%"},
     "falsifier": "若环比与同比由反向转为同向，本节结论作废。"},
    {"id": "q.driver", "finding": "contribution", "priority": 40,
     "text": "整体变动主要由谁贡献？", "decision": "先动哪几个对象",
     "comparison": {"kind": "compare_to_zero", "left": "涨端合计", "right": "跌端合计",
                    "metric": "贡献额", "unit": ""},
     "falsifier": "若贡献最大的对象换人，本节排序作废。"},
    {"id": "q.unit", "finding": "economics", "priority": 50,
     "text": "扣掉履约成本后，哪些是负毛利？", "decision": "停采 / 换源 / 提价",
     "comparison": {"kind": "compare_to_zero", "left": "净毛利", "right": "零",
                    "metric": "单位净毛利", "unit": "元/单位"},
     "falsifier": "若实际损耗或履约成本比假设低 20%，负毛利名单重算。"},
    {"id": "q.chain", "finding": "transmission", "priority": 60,
     "text": "钱在哪一段被吃掉？", "decision": "直采比例 / 渠道选择",
     "comparison": {"kind": "compare_two_points", "left": "上游价", "right": "下游价",
                    "metric": "价差", "unit": "元/单位"},
     "falsifier": "若上下游不是同规格同期，本节价差作废。"},
    {"id": "q.breakeven", "finding": "breakeven", "priority": 70,
     "text": "要提多少才保本？", "decision": "提价幅度 / 止损线",
     "comparison": {"kind": "vs_threshold", "left": "当前价", "right": "保本价",
                    "metric": "提价幅度", "unit": "%"},
     "falsifier": "若成本假设变化超过区间，保本线重算。"},
    {"id": "q.risk", "finding": "risk", "priority": 80,
     "text": "这个结论在什么情况下不成立？", "decision": "要不要设停止条件",
     "comparison": {"kind": "distribution", "left": "各对象", "right": "阈值",
                    "metric": "波动", "unit": ""},
     "falsifier": "若风险项全部未触发，本节降级为观察。"},
    {"id": "q.sample", "finding": "sample", "priority": 90,
     "text": "样本够不够支撑这个结论？", "decision": "能不能下确定性结论",
     "comparison": {"kind": "distribution", "left": "当前样本", "right": "所需样本",
                    "metric": "样本量", "unit": "期/条"},
     "falsifier": "若补充样本后区间跨零，本节结论降级。"},
    {"id": "q.forecast", "finding": "forecast", "priority": 100,
     "text": "下一期大概在哪？", "decision": "锁价 / 清库时点",
     "comparison": {"kind": "change_over_time", "left": "历史", "right": "外推",
                    "metric": "中枢", "unit": ""},
     "falsifier": "若实际值落在区间外，外推作废。"},
    {"id": "q.funnel", "finding": "funnel", "priority": 110,
     "text": "哪一步流失最多？", "decision": "先修哪一段转化",
     "comparison": {"kind": "compare_categories", "left": "各步骤", "right": "上一步",
                    "metric": "转化率", "unit": "%"},
     "falsifier": "若最大流失步骤换人，本节作废。"},
    {"id": "q.retention", "finding": "retention", "priority": 120,
     "text": "留存/复购是在改善还是恶化？", "decision": "投入拉新还是留存",
     "comparison": {"kind": "change_over_time", "left": "本期", "right": "上期",
                    "metric": "留存率", "unit": "%"},
     "falsifier": "若口径从注册改为激活后方向反转，本节作废。"},
    {"id": "q.roi", "finding": "roi", "priority": 130,
     "text": "投入产出比是否为正？", "decision": "继续投放 / 停投",
     "comparison": {"kind": "compare_to_zero", "left": "产出", "right": "投入",
                    "metric": "ROI", "unit": "倍"},
     "falsifier": "若回收周期超过约定窗口，ROI 结论作废。"},
    {"id": "q.sla", "finding": "sla", "priority": 140,
     "text": "可靠性是否达标？", "decision": "要不要扩容 / 加固",
     "comparison": {"kind": "vs_threshold", "left": "实测", "right": "SLA",
                    "metric": "可用性", "unit": "%"},
     "falsifier": "若统计窗口内无事故，达标结论只对窗口内成立。"},
    {"id": "q.capacity", "finding": "capacity", "priority": 150,
     "text": "容量是否够？", "decision": "扩容 / 限流",
     "comparison": {"kind": "vs_threshold", "left": "峰值", "right": "容量",
                    "metric": "利用率", "unit": "%"},
     "falsifier": "若峰值口径不含突发流量，本节作废。"},
    {"id": "q.priority", "finding": "priority", "priority": 160,
     "text": "先做哪几件？", "decision": "排期",
     "comparison": {"kind": "compare_categories", "left": "各项", "right": "阈值",
                    "metric": "优先级分", "unit": "分"},
     "falsifier": "若依赖关系变化，排序作废。"},
    {"id": "q.reviews", "finding": "reviews", "priority": 170,
     "text": "口碑风险集中在哪？", "decision": "改产品还是改预期",
     "comparison": {"kind": "distribution", "left": "评价维度", "right": "均值",
                    "metric": "评分", "unit": "分"},
     "falsifier": "若差评集中在少数异常订单，本节作废。"},
    {"id": "q.headcount", "finding": "headcount", "priority": 180,
     "text": "编制与产出是否匹配？", "decision": "招人 / 缩编",
     "comparison": {"kind": "compare_categories", "left": "团队", "right": "目标",
                    "metric": "人均产出", "unit": ""},
     "falsifier": "若业务口径变化，人均产出作废。"},
    # ---------------- 调研族（v11 / 调味料起）---------------- #
    # 这些 finding 来自 core/methods/market.py 与 core/methods/seasoning.py；
    # 没有这几条，r05 出场也问不出问题，调研型报告会被判「无可答问题」。
    {"id": "q.market_size", "finding": "seasoning_size", "priority": 5,
     "text": "这个盘子有多大，几条口径互证？", "decision": "预算按哪条口径做",
     "comparison": {"kind": "compare_two_points", "left": "社零占比法", "right": "餐饮成本法",
                    "metric": "规模（亿元）", "unit": "亿元"},
     "falsifier": "若补到一手采购数据后偏离本区间 30% 以上，本区间作废。"},
    {"id": "q.market_structure", "finding": "seasoning_structure", "priority": 6,
     "text": "钱在哪个品类，份额在往哪边挪？", "decision": "选品与资源投向",
     "comparison": {"kind": "compare_categories", "left": "品类", "right": "行业均值",
                    "metric": "份额（%）", "unit": "%"},
     "falsifier": "若下期酱油份额转负、酱腌菜转正，结构判断作废。"},
    {"id": "q.market_channel", "finding": "seasoning_channel", "priority": 7,
     "text": "货该铺在哪，各渠道差多少？", "decision": "渠道与陈列投入",
     "comparison": {"kind": "compare_categories", "left": "渠道", "right": "第一入口",
                    "metric": "购买占比（%）", "unit": "%"},
     "falsifier": "若电商占比反超超市，渠道判断作废。"},
    {"id": "q.market_growth", "finding": "seasoning_growth", "priority": 8,
     "text": "行业增速和本地消费大盘，谁快谁慢？", "decision": "增长从哪来、能不能吃到",
     "comparison": {"kind": "compare_categories", "left": "行业增速", "right": "本地大盘",
                    "metric": "同比增速（%）", "unit": "%"},
     "falsifier": "若行业增速回落到本地大盘以下，增长来自结构升级的判断作废。"},
]

# 动作库 = 方法注册表 × 覆盖项（v12）
# 手写 22 条降级为覆盖项；没覆盖的方法按自述生成一条问题。
# 这样「有问题没方法」与「有方法没问题」结构上都不可能发生。
_DEFAULT_FALSIFIER = "若下期该指标背离本节方向超过 5.0%，本节作废。"


def _q_from_method(key: str, spec) -> Dict[str, Any]:
    produces = str(getattr(spec, "produces", "") or key)
    desc = str(getattr(spec, "description", "") or "").strip()
    first = desc.split("；")[0].split("，")[0].strip() if desc else ""
    return {
        "id": f"q.{key}",
        "finding": key,
        "priority": int(getattr(spec, "priority", 100) or 100),
        "text": f"{produces}：现在是什么水平，与谁比、差多少？",
        "decision": "是否调整" + (first or produces),
        "comparison": {"kind": "compare_categories", "left": produces,
                       "right": "基准", "metric": produces, "unit": ""},
        "falsifier": _DEFAULT_FALSIFIER,
    }


def _build_qbank() -> List[Dict[str, Any]]:
    from core import methods as _m
    legacy = {q["finding"]: q for q in _BANK_LEGACY}
    out = [dict(legacy[k]) if k in legacy else _q_from_method(k, sp)
           for k, sp in _m.REGISTRY.items()]
    out.sort(key=lambda q: int(q.get("priority", 100)))
    return out


QBANK = _build_qbank()

BY_ID = {q["id"]: q for q in QBANK}
BY_FINDING = {q["finding"]: q for q in QBANK}

# 意图 → finding 的语义提示词。
# 用途：同一批专家面对不同问题时，问出来的问题必须不同（否则「同数据不同意图」
# 会得到同一份报告）。这里只做**排序加权**，不做筛选——筛选已经在编排器做过。
_INTENT_HINTS: Dict[str, tuple] = {
    "structure": ("涨", "跌", "分化", "哪些", "谁在", "结构", "品类"),
    "trajectory": ("趋势", "噪声", "轨迹", "波动", "斜率", "拐点"),
    "momentum": ("环比", "同比", "节奏", "短期", "基数", "反弹"),
    "contribution": ("贡献", "拉动", "主要", "换手", "净变动", "谁贡献"),
    "economics": ("毛利", "净利", "成本", "亏", "赚", "单位经济", "加价"),
    "transmission": ("链路", "传导", "价差", "中间", "集散", "终端"),
    "arbitrage": ("跨市", "套利", "两地", "调运", "运费"),
    "breakeven": ("保本", "提价", "直采", "止损", "转正"),
    "risk": ("风险", "缺口", "样本", "覆盖", "稳不稳", "可靠"),
    "sample": ("样本", "够不够", "显著性", "功效"),
    "forecast": ("预测", "下季度", "外推", "情景"),
    "funnel": ("漏斗", "转化", "流失"),
    "retention": ("留存", "复购", "回访"),
    "roi": ("投产", "roi", "回本", "投放"),
    "priority": ("优先级", "先做", "排期"),
    "headcount": ("招聘", "编制", "人效", "组织"),
    "seasoning_size": ("规模", "多大", "盘子", "市场多大", "调研", "市场研究"),
    "seasoning_structure": ("品类", "结构", "份额", "酱油", "哪个品类"),
    "seasoning_channel": ("渠道", "铺货", "超市", "电商", "场景"),
    "capacity": ("产能", "容量", "瓶颈"),
    "sla": ("sla", "可用性", "响应"),
    "reviews": ("评价", "口碑", "差评"),
}


def _intent_match(intent: str, q: Dict[str, Any]) -> int:
    """这个问题和用户的意图有多像（只用于排序，不用于筛选）。"""
    s = str(intent or "")
    score = 0
    for w in _INTENT_HINTS.get(str(q.get("finding") or ""), ()):
        if w and w.lower() in s.lower():
            score += 2
    # 问题文本与自己写的判断里的 2-gram 重叠（权重低，避免被常见字带偏）
    blob = f"{q.get('text') or ''}{q.get('decision') or ''}"
    grams = {s[i:i + 2] for i in range(max(0, len(s) - 1))}
    score += sum(1 for g in grams if len(g) == 2 and g in blob)
    return score


# --------------------------------------------------------------------------- #
# 起草
# --------------------------------------------------------------------------- #
def draft(intent: str, available: Iterable[str], decision: str = "",
          audience: str = "业务负责人") -> Dict[str, Any]:
    """从「数据能回答什么」起草契约。auto=true 表示这不是人给的决策问题。

    选问题先保「对照类型不重复」：五个 hbar 不是五条判断，是一种判断。

    注意（v11）：这是**兜底**路径。正常路径是 `draft_from_roster()`：
    问题由编排器选出的专家决定，而不是由数据能算什么决定。
    """
    have = [k for k in available if k in BY_FINDING]
    pool = sorted({k: BY_FINDING[k] for k in have}.values(), key=lambda q: q["priority"])
    if len(pool) < MIN_Q:
        pool = sorted(QBANK, key=lambda q: q["priority"])
    picked: List[Dict[str, Any]] = []
    kinds: set = set()
    for q in pool:
        if len(picked) >= MAX_Q:
            break
        kind = q["comparison"]["kind"]
        if kind in kinds:
            continue
        picked.append(q)
        kinds.add(kind)
    for q in pool:                       # 不够 5 个再按优先级补齐
        if len(picked) >= MAX_Q:
            break
        if q not in picked:
            picked.append(q)
    picked = picked[:MAX_Q]
    qs = []
    for i, q in enumerate(picked, 1):
        qs.append({
            "id": f"dq{i}",
            "text": q["text"],
            "decision": decision or q["decision"],
            "finding": q["finding"],
            "comparison": dict(q["comparison"]),
            "falsifier": q["falsifier"],
            "chart": {"type": CHART_POLICY[q["comparison"]["kind"]][0]},
            "owner": "",
        })
    return {
        "schema": SCHEMA,
        "intent": intent,
        "decision": decision or "读完这份报告要做的取舍",
        "audience": audience,
        "data_cutoff": "",
        "auto": True,
        "drafted_from": "data",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "questions": qs,
    }


def draft_from_roster(intent: str, roster: Iterable[Dict[str, Any]],
                      decision: str = "", audience: str = "业务负责人",
                      min_q: int = MIN_Q, max_q: int = MAX_Q) -> Dict[str, Any]:
    """按「专家能答什么」起草契约（v11 正常路径）。

    与 `draft()` 的唯一差别是**问题来源**：
        draft()             从「挂载了哪些方法」反推问题 → 问招聘也能答水果
        draft_from_roster() 从「哪些专家出场、它们能答什么」抽问题 → 答不了就不问

    每个候选问题都带 `owner`（哪位专家负责），报告页与 manifest 可据此追溯。
    候选不足 `min_q` 时抛 ValueError，由编排器决定是「不出报告」还是「数据驱动兜底」。
    """
    by_finding = {q["finding"]: q for q in QBANK}
    cand: List[Tuple[int, int, Dict[str, Any], Dict[str, Any]]] = []
    seen_f, seen_id = set(), set()
    for e in roster:
        rid = str(e.get("role") or "")
        for mkey in (e.get("methods") or []):
            q = by_finding.get(mkey)
            if not q or q["finding"] in seen_f or q["id"] in seen_id:
                continue
            seen_f.add(q["finding"])
            seen_id.add(q["id"])
            cand.append((_intent_match(intent, q), int(q["priority"]), q, e))
    # 先按「和你的问题有多像」排，再按问题库优先级排。
    # 只按优先级排的后果：同一批专家面对「哪些品类在涨」和「经营诊断」会问出同一组问题。
    cand.sort(key=lambda x: (-x[0], x[1]))
    if len(cand) < min_q:
        raise ValueError(
            f"出场专家的可答问题只有 {len(cand)} 个（< {min_q}）："
            + "、".join(f"{e.get('role')}:{','.join(e.get('methods') or []) or '无方法'}"
                        for e in roster))

    # 选几问：始终问到 max_q（研究报告需要足够节数才过深度门禁），
    # 但**顺序**由意图决定——命中的问题排前面。
    # 这样「哪些品类在涨」与「经营诊断」用同一批方法，却从不同的问题开始讲。
    hit = [x for x in cand if x[0] > 0]
    rest = [x for x in cand if x[0] == 0]
    picked = (hit + rest)[:max_q]
    if len(picked) < min_q:
        picked = cand[:min_q]
    qs = []
    for i, (_, _, q, e) in enumerate(picked, 1):
        qs.append({
            "id": f"dq{i}",
            "text": q["text"],
            "decision": decision or q["decision"],
            "finding": q["finding"],
            "comparison": dict(q["comparison"]),
            "falsifier": q["falsifier"],
            "chart": {"type": CHART_POLICY[q["comparison"]["kind"]][0]},
            "owner": str(e.get("role") or ""),
            "owner_name": str(e.get("name") or ""),
        })
    return {
        "schema": SCHEMA,
        "intent": intent,
        "decision": decision or "读完这份报告要做的取舍",
        "audience": audience,
        "data_cutoff": "",
        "auto": True,
        "drafted_from": "roster",
        "roster": [str(e.get("role") or "") for e in roster],
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "questions": qs,
    }


# --------------------------------------------------------------------------- #
# 校验
# --------------------------------------------------------------------------- #
def validate(contract: Dict[str, Any]) -> Dict[str, Any]:
    errs: List[str] = []
    if contract.get("schema") != SCHEMA:
        errs.append(f"schema 必须是 {SCHEMA}")
    qs = contract.get("questions") or []
    if not (MIN_Q <= len(qs) <= MAX_Q):
        errs.append(f"问题数必须在 {MIN_Q}–{MAX_Q}，当前 {len(qs)}")
    if not str(contract.get("decision") or "").strip():
        errs.append("缺 decision：这份报告要支持哪个决定")
    seen_f, seen_id = set(), set()
    for q in qs:
        qid = str(q.get("id") or "?")
        if qid in seen_id:
            errs.append(f"{qid}: 问题 id 重复")
        seen_id.add(qid)
        for k in ("text", "decision", "falsifier", "finding"):
            if not str(q.get(k) or "").strip():
                errs.append(f"{qid}: 缺 {k}")
        fk = str(q.get("finding") or "")
        if fk in seen_f:
            errs.append(f"{qid}: finding {fk} 重复（两个问题问同一件事）")
        seen_f.add(fk)
        comp = q.get("comparison") or {}
        kind = str(comp.get("kind") or "")
        if kind not in CHART_POLICY:
            errs.append(f"{qid}: 未知对照类型 {kind or '空'}")
        for k in ("left", "right", "metric"):
            if not str(comp.get(k) or "").strip():
                errs.append(f"{qid}: 对照缺 {k}")
        ctype = str((q.get("chart") or {}).get("type") or "")
        if not chart_capabilities.has_chart(ctype):
            errs.append(f"{qid}: 图型 {ctype or '空'} 不在 48 型注册表")
        elif kind in CHART_POLICY and ctype not in CHART_POLICY[kind]:
            errs.append(f"{qid}: 图型 {ctype} 不能表达 {kind}（允许 {CHART_POLICY[kind]}）")
    return {"ok": not errs, "errors": errs, "questions": len(qs)}


# --------------------------------------------------------------------------- #
# 图表：把「对照」变成「可验证的图」
# --------------------------------------------------------------------------- #
def _payload_kinds(chart: Dict[str, Any]) -> Tuple[str, ...]:
    out = []
    if chart.get("bars") or chart.get("vbars"):
        out.append("bars")
    if chart.get("items"):
        out.append("items")
    if chart.get("categories") and chart.get("series"):
        out.append("groups")
    if chart.get("points") or (chart.get("x") and chart.get("y")):
        out.append("points")
    return tuple(out)


def _adapt(chart: Dict[str, Any], ctype: str) -> Optional[Dict[str, Any]]:
    """把方法给的 payload 适配到目标图型；不适配返回 None（不硬画）。

    v11 / P4：图型从 17 型扩到 40+ 型之后，这里必须把 payload 的键名也一起转，
    否则「适配成功」只是把 type 改了、数据还挂在旧键上，渲染时才炸（vbar 读 vbars）。
    """
    c = dict(chart)
    bars = c.get("bars") or c.get("vbars")
    if ctype in ("hbar", "vbar"):
        if bars:
            seq = [{"label": b["label"], "value": b["value"]} for b in bars
                   if b.get("value") is not None]
            if not seq:
                return None
            if ctype == "hbar":
                c["bars"] = seq
                c.pop("vbars", None)
            else:
                c["vbars"] = seq
                c.pop("bars", None)
            return c
        if c.get("items"):
            seq = [{"label": i["label"], "value": i["value"]}
                   for i in c["items"] if i.get("value") is not None]
            if not seq:
                return None
            if ctype == "hbar":
                c["bars"] = seq
            else:
                c["vbars"] = seq
            return c
        return None
    if ctype in ("dot", "lollipop", "pareto"):
        if c.get("items"):
            return c
        if bars:
            c["items"] = [{"label": b["label"], "value": b["value"]}
                          for b in bars if b.get("value") is not None]
            return c
        return None
    if ctype == "grouped_bar":
        return c if (c.get("categories") and c.get("series")) else None
    if ctype == "dumbbell":
        items = c.get("items") or []
        return c if any(i.get("a") is not None and i.get("b") is not None
                        for i in items) else None
    if ctype == "slope":
        # 渲染器要 items（每项含 a/b 或两期值）；只有 series 的 payload 属于组长图，不适配
        items = c.get("items") or []
        return c if any(isinstance(i, dict) and
                        (i.get("a") is not None or i.get("b") is not None)
                        for i in items) else None
    if ctype in ("line", "area", "streamgraph"):
        return c if ("points" in c or ("x" in c and "y" in c)
                     or c.get("series")) else None
    if ctype in ("bullet", "target_band"):
        # 需要目标线；没有就不硬画，交给调用方回退
        return c if (bars and c.get("ref")) else None
    # 其余图型（rose / radar / candlestick / gantt / sankey …）的 payload 契约各不相同，
    # 这里不猜：返 None 让选型继续往下走，最后由调用方记缺口。
    # 方法自己产出这些类型时会走「native 已在 allowed 里就直接用」那条路，不受影响。
    return None


def choose_chart(chart: Optional[Dict[str, Any]], q: Dict[str, Any]) -> Dict[str, Any]:
    """按对照类型选图，并补 chart_spec 要求的证明字段。

    选型规则（v11 / P4 修正）：
        1. 方法已经给的图型若在该关系的 allowed 列表里 → **直接用**，不重选。
           方法最了解自己的 payload 形状，硬换成列表里第一个常常要改 payload 键名，
           是「适配成功、渲染失败」的来源。
        2. 否则按 allowed 顺序找第一个能适配的。
        3. 一个都不适配 → type="" + unsupported，交给调用方记缺口（不硬画）。
    """
    kind = str((q.get("comparison") or {}).get("kind") or "")
    policy = CHART_POLICY.get(kind) or ["hbar"]
    base = dict(chart or {})
    chosen, fallback = "", False
    native = str(base.get("type") or "")
    if native and native in policy:
        chosen = native
    else:
        for ctype in policy:
            if not chart_capabilities.has_chart(ctype):
                continue
            got = _adapt(base, ctype) if base else None
            if got:
                base, chosen = got, ctype
                break
    if not chosen:
        # 没有一种允许的图型能表达这份 payload：不硬画，交给调用方记缺口
        base["type"] = ""
        base["policy"] = {"comparison": kind, "allowed": policy, "chosen": "",
                          "fallback": True, "unsupported": True}
        return base
    # fallback = 「选型时改过图型」：方法没给类型、或给的类型不在 allowed 里，都算。
    # 留痕是为了审计：报告里每张图都能回答「为什么用这个图型，而不是方法原本那个」。
    if native != chosen:
        fallback = True
    base["type"] = chosen
    base["policy"] = {"comparison": kind, "allowed": policy,
                      "chosen": chosen, "native": native, "fallback": fallback}
    base.setdefault("title", q.get("text") or "")
    base.setdefault("unit_meta", (q.get("comparison") or {}).get("unit") or "")
    base.setdefault("source", "证据包（见记录层）")
    if not str(base.get("unit_meta") or "").strip():
        base["unit_meta"] = "同口径单位"
    if not str(base.get("source") or "").strip():
        base["source"] = "证据包（见记录层）"
    base["claim_to_prove"] = base.get("claim_to_prove") or q.get("text") or ""
    base["required_annotations"] = base.get("required_annotations") or {
        "compare_two_points": ["两端值", "差值"],
        "change_over_time": ["起止值", "拐点"],
        "vs_threshold": ["实测值", "阈值线"],
        "composition": ["合计", "占比"],
    }.get(kind, ["最大值", "最小值", "零线"])
    base["fail_if_missing"] = base.get("fail_if_missing") or \
        "缺 refs / 来源 / 单位时不画，改为文字说明缺口"
    base["encoding"] = base.get("encoding") or {
        "x": (q.get("comparison") or {}).get("left"),
        "y": (q.get("comparison") or {}).get("metric"),
        "series": (q.get("comparison") or {}).get("right"),
        "mark": chosen,
    }
    return base


def synth_from_table(table: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """没有图但有表时，从表格合成一个可画的最小数据集（不编数：只取表里已有的数）。"""
    if not table:
        return None
    rows = table.get("rows") or []
    items = []
    for row in rows:
        try:
            label = str(row[0]["text"])
        except (KeyError, IndexError, TypeError):
            continue
        val = None
        for cell in row[1:]:
            m = re.search(r"[-+]?\d+(?:\.\d+)?", str(cell.get("text") if isinstance(cell, dict) else cell))
            if m:
                val = float(m.group())
                break
        if val is not None:
            items.append({"label": label, "value": val})
    if len(items) < 3:
        return None
    return {"items": items, "title": table.get("caption") or ""}


def chart_contract_ok(chart: Dict[str, Any]) -> Dict[str, Any]:
    errs = chart_spec.errors(chart)
    return {"ok": not errs, "errors": errs, "type": chart.get("type")}


# --------------------------------------------------------------------------- #
# 绑定：declared vs answered
# --------------------------------------------------------------------------- #
def bind(contract: Dict[str, Any], findings: Dict[str, Any],
         plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """诚实覆盖率：开工前问的问题里，报告真正答了几个。"""
    skipped = {m.get("key"): (m.get("missing") or [])
               for m in ((plan or {}).get("skipped") or [])}
    rows, unanswered = [], []
    for q in contract.get("questions") or []:
        fk = str(q.get("finding") or "")
        f = findings.get(fk)
        ok = f is not None
        rows.append({"id": q.get("id"), "question": q.get("text"),
                     "finding": fk, "answered": ok})
        if not ok:
            why = "blocked_role" if not skipped.get(fk) else "no_data"
            if fk not in skipped and plan is not None:
                why = "no_finding"
            unanswered.append({"id": q.get("id"), "question": q.get("text"),
                               "finding": fk, "reason": why,
                               "missing": skipped.get(fk) or []})
    declared = len(rows)
    answered = sum(1 for r in rows if r["answered"])
    return {
        "schema": "dsh.decision.binding/v1",
        "auto": bool(contract.get("auto")),
        "declared": declared,
        "answered": answered,
        "binding": round(answered / declared, 3) if declared else 0.0,
        "rows": rows,
        "unanswered": unanswered,
        "verdict": "BOUND" if declared and answered == declared else "PARTIAL",
    }


# --------------------------------------------------------------------------- #
# 落盘
# --------------------------------------------------------------------------- #
def load(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path: str | Path, contract: Dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="decision")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="从数据能力起草决策契约（auto=true）")
    d.add_argument("--intent", required=True)
    d.add_argument("--dir", required=True)
    d.add_argument("--out", required=True)
    c = sub.add_parser("check", help="校验一份决策契约")
    c.add_argument("--decision", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "draft":
        from core.data import analysis_desk
        from core import methods, analysis_methods
        desk = analysis_desk.scan(a.dir)
        views = analysis_methods.build_views(desk)
        prof = analysis_desk.profile(desk)
        plan = methods.plan(desk, views, prof, "analysis")
        avail = [m["key"] for m in plan.get("mounted") or []]
        ctr = draft(a.intent, avail)
        p = save(a.out, ctr)
        print(f"drafted {len(ctr['questions'])} questions -> {p}")
        print(json.dumps(validate(ctr), ensure_ascii=False))
        return 0
    ctr = load(a.decision)
    r = validate(ctr)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
