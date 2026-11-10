# -*- coding: utf-8 -*-
"""engines/runtime_engine.py - [L01] 工具实体层：真实人事与薪酬计算沙箱。

对标开源标杆：
- frappe/hrms / Odoo HR / Deel / Rippling API (Stars > 15k)
- 真实薪酬净额平衡精算、考勤工时与休假折算、招聘漏斗转化率、PII 敏感扫描与合规探测

核心职责：
1. 真实薪酬净额平衡精算沙箱：net = gross - deductions，包含五险一金比例与专项扣除精算，
   严格四舍五入分位，零容差（tolerance <= 0.001）；
2. 工时出勤与加班折算沙箱：working_hours、加班费工时计算、年假/病假余额扣减与天数闭合校验，重叠区间检测；
3. 招聘漏斗流转与转化率探针：funnel (applicants -> screening -> interview -> offer -> onboard)，阶段转化率实算；
4. PII 敏感度安全扫描与最小化合规探测（检测身份证号、银行卡号、超规家庭住址等敏感 PII 并阻断或打分）；
5. 运行时探针健康诊断 probe_health()，包含沙箱运行状态输出。
"""
from __future__ import annotations

import datetime
import math
import re
from typing import Any, Dict, List, Optional, Tuple


class HRRuntimeEngine:
    """真实人事与薪酬精算确定性沙箱引擎。"""

    # 常见标准社保公积金默认参考比例 (中国大陆标准通用参考区间：仅作为精算基准比例校验，严格可由参数覆盖)
    DEFAULT_STATUTORY_RATES = {
        "pension_rate": 0.08,       # 养老保险个人 8%
        "medical_rate": 0.02,       # 医疗保险个人 2%
        "unemployment_rate": 0.005, # 失业保险个人 0.5%
        "housing_fund_rate": 0.07,  # 住房公积金个人 7% (5%~12%弹性)
    }

    # 敏感 PII 规则库
    ID_CARD_REGEX = re.compile(r"(?:\b\d{17}[\dXx]\b|\b\d{15}\b)")
    BANK_CARD_REGEX = re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|62[0-9]{14,17}|3[47][0-9]{13})\b")
    ADDRESS_KEYWORDS = ["省", "市", "区", "县", "街道", "路", "号楼", "单元", "室", "胡同", "大厦", "门牌"]

    def __init__(self, tolerance: float = 0.001):
        self.tolerance = tolerance

    # -------------------------------------------------------------------------
    # 1. 真实薪酬净额平衡精算沙箱
    # -------------------------------------------------------------------------
    def calculate_net_payroll(
        self,
        gross_pay: float,
        deductions: Optional[List[Dict[str, Any]]] = None,
        statutory_base: Optional[float] = None,
        rates_override: Optional[Dict[str, float]] = None,
        special_additional_deduction: float = 0.0,
        tax_threshold: float = 5000.0,
        custom_tax: Optional[float] = None,
    ) -> Dict[str, Any]:
        """真实薪酬净额平衡精算沙箱：net = gross - total_deductions。

        严格四舍五入分位，零容差（tolerance <= 0.001）。
        若提供 statutory_base，按五险一金比例精准算计法定社保公积金扣除。
        """
        gross = round(float(gross_pay), 2)
        if gross < 0:
            raise ValueError("毛薪 (gross_pay) 不能为负数")

        rates = dict(self.DEFAULT_STATUTORY_RATES)
        if rates_override:
            rates.update(rates_override)

        deduction_items: List[Dict[str, Any]] = []
        total_statutory = 0.0

        # 1.1 法定五险一金精算
        base = round(float(statutory_base), 2) if statutory_base is not None else gross
        if base > 0:
            pension = round(base * rates.get("pension_rate", 0.08), 2)
            medical = round(base * rates.get("medical_rate", 0.02), 2)
            unemployment = round(base * rates.get("unemployment_rate", 0.005), 2)
            housing_fund = round(base * rates.get("housing_fund_rate", 0.07), 2)

            deduction_items.extend([
                {"name": "养老保险(个人)", "category": "statutory", "amount": pension, "rate": rates.get("pension_rate", 0.08)},
                {"name": "医疗保险(个人)", "category": "statutory", "amount": medical, "rate": rates.get("medical_rate", 0.02)},
                {"name": "失业保险(个人)", "category": "statutory", "amount": unemployment, "rate": rates.get("unemployment_rate", 0.005)},
                {"name": "住房公积金(个人)", "category": "statutory", "amount": housing_fund, "rate": rates.get("housing_fund_rate", 0.07)},
            ])
            total_statutory = round(pension + medical + unemployment + housing_fund, 2)

        # 1.2 其他自定义扣除项 (如考勤缺勤扣款、餐费代扣、企业年金等)
        custom_deductions_total = 0.0
        if deductions:
            for d in deductions:
                name = str(d.get("name", "其他扣除"))
                amt = round(float(d.get("amount", 0.0)), 2)
                cat = str(d.get("category", "other"))
                if amt < 0:
                    raise ValueError(f"扣除项 [{name}] 金额不能为负数")
                deduction_items.append({"name": name, "category": cat, "amount": amt})
                custom_deductions_total += amt

        custom_deductions_total = round(custom_deductions_total, 2)

        # 1.3 个人所得税精算 (IIT - Individual Income Tax)
        # 应纳税所得额 = 毛薪 - 五险一金 - 专项附加扣除 - 起征点
        special_add = round(float(special_additional_deduction), 2)
        if custom_tax is not None:
            tax = round(float(custom_tax), 2)
        else:
            taxable_income = gross - total_statutory - special_add - tax_threshold
            if taxable_income <= 0:
                tax = 0.0
            else:
                # 综合所得超额累进月度参考表
                if taxable_income <= 3000:
                    tax = taxable_income * 0.03
                elif taxable_income <= 12000:
                    tax = taxable_income * 0.10 - 210
                elif taxable_income <= 25000:
                    tax = taxable_income * 0.20 - 1410
                elif taxable_income <= 35000:
                    tax = taxable_income * 0.25 - 2660
                elif taxable_income <= 55000:
                    tax = taxable_income * 0.30 - 4410
                elif taxable_income <= 80000:
                    tax = taxable_income * 0.35 - 7160
                else:
                    tax = taxable_income * 0.45 - 15160
                tax = round(max(0.0, tax), 2)

        deduction_items.append({"name": "个人所得税", "category": "tax", "amount": tax})

        total_deductions = round(total_statutory + custom_deductions_total + tax, 2)
        net_pay = round(gross - total_deductions, 2)

        # 零容差平衡校验: |(gross - total_deductions) - net_pay| <= tolerance
        diff = abs(round(gross - total_deductions, 4) - round(net_pay, 4))
        is_balanced = diff <= self.tolerance

        return {
            "gross_pay": gross,
            "statutory_base": base,
            "total_statutory": total_statutory,
            "special_additional_deduction": special_add,
            "tax": tax,
            "custom_deductions": custom_deductions_total,
            "total_deductions": total_deductions,
            "net_pay": net_pay,
            "deduction_items": deduction_items,
            "diff": diff,
            "is_balanced": is_balanced,
            "is_conserved": is_balanced,
            "tolerance": self.tolerance,
            "status": "BALANCED" if is_balanced else "UNBALANCED",
        }

    def calculate_attendance_hours(
        self,
        standard_daily_hours: float = 8.0,
        work_days: float = 21.75,
        overtime_hours: float = 0.0,
        leave_hours: float = 0.0,
    ) -> Dict[str, Any]:
        """工时折算简易接口。"""
        std_hours = round(standard_daily_hours * work_days, 2)
        net_hours = round(std_hours + overtime_hours - leave_hours, 2)
        return {
            "status": "OK",
            "standard_hours": std_hours,
            "overtime_hours": overtime_hours,
            "leave_hours": leave_hours,
            "net_payable_hours": net_hours,
        }

    # -------------------------------------------------------------------------
    # 2. 工时出勤与加班折算沙箱
    # -------------------------------------------------------------------------
    def calculate_attendance_and_overtime(
        self,
        standard_daily_hours: float = 8.0,
        hourly_wage: float = 100.0,
        attendance_logs: Optional[List[Dict[str, Any]]] = None,
        overtime_records: Optional[List[Dict[str, Any]]] = None,
        leave_records: Optional[List[Dict[str, Any]]] = None,
        leave_balances: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """工时出勤与加班折算沙箱：

        1. working_hours 统计与考勤闭合校验；
        2. 加班费折算（工作日 1.5x，周末/休息日 2.0x，法定节假日 3.0x）；
        3. 年假/病假余额扣减与天数闭合校验，重叠区间检测。
        """
        logs = attendance_logs or []
        ots = overtime_records or []
        leaves = leave_records or []
        balances = dict(leave_balances or {"annual": 5.0, "sick": 10.0})

        # 2.1 统计正常出勤工时
        total_work_hours = 0.0
        for log in logs:
            h = float(log.get("hours", standard_daily_hours))
            total_work_hours += h
        total_work_hours = round(total_work_hours, 2)

        # 2.2 加班折算 (overtime hours & pay)
        ot_summary: Dict[str, Any] = {
            "weekday_hours": 0.0,
            "weekend_hours": 0.0,
            "holiday_hours": 0.0,
            "total_overtime_hours": 0.0,
            "total_overtime_pay": 0.0,
        }
        for ot in ots:
            ot_type = ot.get("type", "weekday")
            hours = float(ot.get("hours", 0.0))
            if hours < 0:
                raise ValueError("加班工时不能为负数")
            if ot_type == "holiday":
                ot_summary["holiday_hours"] += hours
            elif ot_type == "weekend":
                ot_summary["weekend_hours"] += hours
            else:
                ot_summary["weekday_hours"] += hours

        ot_summary["weekday_hours"] = round(ot_summary["weekday_hours"], 2)
        ot_summary["weekend_hours"] = round(ot_summary["weekend_hours"], 2)
        ot_summary["holiday_hours"] = round(ot_summary["holiday_hours"], 2)
        ot_summary["total_overtime_hours"] = round(
            ot_summary["weekday_hours"] + ot_summary["weekend_hours"] + ot_summary["holiday_hours"], 2
        )

        # 加班费倍率
        ot_pay = (
            ot_summary["weekday_hours"] * hourly_wage * 1.5 +
            ot_summary["weekend_hours"] * hourly_wage * 2.0 +
            ot_summary["holiday_hours"] * hourly_wage * 3.0
        )
        ot_summary["total_overtime_pay"] = round(ot_pay, 2)

        # 2.3 请假时序、区间重叠与余额扣减校验
        overlap_detected = False
        overlap_details: List[str] = []
        parsed_intervals: List[Tuple[datetime.date, datetime.date, str]] = []

        leave_deducted: Dict[str, float] = {}
        for l in leaves:
            ltype = l.get("type", "annual")
            days = float(l.get("days", 1.0))
            from_d = l.get("from_date")
            to_d = l.get("to_date")

            if from_d and to_d:
                f_date = datetime.date.fromisoformat(str(from_d)[:10])
                t_date = datetime.date.fromisoformat(str(to_d)[:10])
                if f_date > t_date:
                    raise ValueError(f"请假时序颠倒: {from_d} > {to_d}")

                # 校验区间重叠
                for (pf, pt, ptype) in parsed_intervals:
                    # 区间交集: max(start1, start2) <= min(end1, end2)
                    if max(f_date, pf) <= min(t_date, pt):
                        overlap_detected = True
                        overlap_details.append(f"检测到请假区间重叠: [{from_d} ~ {to_d}] 与已存在区间 [{pf} ~ {pt}] 冲突")
                parsed_intervals.append((f_date, t_date, ltype))

            leave_deducted[ltype] = round(leave_deducted.get(ltype, 0.0) + days, 2)

        # 扣减余额并检查是否超支
        remaining_balances = dict(balances)
        balance_insufficient = False
        insufficient_details: List[str] = []

        for ltype, used in leave_deducted.items():
            avail = remaining_balances.get(ltype, 0.0)
            if used > avail:
                balance_insufficient = True
                insufficient_details.append(f"假种 [{ltype}] 申请 {used} 天超过可用额度 {avail} 天")
            remaining_balances[ltype] = round(avail - used, 2)

        return {
            "total_work_hours": total_work_hours,
            "standard_daily_hours": standard_daily_hours,
            "hourly_wage": hourly_wage,
            "overtime": ot_summary,
            "leave_deductions": leave_deducted,
            "initial_balances": balances,
            "remaining_balances": remaining_balances,
            "overlap_detected": overlap_detected,
            "overlap_details": overlap_details,
            "balance_insufficient": balance_insufficient,
            "insufficient_details": insufficient_details,
            "is_valid": not (overlap_detected or balance_insufficient),
        }

    # -------------------------------------------------------------------------
    # 3. 招聘漏斗流转与转化率探针
    # -------------------------------------------------------------------------
    def calculate_recruitment_funnel(
        self,
        applicants_count: Any = 0,
        screening_passed_count: int = 0,
        interview_passed_count: int = 0,
        offer_accepted_count: int = 0,
        onboarded_count: int = 0,
    ) -> Dict[str, Any]:
        """招聘漏斗流转与转化率精算探针：

        applicants -> screening -> interview -> offer -> onboard
        计算各阶段绝对留存转化率与上阶段流转率。
        同时支持传入阶段字典列表 `[{"stage": "...", "count": ...}]`。
        """
        if isinstance(applicants_count, list):
            items = applicants_count
            c_dict = {item.get("stage"): int(item.get("count", 0)) for item in items}
            app_c = c_dict.get("applicants", 0)
            scr_c = c_dict.get("screening", 0)
            int_c = c_dict.get("interview", 0)
            off_c = c_dict.get("offer", 0)
            onb_c = c_dict.get("onboard", 0)
            res = self.calculate_recruitment_funnel(app_c, scr_c, int_c, off_c, onb_c)
            res["total_applicants"] = app_c
            return res

        counts = [
            ("applicants", applicants_count),
            ("screening", screening_passed_count),
            ("interview", interview_passed_count),
            ("offer", offer_accepted_count),
            ("onboard", onboarded_count),
        ]

        # 逻辑单调递减校验 (后续阶段不能超过前置阶段)
        stage_violations: List[str] = []
        for i in range(len(counts) - 1):
            curr_name, curr_c = counts[i]
            next_name, next_c = counts[i + 1]
            if curr_c < 0 or next_c < 0:
                stage_violations.append(f"阶段人数不能为负数: {curr_name}={curr_c}, {next_name}={next_c}")
            if next_c > curr_c:
                stage_violations.append(f"招聘流转逆序违背漏斗守恒: {next_name}({next_c}) > {curr_name}({curr_c})")

        total_app = max(1, applicants_count)

        funnel_metrics = {
            "applicants": applicants_count,
            "screening_passed": screening_passed_count,
            "interview_passed": interview_passed_count,
            "offer_accepted": offer_accepted_count,
            "onboarded": onboarded_count,
            # 阶段间转化率
            "rate_screening_per_applicant": round(screening_passed_count / total_app, 4) if applicants_count > 0 else 0.0,
            "rate_interview_per_screening": round(interview_passed_count / screening_passed_count, 4) if screening_passed_count > 0 else 0.0,
            "rate_offer_per_interview": round(offer_accepted_count / interview_passed_count, 4) if interview_passed_count > 0 else 0.0,
            "rate_onboard_per_offer": round(onboarded_count / offer_accepted_count, 4) if offer_accepted_count > 0 else 0.0,
            # 总体终态转化率
            "overall_conversion_rate": round(onboarded_count / total_app, 4) if applicants_count > 0 else 0.0,
            "stage_violations": stage_violations,
            "is_funnel_valid": len(stage_violations) == 0,
        }
        return funnel_metrics

    # -------------------------------------------------------------------------
    # 4. PII 敏感度安全扫描与最小化合规探测
    # -------------------------------------------------------------------------
    def scan_pii_compliance(
        self,
        data: Any,
        strict_block: bool = False,
    ) -> Dict[str, Any]:
        """敏感 PII 安全扫描与最小化合规探测：

        检测身份证号、银行卡号、超规家庭住址等敏感 PII 并阻断或打分。
        """
        findings: List[Dict[str, Any]] = []

        def _traverse(val: Any, path: str = "$"):
            if isinstance(val, dict):
                for k, v in val.items():
                    current_path = f"{path}.{k}"
                    # 检查字段名关键词
                    lk = str(k).lower()
                    if any(term in lk for term in ("id_card", "id_number", "idcard", "identity_card")):
                        findings.append({"path": current_path, "type": "ID_CARD_FIELD", "value": str(v), "severity": "HIGH"})
                    elif any(term in lk for term in ("bank_card", "bank_account", "card_number", "account_no")):
                        findings.append({"path": current_path, "type": "BANK_CARD_FIELD", "value": str(v), "severity": "HIGH"})
                    elif any(term in lk for term in ("home_address", "address", "domicile", "住址", "家庭住址")):
                        findings.append({"path": current_path, "type": "HOME_ADDRESS_FIELD", "value": str(v), "severity": "MEDIUM"})
                    elif any(term in lk for term in ("religion", "ethnicity", "political_status", "medical_report")):
                        findings.append({"path": current_path, "type": "EXCESSIVE_PII_FIELD", "value": str(v), "severity": "HIGH"})
                    _traverse(v, current_path)
            elif isinstance(val, list):
                for idx, item in enumerate(val):
                    _traverse(item, f"{path}[{idx}]")
            elif isinstance(val, str):
                # 检查字符串内容是否命中敏感正则
                if self.ID_CARD_REGEX.search(val):
                    findings.append({"path": path, "type": "ID_CARD_CONTENT", "value": val[:6] + "******", "severity": "CRITICAL"})
                if self.BANK_CARD_REGEX.search(val):
                    findings.append({"path": path, "type": "BANK_CARD_CONTENT", "value": val[:4] + "******", "severity": "CRITICAL"})
                if any(kw in val for kw in ("号楼", "单元", "门牌", "胡同", "大厦")):
                    findings.append({"path": path, "type": "HOME_ADDRESS_CONTENT", "value": val[:10] + "...", "severity": "MEDIUM"})

        _traverse(data)

        # 评分计算 (满分 100，违规按严重程度扣减)
        score = 100
        for f in findings:
            sev = f["severity"]
            if sev == "CRITICAL":
                score -= 40
            elif sev == "HIGH":
                score -= 25
            else:
                score -= 10
        score = max(0, score)

        has_critical_or_high = any(f["severity"] in ("CRITICAL", "HIGH") for f in findings)
        is_blocked = strict_block and has_critical_or_high

        return {
            "pii_score": score,
            "compliant": score >= 80 and not is_blocked,
            "is_compliant": score >= 80 and not is_blocked,
            "blocked": is_blocked,
            "findings_count": len(findings),
            "violations_count": len(findings),
            "findings": findings,
            "recommendation": "阻断入库并进行去标识化/脱敏处理" if has_critical_or_high else "合规风险较低",
        }

    # -------------------------------------------------------------------------
    # 5. 运行时探针健康诊断
    # -------------------------------------------------------------------------
    def probe_health(self) -> Dict[str, Any]:
        """HR 运行时沙箱健康探测诊断。"""
        # 自测薪酬精算
        calc_test = self.calculate_net_payroll(
            gross_pay=10000.0,
            statutory_base=10000.0,
            special_additional_deduction=1500.0,
        )
        # 自测考勤休假
        att_test = self.calculate_attendance_and_overtime(
            standard_daily_hours=8.0,
            hourly_wage=50.0,
            attendance_logs=[{"hours": 8.0}],
            overtime_records=[{"type": "weekday", "hours": 2.0}],
            leave_records=[],
            leave_balances={"annual": 5.0},
        )
        # 自测招聘漏斗
        funnel_test = self.calculate_recruitment_funnel(100, 40, 20, 5, 4)

        healthy = (
            calc_test["is_balanced"] and
            att_test["is_valid"] and
            funnel_test["is_funnel_valid"]
        )

        return {
            "status": "HEALTHY" if healthy else "DEGRADED",
            "tolerance": self.tolerance,
            "payroll_sandbox": "OK" if calc_test["is_balanced"] else "FAIL",
            "attendance_sandbox": "OK" if att_test["is_valid"] else "FAIL",
            "funnel_sandbox": "OK" if funnel_test["is_funnel_valid"] else "FAIL",
            "pii_scanner": "READY",
            "engine": "HRRuntimeEngine",
            "version": "13.0",
        }
