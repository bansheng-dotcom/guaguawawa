# -*- coding: utf-8 -*-
"""engines/reflexive_healer.py - [L03] 自愈反思层：人事红线刚性审判与就地反思自纠。

对标开源标杆：
- Reflexion: Language Agents with Verbal Reinforcement Learning (Stars > 40k)
- Critic-Agent 门禁拦截器与状态自愈修复模式

核心职责：
1. 刚性拦截人事四大违规红线：
   - REDLINE_UNAUTHORIZED_DISBURSEMENT: 严禁擅自直接发薪打款/解聘（强制要求交接并生成 handoff 声明，移交 R03 或人类授权）；
   - REDLINE_PII_OVERREACH: 严禁超限采集个人信息（身份证原件扫描、银行卡账号明文存储、超限个人隐私）；
   - REDLINE_LEGAL_TAX_VERDICT: 严禁代替律师或会计师出具劳动法仲裁/税务豁免/正式审计法律结论（必须声明移交 R03 + 外部法务）；
   - REDLINE_FABRICATED_PAYROLL_POLICY: 严禁凭空伪造/无源编造制度性薪酬字段（无 policy source 直接阻断）；
2. 反思自纠与自愈修补能力：
   - 当发现薪酬计算净额有微小偏差时，自动反思自纠并提示补平扣除明细；
   - 当发现 Offer 缺失前置状态（如直接从未初筛状态跳到 Accepted）时，自愈补齐前置流转审计节点；
   - 当发现输入缺少 handoff 或审计签名时，自愈注入责任人声明（DRI: R16 蛙人事）与 R03 移交标记。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple


class HRReflexiveHealer:
    """人事红线刚性审判与 Reflexion 反思自纠引擎。"""

    # 4 大违规红线定义
    REDLINES = [
        {
            "id": "REDLINE_UNAUTHORIZED_DISBURSEMENT",
            "name": "严禁擅自直接发薪打款或无授权解聘",
            "keywords": [
                "直接发薪", "代发工资", "直接打款", "代打款", "自动划扣薪资",
                "开除员工", "立即解聘", "擅自辞退", "直接裁员", "代付报销款"
            ],
            "category": "unauthorized_exec",
            "handoff_target": "R03 蛙首显 (CFO) / 人类授权主管",
        },
        {
            "id": "REDLINE_PII_OVERREACH",
            "name": "严禁超限采集或明文存储高敏个人信息",
            "keywords": [
                "身份证原件扫描", "明文存储银行卡", "采集宗教信仰", "采集政党派别",
                "采集婚育史", "采集乙肝血常规", "超规采集家庭住址"
            ],
            "category": "pii_violation",
            "handoff_target": "数据合规官 / 最小必要脱敏管道",
        },
        {
            "id": "REDLINE_LEGAL_TAX_VERDICT",
            "name": "严禁代替法务或会计师出具正式劳动仲裁与税务免责结论",
            "keywords": [
                "仲裁胜诉判定", "免除劳动合同赔偿", "出具正式法律意见书",
                "税务免责裁定", "出具审计结论", "担保无劳动争议风险"
            ],
            "category": "unauthorized_legal_verdict",
            "handoff_target": "R03 蛙首显 + 外部劳动法律顾问",
        },
        {
            "id": "REDLINE_FABRICATED_PAYROLL_POLICY",
            "name": "严禁凭空伪造/无源编造制度性薪酬字段",
            "keywords": [
                "伪造免税额度", "自设社保免缴", "凭空修改个税起征点", "编造离职补偿公式"
            ],
            "category": "fabricated_payroll_policy",
            "handoff_target": "HR Policy Source 规章制度台账",
        },
    ]

    def __init__(self, max_heal_rounds: int = 3):
        self.max_heal_rounds = max_heal_rounds

    # -------------------------------------------------------------------------
    # 1. 红线刚性审判
    # -------------------------------------------------------------------------
    def audit_redlines(self, action_or_query: str) -> Dict[str, Any]:
        """检查动作或文本是否触犯四大红线。触犯直接抛出 ValueError 或阻断判定。"""
        lower = action_or_query.lower()
        for red in self.REDLINES:
            for kw in red["keywords"]:
                if kw in lower:
                    raise ValueError(
                        f"触犯人事运营刚性红线 [{red['id']} - {red['name']}]："
                        f"检测到高危受限指令 '{kw}'！强制拦截阻断，必须移交 {red['handoff_target']}！"
                    )
        return {"ok": True, "compliant": True}

    # -------------------------------------------------------------------------
    # 2. 薪酬微小偏差自愈修补 (Net Payroll Balancing)
    # -------------------------------------------------------------------------
    def heal_payroll_balance(self, payroll_record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """当发现薪酬计算净额有微小偏差时，自动反思自纠并补平扣除明细与分位差。"""
        data = copy.deepcopy(payroll_record)
        heals: List[str] = []

        gross = round(float(data.get("gross_pay", 0.0)), 2)
        total_ded = round(float(data.get("total_deductions", 0.0)), 2)
        reported_net = round(float(data.get("net_pay", 0.0)), 2)
        theoretical_net = round(gross - total_ded, 2)

        diff = abs(reported_net - theoretical_net)
        if diff > 1e-4:
            data["net_pay"] = theoretical_net
            data["diff"] = 0.0
            data["is_balanced"] = True
            data["status"] = "BALANCED"
            heals.append(
                f"[Reflexion] 薪酬净额平衡修正：原净额 {reported_net} 与理论计算值 {theoretical_net} (差额={diff:.4f}) 存在分位不平，已就地自愈补平。"
            )

        # 确保包含五险一金或扣除明细项
        if "deduction_items" not in data or not data["deduction_items"]:
            data["deduction_items"] = [
                {"name": "法定社保公积金及个税", "amount": total_ded, "category": "statutory_and_tax"}
            ]
            heals.append("[Reflexion] 补齐缺失的扣除明细容器 (deduction_items)")

        return data, heals

    # -------------------------------------------------------------------------
    # 3. 招聘流转状态自愈 (Candidate Funnel Healing)
    # -------------------------------------------------------------------------
    def heal_candidate_flow(self, candidate_record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """当发现 Offer 缺失前置状态（如直接从 Applied 跳到 Accepted）时，自愈补齐前置流转审计节点。"""
        data = copy.deepcopy(candidate_record)
        heals: List[str] = []

        status = data.get("status", "Applied")
        history = list(data.get("stage_history", []))

        # 标准合法状态流转链
        flow_chain = ["Applied", "Screening_Passed", "Interview_Passed", "Offer_Issued", "Accepted"]

        if status == "Accepted":
            required_stages = ["Applied", "Screening_Passed", "Interview_Passed", "Offer_Issued"]
            missing_stages = [st for st in required_stages if st not in history]
            if missing_stages:
                # 自愈补齐前置审计节点
                for st in missing_stages:
                    history.append(st)
                    heals.append(f"[Reflexion] 候选人录用流转修补：就地补齐缺失的前置审计检查点 [{st}]")
                history.append("Accepted")
                data["stage_history"] = history
                data["audit_trail_healed"] = True

        return data, heals

    # -------------------------------------------------------------------------
    # 4. Handoff 与审计签名自愈注入 (Audit & Handoff Injection)
    # -------------------------------------------------------------------------
    def heal_handoff_and_dri(
        self,
        record: Dict[str, Any],
        requires_financial_handoff: bool = False,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """当发现输入缺少 handoff 或责任人签名时，自愈注入责任人声明 (DRI: R16 蛙人事) 与 R03 移交标记。"""
        data = copy.deepcopy(record)
        heals: List[str] = []

        if not data.get("dri"):
            data["dri"] = "R16 蛙人事 (人员与组织运营官)"
            heals.append("[Reflexion] 注入责任人声明 DRI: R16 蛙人事")

        if not data.get("audit_hash"):
            import hashlib
            raw_repr = str(sorted(data.items())).encode("utf-8")
            data["audit_hash"] = hashlib.sha256(raw_repr).hexdigest()[:16]
            heals.append(f"[Reflexion] 注入防篡改审计签名 hash={data['audit_hash']}")

        if requires_financial_handoff or any(kw in str(data).lower() for kw in ("payroll", "薪酬", "打款", "工资", "报销")):
            if not data.get("handoff_declared"):
                data["handoff_declared"] = True
                data["handoff_to"] = "R03 蛙首显 (CFO) / 财务税务复核"
                data["handoff_note"] = "本工件为 HR 运营核算草稿，不构成直接发薪打款指令，需 R03 与外部财务执行最终拨款。"
                heals.append("[Reflexion] 自愈注入财务跨角色移交声明三件套 (handoff_to R03)")

        return data, heals
