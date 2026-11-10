# -*- coding: utf-8 -*-
"""engines/reflexive_healer.py - [L03] 自愈反思层：客户成功红线审判与反思自愈引擎。

对标开源标杆：
- Reflexion 闭环反思自纠架构 (Stars > 40k)
- Critic-Agent 对抗与红线安全防御 (Stars > 35k)

核心职责：
1. 拦截越权边界（严禁跨界处理支付退款，移交 R14；严禁未经授权免除账单与私自承诺超规赔偿）；
2. 拦截双门槛违规（未满足健康分及风险分底线时严禁放行续约）；
3. 闭环就地自愈（自愈缺失的客户档案字段、自动规范承诺三件套、标准化脏别名）。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class ReflexiveHealer:
    """客户成功安全红线拦截与反思自愈引擎。"""

    # 严禁红线关键词匹配
    PAYMENT_REDLINES = [
        "退款", "打款", "提现", "退费", "减免费用", "免除账单", "开具发票", "支付网关", "结算账户"
    ]
    UNAUTHORIZED_PROMISES = [
        "私下承诺", "私自承诺", "口头答应免单", "无条件赔偿", "兜底全额赔付", "承诺永久免费"
    ]

    def __init__(self):
        pass

    def check_redlines(self, action_or_text: str) -> Dict[str, Any]:
        """红线审判：检测越权及合规红线行为，命中直接抛出异常或返回阻断信息。"""
        text = str(action_or_text)

        # 1. 支付与退款边界检查 (移交 R14)
        for kw in self.PAYMENT_REDLINES:
            if kw in text:
                raise ValueError(
                    f"[REDLINE BLOCKED] 触犯角色边界：检测到支付/退款/发票相关操作 '{kw}'。"
                    f"R13 仅负责客户关系与续约健康，支付履约与资金退付请移交 R14 (蛙交易 · 商业化与支付官)。"
                )

        # 2. 越权承诺与免单检查
        for kw in self.UNAUTHORIZED_PROMISES:
            if kw in text:
                raise ValueError(
                    f"[REDLINE BLOCKED] 触犯客户承诺红线：检测到未授权的违规承诺 '{kw}'。"
                    f"严禁在未经过 R01/R03 审批的情况下私自向客户承诺免单或兜底赔偿。"
                )

        return {"status": "passed", "action": action_or_text, "blocked": False}

    def evaluate_renewal_gate(self, health_score: float, risk_score: float) -> Tuple[bool, str]:
        """双门槛续约准入校验。
        
        标准：
        - health_score >= 70
        - risk_score <= 40
        """
        h_ok = health_score >= 70.0
        r_ok = risk_score <= 40.0

        if h_ok and r_ok:
            return True, "双门槛完全达标：可安全推进续约商务流程。"
        elif not h_ok and not r_ok:
            return False, f"双门槛严重破损：健康分 {health_score} < 70 且 风险分 {risk_score} > 40，严禁列入续约候选，必须转入救亡清单。"
        elif not h_ok:
            return False, f"健康分门槛破损：健康分 {health_score} < 70，需专项排查使用度与产品质量。"
        else:
            return False, f"风险分门槛超标：风险分 {risk_score} > 40，存在未闭环高危工单或决策层异动。"

    def heal_client_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """自愈不完整或带脏别名的客户档案。"""
        healed = dict(record)
        heals_applied = []

        # 1. 字段别名映射自愈
        alias_map = {
            "name": "company_name",
            "client": "company_name",
            "nps_score": "nps",
            "health": "health_score",
            "risk": "risk_score",
        }
        for alias, std in alias_map.items():
            if alias in healed and std not in healed:
                healed[std] = healed.pop(alias)
                heals_applied.append(f"Mapped alias '{alias}' -> '{std}'")

        # 2. 补齐必填客户健康默认值
        if "health_score" not in healed:
            healed["health_score"] = 70.0
            heals_applied.append("Defaulted health_score to 70.0")

        if "status" not in healed:
            healed["status"] = "active"
            heals_applied.append("Defaulted status to 'active'")

        # 3. 补齐承诺三件套 (若存在 commitments 列表)
        if "commitments" in healed and isinstance(healed["commitments"], list):
            new_commitments = []
            for item in healed["commitments"]:
                if isinstance(item, str):
                    new_commitments.append({
                        "what": item,
                        "owner": healed.get("owner", "蛙客成"),
                        "due": "2026-12-31",
                    })
                    heals_applied.append(f"Expanded string commitment to triad: {item}")
                elif isinstance(item, dict):
                    comm = dict(item)
                    if "owner" not in comm:
                        comm["owner"] = healed.get("owner", "蛙客成")
                        heals_applied.append("Injected default owner into commitment")
                    if "due" not in comm:
                        comm["due"] = "2026-12-31"
                        heals_applied.append("Injected default due date into commitment")
                    new_commitments.append(comm)
            healed["commitments"] = new_commitments

        healed["_reflexive_heals"] = heals_applied
        return healed
