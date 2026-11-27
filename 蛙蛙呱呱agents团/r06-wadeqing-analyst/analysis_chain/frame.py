# -*- coding: utf-8 -*-
"""第 1 段 frame：把业务问题变成 3–5 个可证伪假设 + 决策用途。

方案 §13.4 的硬要求：
  - 每个假设必须能被数据推翻（falsifiable_if 带阈值）；
  - 每个假设必须对应一个决策（成立做什么 / 不成立做什么）；
  - 维度必须 MECE（互斥且合起来覆盖指标恒等式）；
  - 数据还没看：全部假设 status=unverified，禁止写“已确认”。

不做的事：不做数据计算、不下结论；那是 plan 之后的事。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import ck, gate, now_iso

DOMAINS: Dict[str, Dict[str, Any]] = {
    "profit": {
        "metric": "profit",
        "identity": ["收入", "成本"],
        "dimensions": ["channel", "category"],
        "hypotheses": [
            {"driver": "price", "label": "价格/折扣",
             "statement": "折扣或成交价变化解释了本期利润变化的主要部分",
             "falsifiable_if": "若折扣率同比变化 <2 个百分点，或价格效应对利润变化的贡献 <20%，则推翻",
             "test": "decomposition", "component": "收入",
             "decision_if_true": "收紧高折扣渠道的促销预算并设折扣上限",
             "decision_if_false": "维持价格策略，把排查预算转向上游成本与产品结构",
             "role": "r12"},
            {"driver": "volume", "label": "销量",
             "statement": "销量下滑（而非价格）是本期利润变化的主要驱动",
             "falsifiable_if": "若销量同比变化 >-2%，或销量效应对利润变化的贡献 <20%，则推翻",
             "test": "decomposition", "component": "收入",
             "decision_if_true": "优先恢复流量与转化，而非降价换量",
             "decision_if_false": "销量不是主因，停止在获客端加投",
             "role": "r12"},
            {"driver": "unit_cost", "label": "单位成本",
             "statement": "单位成本（采购/履约/退货）上升解释了利润变化的主要部分",
             "falsifiable_if": "若单位成本同比变化 <1%，或成本效应对利润变化的贡献 <20%，则推翻",
             "test": "decomposition", "component": "成本",
             "decision_if_true": "启动供应商比价与履约链路降本",
             "decision_if_false": "成本不是主因，暂缓采购重谈",
             "role": "r15"},
            {"driver": "mix", "label": "产品结构",
             "statement": "高毛利品类占比下降（结构变化）解释了利润变化的主要部分",
             "falsifiable_if": "若高毛利品类收入占比变化 <2 个百分点，或结构效应对利润变化的贡献 <20%，则推翻",
             "test": "attribution", "component": "收入",
             "decision_if_true": "调整货盘与陈列，恢复高毛利品类权重",
             "decision_if_false": "结构稳定，不调整货盘",
             "role": "r07"},
            {"driver": "channel_mix", "label": "渠道结构",
             "statement": "低毛利渠道占比上升解释了利润变化的主要部分",
             "falsifiable_if": "若各渠道毛利率差异 <3 个百分点，或渠道结构效应对利润变化的贡献 <20%，则推翻",
             "test": "attribution", "component": "收入",
             "decision_if_true": "重配渠道预算，给高毛利渠道加权重",
             "decision_if_false": "渠道结构不是主因，维持投放配比",
             "role": "r12"},
        ],
    },
    "revenue": {
        "metric": "revenue",
        "identity": ["量", "价"],
        "dimensions": ["channel", "category"],
        "hypotheses": [
            {"driver": "traffic", "label": "流量",
             "statement": "访问/曝光量变化解释了收入变化的主要部分",
             "falsifiable_if": "若流量同比变化 <3%，或流量效应对收入变化的贡献 <20%，则推翻",
             "test": "trend_analysis", "component": "量",
             "decision_if_true": "优先恢复流量入口与投放",
             "decision_if_false": "流量不是主因，转向转化与客单",
             "role": "r12"},
            {"driver": "conversion", "label": "转化率",
             "statement": "转化率变化解释了收入变化的主要部分",
             "falsifiable_if": "若转化率同比变化 <0.5 个百分点，或转化效应对收入变化的贡献 <20%，则推翻",
             "test": "decomposition", "component": "量",
             "decision_if_true": "排查下单流程与价格门槛，做转化专项",
             "decision_if_false": "转化稳定，不投入转化优化",
             "role": "r07"},
            {"driver": "aov", "label": "客单价",
             "statement": "客单价（件单价 × 件数）变化解释了收入变化的主要部分",
             "falsifiable_if": "若客单价同比变化 <2%，或客单价效应对收入变化的贡献 <20%，则推翻",
             "test": "decomposition", "component": "价",
             "decision_if_true": "调整组合装与满减门槛",
             "decision_if_false": "客单稳定，不做价格结构动作",
             "role": "r07"},
            {"driver": "mix", "label": "品类结构",
             "statement": "高单价品类占比变化（结构）解释了收入变化的主要部分",
             "falsifiable_if": "若高单价品类占比变化 <2 个百分点，或结构效应对收入变化的贡献 <20%，则推翻",
             "test": "attribution", "component": "价",
             "decision_if_true": "调整主推品类与货盘宽度",
             "decision_if_false": "品类结构稳定，不调货盘",
             "role": "r07"},
            {"driver": "retention", "label": "复购/留存",
             "statement": "老客复购下降解释了收入变化的主要部分",
             "falsifiable_if": "若复购率同比变化 <1 个百分点，或复购效应对收入变化的贡献 <20%，则推翻",
             "test": "risk_mining", "component": "量",
             "decision_if_true": "启动老客召回与会员权益",
             "decision_if_false": "复购稳定，把预算留给拉新",
             "role": "r13"},
        ],
    },
    "churn": {
        "metric": "churn_rate",
        "identity": ["新客", "老客"],
        "dimensions": ["plan", "onboarding"],
        "hypotheses": [
            {"driver": "onboarding", "label": "激活/上手",
             "statement": "未完成关键激活动作的客户流失率显著更高，且解释了整体流失变化",
             "falsifiable_if": "若已完成与未完成激活组的流失率差 <3 个百分点，或该因素贡献 <20%，则推翻",
             "test": "risk_mining", "component": "新客",
             "decision_if_true": "把激活里程碑纳入客户成功 SOP 并设 7 日干预",
             "decision_if_false": "激活不是主因，转向价值实现与价格",
             "role": "r13"},
            {"driver": "value", "label": "价值实现",
             "statement": "低频使用/未达成价值指标的客户流失率显著更高",
             "falsifiable_if": "若高低使用组的流失率差 <3 个百分点，或使用度贡献 <20%，则推翻",
             "test": "decomposition", "component": "老客",
             "decision_if_true": "做使用度干预与成功案例共创",
             "decision_if_false": "使用度不是主因，停止泛化运营动作",
             "role": "r13"},
            {"driver": "price", "label": "价格敏感",
             "statement": "续费涨价或折扣退出解释了流失上升的主要部分",
             "falsifiable_if": "若涨价组与未涨价组流失率差 <2 个百分点，或价格贡献 <20%，则推翻",
             "test": "decomposition", "component": "老客",
             "decision_if_true": "对价格敏感客群设过渡价或降档方案",
             "decision_if_false": "价格不是主因，不调整定价",
             "role": "r03"},
            {"driver": "support", "label": "服务体验",
             "statement": "高工单量/低满意度客户的流失率显著更高",
             "falsifiable_if": "若高工单组与低工单组流失率差 <2 个百分点，或服务贡献 <20%，则推翻",
             "test": "risk_mining", "component": "老客",
             "decision_if_true": "对高工单客户做专属跟进与根因整改",
             "decision_if_false": "服务不是主因，不扩客服编制",
             "role": "r13"},
            {"driver": "competitor", "label": "竞争替代",
             "statement": "竞品替代（主动流失原因）解释了流失上升的主要部分",
             "falsifiable_if": "若主动流失中“竞品替代”占比 <15%，或该原因贡献 <20%，则推翻",
             "test": "trend_analysis", "component": "老客",
             "decision_if_true": "做竞品对标与差异化权益",
             "decision_if_false": "竞品不是主因，回到内部体验",
             "role": "r05"},
        ],
    },
    "conversion": {
        "metric": "conversion_rate",
        "identity": ["流量", "流程"],
        "dimensions": ["channel", "device"],
        "hypotheses": [
            {"driver": "traffic_quality", "label": "流量质量",
             "statement": "低意图流量占比上升解释了转化率下降的主要部分",
             "falsifiable_if": "若高/低意图渠道转化率差 <1 个百分点，或结构贡献 <20%，则推翻",
             "test": "attribution", "component": "流量",
             "decision_if_true": "收紧低意图渠道的出价与定向",
             "decision_if_false": "流量质量不是主因，转向流程摩擦",
             "role": "r12"},
            {"driver": "funnel_friction", "label": "流程摩擦",
             "statement": "关键步骤流失率上升解释了转化率下降的主要部分",
             "falsifiable_if": "若关键步骤流失率变化 <1 个百分点，或该步骤贡献 <20%，则推翻",
             "test": "decomposition", "component": "流程",
             "decision_if_true": "对流失最大的步骤做 A/B 优化",
             "decision_if_false": "流程稳定，不投入改版",
             "role": "r07"},
            {"driver": "price", "label": "价格/促销",
             "statement": "促销退出或价格上调解释了转化率下降的主要部分",
             "falsifiable_if": "若价格变化组与对照组的转化率差 <0.5 个百分点，或价格贡献 <20%，则推翻",
             "test": "decomposition", "component": "流程",
             "decision_if_true": "设阶段性优惠或降低首单门槛",
             "decision_if_false": "价格不是主因，不恢复促销",
             "role": "r12"},
            {"driver": "trust", "label": "信任要素",
             "statement": "评价/保障/支付信任要素缺失解释了转化率下降的主要部分",
             "falsifiable_if": "若有信任要素与无信任要素页面的转化率差 <0.5 个百分点，或贡献 <20%，则推翻",
             "test": "risk_mining", "component": "流程",
             "decision_if_true": "补齐评价、保障与退款承诺",
             "decision_if_false": "信任不是主因，不改页面信任区",
             "role": "r07"},
            {"driver": "supply", "label": "库存/供给",
             "statement": "缺货与延迟发货解释了转化率下降的主要部分",
             "falsifiable_if": "若缺货 SKU 占比变化 <2 个百分点，或缺货贡献 <20%，则推翻",
             "test": "risk_mining", "component": "流程",
             "decision_if_true": "优先补货并下线缺货流量",
             "decision_if_false": "供给不是主因，不调库存",
             "role": "r15"},
        ],
    },
    "growth": {
        "metric": "growth",
        "identity": ["供给", "分发"],
        "dimensions": ["platform", "account"],
        "hypotheses": [
            {"driver": "content", "label": "内容供给",
             "statement": "内容发布量与质量变化解释了增长变化的主要部分",
             "falsifiable_if": "若发布量同比变化 <10%，或内容贡献 <20%，则推翻",
             "test": "trend_analysis", "component": "供给",
             "decision_if_true": "恢复更新频率并做选题复盘",
             "decision_if_false": "供给不是主因，转向分发与转化",
             "role": "r11"},
            {"driver": "distribution", "label": "分发/投放",
             "statement": "分发渠道结构变化解释了增长变化的主要部分",
             "falsifiable_if": "若单渠道占比变化 <5 个百分点，或渠道结构贡献 <20%，则推翻",
             "test": "attribution", "component": "分发",
             "decision_if_true": "重配渠道预算并复盘投放素材",
             "decision_if_false": "渠道结构稳定，不调预算",
             "role": "r12"},
            {"driver": "algorithm", "label": "平台算法",
             "statement": "平台推荐量变化解释了增长变化的主要部分",
             "falsifiable_if": "若推荐曝光同比变化 <10%，或推荐贡献 <20%，则推翻",
             "test": "trend_analysis", "component": "分发",
             "decision_if_true": "按平台规则调整内容形态与发布时间",
             "decision_if_false": "算法不是主因，回到内容与转化",
             "role": "r12"},
            {"driver": "conversion_path", "label": "转化路径",
             "statement": "主页/私域承接转化变化解释了增长变化的主要部分",
             "falsifiable_if": "若加微/下单转化率变化 <0.5 个百分点，或转化贡献 <20%，则推翻",
             "test": "decomposition", "component": "分发",
             "decision_if_true": "优化主页承接与私域话术",
             "decision_if_false": "承接稳定，不改路径",
             "role": "r11"},
            {"driver": "retention", "label": "粉丝留存",
             "statement": "取关/沉默上升解释了增长变化的主要部分",
             "falsifiable_if": "若取关率变化 <0.3 个百分点，或留存贡献 <20%，则推翻",
             "test": "risk_mining", "component": "供给",
             "decision_if_true": "做粉丝分层运营与内容节奏校准",
             "decision_if_false": "留存稳定，把预算留给拉新",
             "role": "r13"},
        ],
    },
    "generic": {
        "metric": "metric",
        "identity": ["量", "价"],
        "dimensions": ["segment", "channel"],
        "hypotheses": [
            {"driver": "volume", "label": "量",
             "statement": "量的变化解释了指标变化的主要部分",
             "falsifiable_if": "若量的贡献 <20%，则推翻",
             "test": "decomposition", "component": "量",
             "decision_if_true": "优先做量的恢复", "decision_if_false": "转向价与结构",
             "role": "r12"},
            {"driver": "price", "label": "价",
             "statement": "价的变化解释了指标变化的主要部分",
             "falsifiable_if": "若价的贡献 <20%，则推翻",
             "test": "decomposition", "component": "价",
             "decision_if_true": "调整价格与促销", "decision_if_false": "价格不是主因",
             "role": "r12"},
            {"driver": "mix", "label": "结构",
             "statement": "结构（组合）变化解释了指标变化的主要部分",
             "falsifiable_if": "若结构贡献 <20%，则推翻",
             "test": "attribution", "component": "量",
             "decision_if_true": "调整组合与资源配比", "decision_if_false": "结构稳定",
             "role": "r07"},
            {"driver": "efficiency", "label": "效率",
             "statement": "单位效率变化解释了指标变化的主要部分",
             "falsifiable_if": "若效率贡献 <20%，则推翻",
             "test": "decomposition", "component": "价",
             "decision_if_true": "做效率专项", "decision_if_false": "效率不是主因",
             "role": "r02"},
        ],
    },
}

_KEYWORDS = (
    ("churn", ("流失", "续费", "退订", "留存率", "churn")),
    ("conversion", ("转化", "漏斗", "加购", "下单率", "cvr")),
    ("growth", ("涨粉", "流量增长", "自媒", "粉丝", "播放量", "增长")),
    ("profit", ("利润", "毛利", "亏损", "成本", "盈利")),
    ("revenue", ("收入", "营收", "销售额", "gmv", "成交额")),
)


def classify(question: str, domain: Optional[str] = None) -> str:
    if domain:
        return domain if domain in DOMAINS else "generic"
    low = question.lower()
    for name, kws in _KEYWORDS:
        if any(k in low for k in kws):
            return name
    return "generic"


def build(question: str, decision_use: str = "", metric: str = "",
          dimensions: Optional[List[str]] = None, domain: Optional[str] = None,
          window: str = "近90天", min_impact_pct: float = 3.0) -> Dict[str, Any]:
    dom = classify(question, domain)
    profile = DOMAINS[dom]
    hyps: List[Dict[str, Any]] = []
    for i, h in enumerate(profile["hypotheses"], 1):
        hyps.append({
            "id": f"H{i}",
            "driver": h["driver"],
            "label": h["label"],
            "statement": h["statement"],
            "falsifiable_if": h["falsifiable_if"],
            "test": h["test"],
            "component": h["component"],
            "evidence_required": ["前后期同口径数据", "分段维度取值", "分母定义"],
            "decision_if_true": h["decision_if_true"],
            "decision_if_false": h["decision_if_false"],
            "owner_role": h["role"],
            "status": "unverified",
            "min_impact_pct": min_impact_pct,
        })
    dims = dimensions or list(profile["dimensions"])
    frame = {
        "artifact": "frame",
        "version": "1.0",
        "generated_at": now_iso(),
        "question": question.strip(),
        "decision_use": (decision_use or "判断本期指标变化的主因，并决定下一步资源投向").strip(),
        "domain": dom,
        "metric": (metric or profile["metric"]).strip(),
        "window": window,
        "dimensions": dims,
        "hypotheses": hyps,
        "mece": {
            "components": list(profile["identity"]),
            "dimensions": dims,
            "mutually_exclusive": len({h["driver"] for h in hyps}) == len(hyps),
            "collectively_exhaustive": set(h["component"] for h in hyps) >= set(profile["identity"]),
        },
        "decision_mapping": [
            {"hypothesis": h["id"], "role": h["owner_role"],
             "if_true": h["decision_if_true"], "if_false": h["decision_if_false"]}
            for h in hyps
        ],
        "evidence_status": "not_collected",
    }
    frame["gate"] = check(frame)
    return frame


def check(frame: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    hyps = frame.get("hypotheses") or []
    checks.append(ck(3 <= len(hyps) <= 5, f"假设数={len(hyps)}（要求 3–5）",
                     "hypotheses", "CRITICAL" if not 3 <= len(hyps) <= 5 else "OK"))
    ids = [h.get("id") for h in hyps]
    checks.append(ck(len(ids) == len(set(ids)), f"假设 ID 唯一（{len(set(ids))}）",
                     "hypotheses", "CRITICAL" if len(ids) != len(set(ids)) else "OK"))
    for h in hyps:
        hid = h.get("id", "?")
        checks.append(ck(bool(str(h.get("statement", "")).strip()),
                         f"{hid} 有假设陈述", "hypotheses",
                         "CRITICAL" if not str(h.get("statement", "")).strip() else "OK"))
        checks.append(ck(len(str(h.get("falsifiable_if", ""))) >= 8,
                         f"{hid} 可证伪条件非空", "falsifiability",
                         "CRITICAL" if len(str(h.get("falsifiable_if", ""))) < 8 else "OK"))
        checks.append(ck(bool(h.get("decision_if_true")) and bool(h.get("decision_if_false")),
                         f"{hid} 对应成立/不成立决策", "decision",
                         "CRITICAL" if not (h.get("decision_if_true") and h.get("decision_if_false")) else "OK"))
        checks.append(ck(bool(h.get("evidence_required")), f"{hid} 列出所需证据",
                         "evidence", "CRITICAL" if not h.get("evidence_required") else "OK"))
        checks.append(ck(str(h.get("driver", "")).lower() not in ("time", "时间", "日期", "趋势"),
                         f"{hid} 驱动不是“时间”", "causality",
                         "CRITICAL" if str(h.get("driver", "")).lower() in ("time", "时间", "日期", "趋势") else "OK"))
        checks.append(ck(h.get("status") == "unverified", f"{hid} 未看数前状态=unverified",
                         "preregistration", "HIGH" if h.get("status") != "unverified" else "OK"))
    mece = frame.get("mece") or {}
    checks.append(ck(bool(mece.get("mutually_exclusive")), "假设驱动互斥", "mece",
                     "HIGH" if not mece.get("mutually_exclusive") else "OK"))
    checks.append(ck(bool(mece.get("collectively_exhaustive")),
                     f"假设覆盖指标恒等式 {mece.get('components')}", "mece",
                     "CRITICAL" if not mece.get("collectively_exhaustive") else "OK"))
    dims = frame.get("dimensions") or []
    checks.append(ck(1 <= len(dims) <= 3 and len(set(dims)) == len(dims),
                     f"切分维度={dims}（1–3 且不重复）", "mece",
                     "CRITICAL" if not (1 <= len(dims) <= 3 and len(set(dims)) == len(dims)) else "OK"))
    checks.append(ck(bool(str(frame.get("question", "")).strip()), "业务问题非空",
                     "existence", "CRITICAL" if not str(frame.get("question", "")).strip() else "OK"))
    checks.append(ck(bool(str(frame.get("decision_use", "")).strip()), "写明决策用途",
                     "decision", "CRITICAL" if not str(frame.get("decision_use", "")).strip() else "OK"))
    checks.append(ck(bool(str(frame.get("metric", "")).strip()), "指标已指定",
                     "metric", "CRITICAL" if not str(frame.get("metric", "")).strip() else "OK"))
    return gate(checks, "frame")
