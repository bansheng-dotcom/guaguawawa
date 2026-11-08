# -*- coding: utf-8 -*-
"""T8 内嵌案例：确定性案例（本仓库即可复算）。

案例一 month-end-close（月结对账）：
  现象 = 期末现金与子账不符。先跑 financial.recon 对账（金额/时点/单边），
  再跑 financial.rollforward 平衡门禁，最后跑 cfo.healthcheck 三表勾稽。

案例二 kyc-onboarding（KYC 尽调）：
  现象 = 高风险申请人材料不全。先跑 risk.kyc 规则引擎评级，
  再跑 risk.aml 关联交易监测。

语义层：服务端语义表（语义层驱动 Gherkin 的世界观）。
"""
from __future__ import annotations

from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = [
    {
        "case": "month-end-close",
        "story": "月结对账",
        "phenomenon": "期末现金与子账明细不符，须先归因再调平",
        "scenario": ("给定 GL 现金分录与银行子账分录 "
                     "当我对账 financial.recon "
                     "则匹配率 50% 且产生 3 条破差 "
                     "当我校验 rollforward "
                     "则现金账户不平差 500 "
                     "当我校验三表 healthcheck "
                     "则现金勾稽差同为 500（同一根因）"),
        "steps": [
            {"skill": "financial", "action": "recon",
             "expect": {"matched_pct": 0.5, "break_count": 3}},
            {"skill": "financial", "action": "rollforward",
             "expect": {"balanced": 1, "broken.0.diff": -500.0}},
            {"skill": "cfo", "action": "healthcheck",
             "expect": {"ok": False}},
        ],
        "fact": {
            "asserts": [
                "matched_pct == 0.5（6 键全外连接：3 匹配 + 1 金额破差"
                " + 1 时点破差 + 1 子账单边）",
                "rollforward 现金账户差 −500（GL 漏记一笔 500 付款）",
                "三表现金勾稽差 = −500（同根因，不是新问题）",
                "两处差异同源 → 归因为 GL 漏记付款",
            ],
            "cartridges": {
                "recon": {
                    "gl_entries": [
                        {"key": "t1", "amount": 10000.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t2", "amount": 2500.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t3", "amount": 800.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t5", "amount": 4100.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t6", "amount": 1200.0,
                         "quantity": 1, "posting_date": "2026-09-28"},
                    ],
                    "subledger_entries": [
                        {"key": "t1", "amount": 10000.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t2", "amount": 2500.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t3", "amount": 760.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t4", "amount": 3300.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t5", "amount": 4100.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                        {"key": "t6", "amount": 1200.0,
                         "quantity": 1, "posting_date": "2026-09-30"},
                    ],
                },
                "rollforward": {
                    "accounts": [
                        {"account": "cash",
                         "opening": 50000.0, "additions": 12500.0,
                         "accruals": 0.0, "reversals": 0.0,
                         "payments": 3000.0, "reclass": 0.0, "fx": 0.0,
                         "closing": 60000.0},
                        {"account": "accrued_liabilities",
                         "opening": 2400.0, "additions": 0.0,
                         "accruals": 0.0, "reversals": 0.0,
                         "payments": 0.0, "reclass": 0.0, "fx": 0.0,
                         "closing": 2400.0},
                    ],
                },
                "healthcheck": {
                    "balance_sheet": {"assets": 160000.0,
                                      "liabilities": 60000.0,
                                      "equity": 100000.0},
                    "cash_flow": {"cash_begin": 50000.0,
                                  "operating": 9500.0,
                                  "investing": 0.0,
                                  "financing": 0.0,
                                  "cash_end": 60000.0},
                    "income_statement": {"revenue": 12500.0,
                                         "cogs": 3000.0,
                                         "gross_profit": 9500.0},
                },
            },
        },
    },
    {
        "case": "kyc-onboarding",
        "story": "KYC 尽调",
        "phenomenon": "PEP 关联申请人材料不全，须评级并给处置建议",
        "scenario": ("给定申请人风险因子与缺失文档 "
                     "当我评级 risk.kyc "
                     "则风险分 5（high）且处置为 request-docs 或 escalate-edd "
                     "当我监测关联流水 risk.aml "
                     "则同日拆分现金触发结构化红旗"),
        "steps": [
            {"skill": "risk", "action": "kyc",
             "expect": {"risk_score": 5, "rating": "high",
                        "disposition": ["request-docs", "escalate-edd"]}},
            {"skill": "risk", "action": "aml",
             "expect": {"alerts.0.type": "structuring"}},
        ],
        "fact": {
            "asserts": [
                "风险分 = jurisdiction 1 + pep 3 + sof 1 = 5 → high",
                "PEP 因子 3 ≥ 3 触发升级规则（处置不为 clear）",
                "identity/tax_id 缺失 → 处置至少 request-docs",
                "同日 2 笔现金（5,500 + 4,200 = 9,700 ≥ 9,000）"
                "且单笔 < 10,000 → 结构化拆分红旗",
                "approved == False（本 agent 永不直接批准开户）",
            ],
            "cartridges": {
                "kyc": {
                    "applicant": {
                        "risk_factors": {"jurisdiction": 1, "pep": 3,
                                         "source_of_funds": 1},
                        "documents": {"identity": "received",
                                      "address": "received",
                                      "tax_id": "missing",
                                      "sof": "missing"},
                        "beneficial_owners": [
                            {"name": "张三", "ownership_pct": 60,
                             "verified": True},
                        ],
                    },
                },
                "aml": {
                    "transactions": [
                        {"id": "x1", "date": "2026-10-05", "type": "cash",
                         "amount": 5500.0},
                        {"id": "x2", "date": "2026-10-05", "type": "cash",
                         "amount": 4200.0},
                    ],
                },
            },
        },
    },
]

SEMANTIC_LAYER = {
    "entity": {
        "GL 分录": "总账现金科目的日记账行（key/amount/posting_date）",
        "子账分录": "银行对账单明细行（同构）",
        "roll-forward": "资产负债表账户的期初→期末滚动调节表",
        "三表": "资产负债表 / 现金流量表 / 利润表的勾稽恒等式",
        "KYC 申请人": "开户尽调对象（风险因子/文档/受益所有人）",
        "交易": "AML 监测流水（type=cash 触发 CTR/结构化规则）",
    },
    "metric": {
        "matched_pct": "对账匹配率 = matched / 全外连接键数",
        "runway": "现金 / 月净烧钱（月度模拟）",
        "burn multiple": "累计净烧钱 / 净新增 ARR",
        "LTV:CAC": "ARPA×GM/churn ÷ CAC",
        "风险分": "六因子封顶加总（jurisdiction/type/opacity/pep/"
                 "sanctions/sof）",
        "RMD": "上年 12/31 余额 ÷ Uniform Lifetime Table 除数",
    },
    "enum": {
        "break 桶": ["matched", "amount_break", "quantity_break",
                     "timing_break", "gl_only", "subledger_only"],
        "KYC 处置": ["clear", "request-docs", "escalate-edd",
                     "decline-recommend"],
        "AI 风险级": ["prohibited", "high", "limited", "minimal"],
        "留存层": ["six_years", "three_years", "lifetime"],
    },
    "edge": {
        "月结顺序": "recon → rollforward → healthcheck → variance",
        "KYC 顺序": "kyc 评级 → aml 监测 → 人工批准（不在本 agent）",
        "处置门": "升级规则命中 → 处置永不等于 clear",
    },
    "invariant": [
        "roll-forward：X+A+B−C−D+E+F=Y，不得 plug",
        "资产 = 负债 + 权益；期末现金 = 期初 + 三活动净额",
        "KYC 永不直接批准（approved 恒 False）",
        "本 agent 永不出具持牌意见（正式法律/审计意见）",
    ],
}


def case_by_name(name: str) -> Dict[str, Any]:
    for cs in CASES:
        if cs["case"] == name:
            return cs
    raise KeyError(name)


if __name__ == "__main__":
    import json

    print(json.dumps({"cases": [c["case"] for c in CASES],
                      "semantic_layer": SEMANTIC_LAYER},
                     ensure_ascii=False, indent=2))
