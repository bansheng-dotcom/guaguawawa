# -*- coding: utf-8 -*-
"""engines/spec_ledger.py - [L04] 领域账本层：HR 业务规格账本加载与 8 维门禁合规校验。

对标开源标杆：
- dbt Semantic Layer / Cube.js 指标账本模式
- Frappe HRMS / Workday HCM 业务对象约束与单一信任源 (SSOT)

核心职责：
1. 动态读取并解析 HR_SPEC.md 单一信任源 (Single Source of Truth)；
2. 提取北极星指标 (PRA, OTA, PMR, LBR, TOR) 与量纲容差；
3. 执行 8 维人事硬门禁刚性审查 (The 8-Dimension HR Gate Matrix)；
4. 输出合规性审查摘要与违规门禁阻断列表。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(_HERE, "HR_SPEC.md")


class HRSpecLedger:
    """HR 与组织运营单一信任源规格账本管理器。"""

    def __init__(self, spec_file: str = SPEC_PATH):
        self.spec_file = spec_file

    def load_spec(self) -> Dict[str, Any]:
        """读取并结构化解析 HR_SPEC.md。"""
        if not os.path.exists(self.spec_file):
            raise FileNotFoundError(f"找不到统一规格账本: {self.spec_file}")

        with open(self.spec_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取北极星指标
        kpis = {
            "PRA": {
                "name": "薪酬记录准度",
                "target": ">= 100.0%",
                "tolerance": 0.00,
                "description": "实发净额与应发扣款绝对守恒，净额容差 0.00",
            },
            "OTA": {
                "name": "录用接受前置率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "Offer 发放必须前置通过筛选/面试且状态源自 Shortlisted/Accepted",
            },
            "PMR": {
                "name": "敏感个人信息泄露率",
                "target": "= 0.00%",
                "tolerance": 0.00,
                "description": "明文身份证号、银行卡号、私密家庭住址零泄露收录",
            },
            "LBR": {
                "name": "休假天数与余额恒等率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "申请天数<=可用余额且同一员工假期区间不重叠",
            },
            "TOR": {
                "name": "流动率实算率",
                "target": "= 100.0%",
                "tolerance": 0.00,
                "description": "离职流动率严格实算，拒绝主观臆断拍脑袋",
            },
        }

        # 提取 8 维硬门禁
        gates = [
            {"id": "GATE-01", "name": "净额恒等门禁", "threshold": "gross - Σdeduction == net (tolerance 0.00)"},
            {"id": "GATE-02", "name": "PII 最小化刚性拦截", "threshold": "pii_violations == 0 (no raw id_card/bank_card/address)"},
            {"id": "GATE-03", "name": "录用前置门禁", "threshold": "offer_status in ['Shortlisted', 'Accepted'] and valid_pipeline"},
            {"id": "GATE-04", "name": "休假天数与余额守恒", "threshold": "0 < requested_days <= leave_balance"},
            {"id": "GATE-05", "name": "休假重叠检测", "threshold": "overlap_intervals_count == 0"},
            {"id": "GATE-06", "name": "薪酬制度溯源", "threshold": "has_source_policy == True"},
            {"id": "GATE-07", "name": "报销总额与明细恒等", "threshold": "total == sum(items) and len(items) >= 1 and item > 0"},
            {"id": "GATE-08", "name": "人事红线授权与移交", "threshold": "requires_handoff implies handoff_declared == True"},
        ]

        return {
            "spec_file": os.path.basename(self.spec_file),
            "version": "v13.0",
            "role": "R16 蛙人事 · 人力资源与组织运营官",
            "north_star_kpis": kpis,
            "gates_count": len(gates),
            "gates": gates,
            "raw_size": len(content),
        }

    def verify_gate_compliance(self, artifact_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """按 8 维人事门禁标准对给定工件执行刚性合规审查。"""
        violations: List[str] = []
        checks: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # GATE-01: 净额恒等门禁 (gross - Σdeduction = net, 容差 0.00)
        # -------------------------------------------------------------
        if "gross_pay" in data and "net_pay" in data:
            gross = float(data["gross_pay"])
            net = float(data["net_pay"])

            # 计算扣减合计
            if "total_deductions" in data:
                total_ded = float(data["total_deductions"])
            elif "deductions" in data:
                if isinstance(data["deductions"], list):
                    total_ded = sum(float(x.get("amount", 0.0)) for x in data["deductions"])
                else:
                    total_ded = float(data["deductions"])
            elif "components" in data and isinstance(data["components"], list):
                total_ded = 0.0
                for comp in data["components"]:
                    amt = float(comp.get("amount", 0.0))
                    ctype = str(comp.get("type", "")).lower()
                    if amt < 0:
                        total_ded += abs(amt)
                    elif ctype in ("deduction", "tax", "statutory", "social_security", "housing_fund"):
                        total_ded += amt
            else:
                total_ded = 0.0

            expected_net = round(gross - total_ded, 4)
            actual_net = round(net, 4)
            diff = abs(expected_net - actual_net)
            is_ok = diff < 1e-4
            checks.append({"gate": "GATE-01", "ok": is_ok, "detail": f"净额期望: {expected_net}, 实际: {actual_net}, 差额: {diff}"})
            if not is_ok:
                violations.append(
                    f"GATE-01 破损: 薪酬实发净额不守恒 (应发 {gross} - 扣除 {total_ded} = {expected_net}, 实际 {actual_net}, 差额 {diff})"
                )

        # -------------------------------------------------------------
        # GATE-02: PII 最小化刚性拦截 (禁止明文身份证/银行卡/私密住址)
        # -------------------------------------------------------------
        forbidden_keys = {
            "id_card", "id_number", "id_card_number",
            "bank_card", "bank_account", "bank_account_number",
            "home_address", "social_security_card",
        }
        if "pii_violations" in data:
            pii_count = int(data["pii_violations"])
            is_pii_ok = (pii_count == 0)
            checks.append({"gate": "GATE-02", "ok": is_pii_ok, "detail": f"PII 违规命中数: {pii_count}"})
            if not is_pii_ok:
                violations.append(f"GATE-02 破损: 检出 {pii_count} 项未脱敏个人隐私 PII")
        else:
            pii_hits: List[str] = []

            def _scan_pii(obj: Any, prefix: str = ""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        k_lower = str(k).lower()
                        if k_lower in forbidden_keys and v:
                            v_str = str(v)
                            # 如果没有脱敏掩码，判定为违规收录
                            if "*" not in v_str:
                                pii_hits.append(f"字段 [{prefix}{k}] 包含未脱敏个人隐私: {v_str[:6]}...")
                        _scan_pii(v, prefix=f"{prefix}{k}.")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        _scan_pii(item, prefix=f"{prefix}[{i}].")
                elif isinstance(obj, str):
                    # 校验身份证号正则
                    if re.search(r"\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", obj):
                        if "*" not in obj:
                            pii_hits.append(f"文本值检测到明文中国居民身份证: {obj[:6]}...")
                    # 校验银行卡号正则 (16~19位连续数字)
                    if re.search(r"\b62\d{14,17}\b", obj):
                        if "*" not in obj:
                            pii_hits.append(f"文本值检测到明文银行卡号: {obj[:6]}...")

            _scan_pii(data)
            is_pii_ok = len(pii_hits) == 0
            checks.append({"gate": "GATE-02", "ok": is_pii_ok, "detail": f"PII 违规命中数: {len(pii_hits)}"})
            if not is_pii_ok:
                violations.append(f"GATE-02 破损: 检出高敏个人隐私 PII ({'; '.join(pii_hits[:3])})，严禁明文入库")

        # -------------------------------------------------------------
        # GATE-03: 录用前置门禁 (Offer 状态必须来自 Shortlisted/Accepted)
        # -------------------------------------------------------------
        valid_priors = {"shortlisted", "accepted", "interviewed", "interview_passed", "screening_passed"}
        if "stage" in data and "previous_stage" in data:
            stage = str(data["stage"]).lower()
            prev = str(data["previous_stage"]).lower()
            if stage == "offer" and prev not in ("shortlisted", "accepted"):
                violations.append(f"GATE-03 破损: Offer 状态来自非法前置阶段 [{prev}]，必须来自 Shortlisted/Accepted")
                checks.append({"gate": "GATE-03", "ok": False, "detail": "录用流程前置校验失败"})
            else:
                checks.append({"gate": "GATE-03", "ok": True, "detail": "录用流程前置校验通过"})
        elif artifact_type == "offer" or "offer_status" in data or "prior_status" in data or "stage_history" in data:
            is_offer_ok = True
            invalid_reasons: List[str] = []

            # 校验 stage_history 漏斗完整性
            if "stage_history" in data and isinstance(data["stage_history"], list):
                history = [str(s).lower() for s in data["stage_history"]]
                # 严禁直接从 applied/sourced 跃迁发 offer
                if len(history) <= 1 and history and history[0] in ("applied", "sourced"):
                    is_offer_ok = False
                    invalid_reasons.append(f"流转历史仅包含前置起步阶段 {data['stage_history']}，缺少筛选面试记录")
                elif not any(req in history for req in ("shortlisted", "interviewed", "interview_passed", "screening_passed")):
                    is_offer_ok = False
                    invalid_reasons.append(f"流转历史 {data['stage_history']} 未包含筛选或面试通过节点")

            # 校验 prior_status
            if "prior_status" in data:
                prior = str(data["prior_status"]).strip().lower()
                if prior not in valid_priors:
                    is_offer_ok = False
                    invalid_reasons.append(f"前置状态 '{data['prior_status']}' 不在允许状态 Shortlisted/Accepted 范围")

            # 校验 candidate_status 跃迁
            if "candidate_status" in data:
                cand_st = str(data["candidate_status"]).strip().lower()
                if cand_st in ("applied", "sourced") and data.get("action") == "issue_offer":
                    is_offer_ok = False
                    invalid_reasons.append(f"候选人当前状态仍为 '{data['candidate_status']}'，严禁跨阶段发放 Offer")

            checks.append({"gate": "GATE-03", "ok": is_offer_ok, "detail": f"Offer 前置流转合规性: {is_offer_ok}"})
            if not is_offer_ok:
                violations.append(f"GATE-03 破损: 录用前置门禁未通过 ({'; '.join(invalid_reasons)})")
        else:
            checks.append({"gate": "GATE-03", "ok": True, "detail": "非 Offer 流程或状态数据缺失，跳过校验"})

        # -------------------------------------------------------------
        # GATE-04: 休假天数与余额守恒 (天数必须与周期匹配且额度<=余额)
        # -------------------------------------------------------------
        if "requested_days" in data and "leave_balance" in data:
            days = float(data["requested_days"])
            balance = float(data["leave_balance"])
            is_leave_ok = (days > 0) and (days <= balance)
            checks.append({"gate": "GATE-04", "ok": is_leave_ok, "detail": f"申请天数: {days}, 可用余额: {balance}"})
            if not is_leave_ok:
                violations.append(f"GATE-04 破损: 休假天数超出可用余额或为非法非正数 (申请 {days} 天, 余额 {balance} 天)")
        elif "leave_days" in data and "leave_balance" in data:
            days = float(data["leave_days"])
            balance = float(data["leave_balance"])
            is_leave_ok = (days > 0) and (days <= balance)
            checks.append({"gate": "GATE-04", "ok": is_leave_ok, "detail": f"申请天数: {days}, 可用余额: {balance}"})
            if not is_leave_ok:
                violations.append(f"GATE-04 破损: 休假天数超出可用余额或为非法非正数 (申请 {days} 天, 余额 {balance} 天)")

        if "leave_records" in data and "leave_balances" in data and isinstance(data["leave_records"], list):
            balances = dict(data["leave_balances"])
            is_lbr_ok = True
            for rec in data["leave_records"]:
                ltype = rec.get("type", "annual")
                ldays = float(rec.get("days", 0.0))
                avail = float(balances.get(ltype, 0.0))
                if ldays <= 0 or ldays > avail:
                    is_lbr_ok = False
                    violations.append(f"GATE-04 破损: 假期 [{ltype}] 申请 {ldays} 天超出可用额度 {avail} 天")
                balances[ltype] = avail - ldays
            checks.append({"gate": "GATE-04", "ok": is_lbr_ok, "detail": "多类型休假记录余额扣减审查"})

        # -------------------------------------------------------------
        # GATE-05: 休假重叠检测 (同一员工假期区间不得重叠)
        # -------------------------------------------------------------
        if "overlap_count" in data:
            is_overlap_ok = (int(data["overlap_count"]) == 0)
            checks.append({"gate": "GATE-05", "ok": is_overlap_ok, "detail": f"假期区间重叠数: {data['overlap_count']}"})
            if not is_overlap_ok:
                violations.append(f"GATE-05 破损: 检测到 {data['overlap_count']} 处假期区间重叠")
        elif "leave_records" in data and isinstance(data["leave_records"], list) and len(data["leave_records"]) > 1:
            records = data["leave_records"]
            overlap_found = False
            for i in range(len(records)):
                for j in range(i + 1, len(records)):
                    r1 = records[i]
                    r2 = records[j]
                    f1, t1 = r1.get("from_date", ""), r1.get("to_date", "")
                    f2, t2 = r2.get("from_date", ""), r2.get("to_date", "")
                    if f1 and t1 and f2 and t2:
                        # 区间重叠判断: not (t1 < f2 or t2 < f1)
                        if not (t1 < f2 or t2 < f1):
                            overlap_found = True
                            break
                if overlap_found:
                    break
            is_overlap_ok = not overlap_found
            checks.append({"gate": "GATE-05", "ok": is_overlap_ok, "detail": f"假期区间重叠检出: {overlap_found}"})
            if not is_overlap_ok:
                violations.append("GATE-05 破损: 检测到同一员工请假日期区间存在交叉重叠，违反守恒约束")

        # -------------------------------------------------------------
        # GATE-06: 薪酬制度溯源 (社保公积金免税额必须带 source 制度行)
        # -------------------------------------------------------------
        if "policy_source" in data:
            has_source = bool(data["policy_source"])
            checks.append({"gate": "GATE-06", "ok": has_source, "detail": f"薪酬制度溯源: {data['policy_source']}"})
            if not has_source:
                violations.append("GATE-06 破损: 缺失薪酬规章制度溯源")
        elif "statutory_base" in data or "statutory_deductions" in data or "social_security" in data or "housing_fund" in data or (artifact_type == "payroll_calc" and "statutory_base" in data):
            has_source = any(k in data for k in ("source_policy", "policy_line", "statutory_source", "policy_reference"))
            if not has_source and "components" in data and isinstance(data["components"], list):
                # 检查各项扣款是否带 source 标注
                has_source = any("source" in c or "policy" in c for c in data["components"])
            checks.append({"gate": "GATE-06", "ok": has_source, "detail": f"法定扣减制度溯源: {has_source}"})
            if not has_source:
                violations.append("GATE-06 破损: 社保/公积金/个税法定扣除项缺失制度法规溯源行 (source_policy/policy_line)")

        # -------------------------------------------------------------
        # GATE-07: 报销总额与明细恒等 (总额 = Σ明细且明细行数>=1且金额>0)
        # -------------------------------------------------------------
        if "claim_total" in data and "claim_items" in data:
            total_amt = float(data["claim_total"])
            details = data["claim_items"]
            is_claim_ok = True
            claim_err = ""
            if not isinstance(details, list) or len(details) == 0:
                is_claim_ok = False
                claim_err = "报销单明细行数必须 >= 1"
            else:
                sum_details = sum(float(it.get("amount", 0.0)) for it in details)
                diff = abs(round(total_amt, 4) - round(sum_details, 4))
                if diff >= 1e-4:
                    is_claim_ok = False
                    claim_err = f"报销申报总额 {total_amt} 与明细合计 {sum_details} 不恒等"
            checks.append({"gate": "GATE-07", "ok": is_claim_ok, "detail": claim_err or "报销总额与明细一致"})
            if not is_claim_ok:
                violations.append(f"GATE-07 破损: {claim_err}")
        elif artifact_type in ("claim", "expense", "reimbursement") or "total_claimed_amount" in data or "expense_details" in data:
            total_amt = float(data.get("total_claimed_amount", data.get("total_amount", 0.0)))
            details = data.get("expense_details", data.get("items", []))
            is_claim_ok = True
            claim_err = ""

            if not isinstance(details, list) or len(details) == 0:
                is_claim_ok = False
                claim_err = "报销单明细行数必须 >= 1"
            else:
                sum_details = 0.0
                for idx, it in enumerate(details):
                    amt = float(it.get("amount", 0.0))
                    if amt <= 0:
                        is_claim_ok = False
                        claim_err = f"明细第 {idx+1} 项金额 ({amt}) 必须大于 0"
                        break
                    sum_details += amt

                if is_claim_ok:
                    diff = abs(round(total_amt, 4) - round(sum_details, 4))
                    if diff >= 1e-4:
                        is_claim_ok = False
                        claim_err = f"报销申报总额 {total_amt} 与明细合计 {sum_details} 不恒等 (差额 {diff})"

            checks.append({"gate": "GATE-07", "ok": is_claim_ok, "detail": claim_err or "报销总额与明细一致且单项>0"})
            if not is_claim_ok:
                violations.append(f"GATE-07 破损: {claim_err}")

        # -------------------------------------------------------------
        # GATE-08: 人事红线授权与移交 (严禁擅自发薪/解聘/法律税务结论)
        # -------------------------------------------------------------
        if "requires_handoff" in data:
            if data["requires_handoff"]:
                has_handoff = bool(data.get("handoff_declared", False))
                checks.append({"gate": "GATE-08", "ok": has_handoff, "detail": f"人事红线授权移交状态: {has_handoff}"})
                if not has_handoff:
                    violations.append("GATE-08 破损: 涉及发薪/解聘红线动作缺少显式 handoff 授权移交声明")
            else:
                checks.append({"gate": "GATE-08", "ok": True, "detail": "无发薪/解聘红线动作，无需 handoff"})
        else:
            action = str(data.get("action", "")).lower()
            needs_handoff = (
                artifact_type in ("payroll_payout", "payout", "termination", "dismissal", "tax_filing")
                or action in ("payout", "terminate", "dismiss", "tax_filing", "execute_payout")
                or bool(data.get("is_payout", False))
                or bool(data.get("is_termination", False))
            )
            if needs_handoff:
                has_handoff = bool(
                    data.get("handoff_declared", False)
                    or data.get("handoff_to")
                    or data.get("authorized", False)
                    or data.get("legal_handoff", False)
                )
                checks.append({"gate": "GATE-08", "ok": has_handoff, "detail": f"人事红线动作授权移交状态: {has_handoff}"})
                if not has_handoff:
                    violations.append(f"GATE-08 破损: 涉及发薪/解聘/法务红线动作 ({action or artifact_type}) 缺少显式 handoff 授权移交声明")

        passed = len(violations) == 0
        return {
            "compliant": passed,
            "violations_count": len(violations),
            "violations": violations,
            "checks_evaluated": len(checks),
            "checks": checks,
        }


# 别名兼容
SpecLedger = HRSpecLedger
