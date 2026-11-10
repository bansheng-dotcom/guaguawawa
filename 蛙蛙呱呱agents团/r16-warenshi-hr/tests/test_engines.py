# -*- coding: utf-8 -*-
"""tests/test_engines.py - L01~L06 核心引擎单元测试。"""
import pytest
from engines.runtime_engine import HRRuntimeEngine
from engines.intent_compiler import HRIntentCompiler
from engines.reflexive_healer import HRReflexiveHealer
from engines.spec_ledger import HRSpecLedger, SpecLedger
from engines.slop_guard import HRSlopGuard, SlopGuard
from engines.scenario_matrix import HRScenarioMatrix, ScenarioMatrix


def test_runtime_engine_payroll_balance():
    engine = HRRuntimeEngine()
    # 正常薪酬精算
    res = engine.calculate_net_payroll(
        gross_pay=20000.0,
        statutory_base=20000.0,
        special_additional_deduction=1500.0,
    )
    assert res["is_balanced"] is True
    assert res["diff"] <= 0.001
    assert res["gross_pay"] == 20000.0
    assert res["net_pay"] > 0
    assert len(res["deduction_items"]) >= 5


def test_runtime_engine_attendance_and_overtime():
    engine = HRRuntimeEngine()
    res = engine.calculate_attendance_and_overtime(
        standard_daily_hours=8.0,
        hourly_wage=100.0,
        attendance_logs=[{"hours": 8.0}, {"hours": 8.0}],
        overtime_records=[
            {"type": "weekday", "hours": 2.0},
            {"type": "weekend", "hours": 4.0},
        ],
        leave_records=[
            {"type": "annual", "days": 1.0, "from_date": "2026-11-01", "to_date": "2026-11-01"}
        ],
        leave_balances={"annual": 5.0, "sick": 10.0},
    )
    assert res["is_valid"] is True
    assert res["total_work_hours"] == 16.0
    # 加班费: 2*100*1.5 + 4*100*2.0 = 300 + 800 = 1100
    assert res["overtime"]["total_overtime_pay"] == 1100.0
    assert res["remaining_balances"]["annual"] == 4.0


def test_runtime_engine_attendance_overlap():
    engine = HRRuntimeEngine()
    res = engine.calculate_attendance_and_overtime(
        leave_records=[
            {"type": "annual", "days": 2.0, "from_date": "2026-11-01", "to_date": "2026-11-02"},
            {"type": "sick", "days": 1.0, "from_date": "2026-11-02", "to_date": "2026-11-03"},
        ],
        leave_balances={"annual": 5.0, "sick": 5.0},
    )
    assert res["overlap_detected"] is True
    assert res["is_valid"] is False


def test_runtime_engine_funnel():
    engine = HRRuntimeEngine()
    res = engine.calculate_recruitment_funnel(100, 40, 20, 5, 4)
    assert res["is_funnel_valid"] is True
    assert res["rate_screening_per_applicant"] == 0.4
    assert res["rate_interview_per_screening"] == 0.5
    assert res["overall_conversion_rate"] == 0.04


def test_runtime_engine_pii_scanner():
    engine = HRRuntimeEngine()
    # 含有敏感身份证和超规住址
    dirty_data = {
        "candidate": "张三",
        "id_card": "110101199003072345",
        "home_address": "北京市朝阳区某某路1号楼3单元501室",
    }
    scan = engine.scan_pii_compliance(dirty_data, strict_block=True)
    assert scan["blocked"] is True
    assert scan["pii_score"] < 80
    assert scan["findings_count"] >= 2


def test_runtime_engine_health():
    engine = HRRuntimeEngine()
    h = engine.probe_health()
    assert h["status"] == "HEALTHY"


def test_intent_compiler_dag_compilation():
    compiler = HRIntentCompiler()
    prompt = "急聘两名高级前端工程师，预算25k，安排面试发offer并推进下月薪酬与考勤入职"
    stages = compiler.compile_intent(prompt)
    assert len(stages) == 5
    assert stages[0]["id"] == "S1_SOURCING"
    assert stages[-1]["id"] == "S5_PAYROLL_ENROLLMENT"

    sched = compiler.evaluate_budget_and_schedule(stages)
    assert sched["is_dag_valid"] is True
    assert sched["topological_sequence"] == [
        "S1_SOURCING",
        "S2_SCREENING_INTERVIEW",
        "S3_OFFER_CONTRACT",
        "S4_ONBOARD_ATTENDANCE",
        "S5_PAYROLL_ENROLLMENT",
    ]
    assert sched["total_estimated_hours"] > 0


def test_reflexive_healer_redlines():
    healer = HRReflexiveHealer()
    # 违规直接打款
    with pytest.raises(ValueError, match="严禁擅自直接发薪打款"):
        healer.audit_redlines("请为张三直接发薪打款到其个人账户")

    # 违规超限采集
    with pytest.raises(ValueError, match="严禁超限采集"):
        healer.audit_redlines("要求候选人提供身份证原件扫描并上传")


def test_reflexive_healer_healing():
    healer = HRReflexiveHealer()

    # 薪酬平衡修补
    imbalanced_payroll = {
        "gross_pay": 10000.0,
        "total_deductions": 2000.0,
        "net_pay": 7999.0,  # 存在 1 元偏差
    }
    healed_pay, heals = healer.heal_payroll_balance(imbalanced_payroll)
    assert healed_pay["net_pay"] == 8000.0
    assert healed_pay["is_balanced"] is True
    assert len(heals) > 0

    # 候选人流转修补
    candidate_skip = {
        "name": "李四",
        "status": "Accepted",
        "stage_history": ["Applied"],
    }
    healed_cand, cand_heals = healer.heal_candidate_flow(candidate_skip)
    assert "Screening_Passed" in healed_cand["stage_history"]
    assert "Offer_Issued" in healed_cand["stage_history"]

    # Handoff 与 DRI 注入
    record = {"task": "核算薪酬发放草稿"}
    healed_rec, rec_heals = healer.heal_handoff_and_dri(record, requires_financial_handoff=True)
    assert "R16 蛙人事" in healed_rec["dri"]
    assert healed_rec["handoff_declared"] is True
    assert "R03" in healed_rec["handoff_to"]


# =========================================================================
# L04 领域账本层测试 (HRSpecLedger / SpecLedger)
# =========================================================================

def test_spec_ledger_load_spec():
    ledger = HRSpecLedger()
    spec = ledger.load_spec()
    assert spec["version"] == "v13.0"
    assert spec["gates_count"] == 8
    assert "PRA" in spec["north_star_kpis"]
    assert "OTA" in spec["north_star_kpis"]
    assert "PMR" in spec["north_star_kpis"]
    assert "LBR" in spec["north_star_kpis"]
    assert "TOR" in spec["north_star_kpis"]
    assert len(spec["gates"]) == 8


def test_spec_ledger_gate_01_net_balance():
    ledger = SpecLedger()
    # 合规薪酬
    good_pay = {
        "gross_pay": 18000.0,
        "total_deductions": 3600.0,
        "net_pay": 14400.0,
    }
    res_good = ledger.verify_gate_compliance("payroll", good_pay)
    assert res_good["compliant"] is True

    # 破损薪酬 (差额 10 元)
    bad_pay = {
        "gross_pay": 18000.0,
        "total_deductions": 3600.0,
        "net_pay": 14390.0,
    }
    res_bad = ledger.verify_gate_compliance("payroll", bad_pay)
    assert res_bad["compliant"] is False
    assert any("GATE-01" in v for v in res_bad["violations"])


def test_spec_ledger_gate_02_pii_minimization():
    ledger = HRSpecLedger()
    # 含有明文身份证
    dirty_pii = {
        "applicant": "王五",
        "id_card": "110101199003072345",
    }
    res_pii = ledger.verify_gate_compliance("applicant", dirty_pii)
    assert res_pii["compliant"] is False
    assert any("GATE-02" in v for v in res_pii["violations"])

    # 脱敏后合规
    clean_pii = {
        "applicant": "王五",
        "id_card": "110101********2345",
    }
    res_clean = ledger.verify_gate_compliance("applicant", clean_pii)
    assert res_clean["compliant"] is True


def test_spec_ledger_gate_03_offer_prereq():
    ledger = HRSpecLedger()
    # 跳过初筛面试直接发 offer
    skip_offer = {
        "applicant": "赵六",
        "stage_history": ["Applied"],
        "action": "issue_offer",
    }
    res_skip = ledger.verify_gate_compliance("offer", skip_offer)
    assert res_skip["compliant"] is False
    assert any("GATE-03" in v for v in res_skip["violations"])

    # 完整流程合规发 offer
    valid_offer = {
        "applicant": "赵六",
        "stage_history": ["Applied", "Screening_Passed", "Interview_Passed", "Shortlisted"],
        "prior_status": "Shortlisted",
    }
    res_valid = ledger.verify_gate_compliance("offer", valid_offer)
    assert res_valid["compliant"] is True


def test_spec_ledger_gate_04_05_leave_balance_and_overlap():
    ledger = HRSpecLedger()
    # 超额休假
    over_leave = {
        "employee": "EMP001",
        "leave_days": 10.0,
        "leave_balance": 5.0,
    }
    res_over = ledger.verify_gate_compliance("leave", over_leave)
    assert res_over["compliant"] is False
    assert any("GATE-04" in v for v in res_over["violations"])

    # 假期区间重叠
    overlap_leaves = {
        "leave_records": [
            {"from_date": "2026-11-01", "to_date": "2026-11-05"},
            {"from_date": "2026-11-03", "to_date": "2026-11-07"},
        ]
    }
    res_overlap = ledger.verify_gate_compliance("leave", overlap_leaves)
    assert res_overlap["compliant"] is False
    assert any("GATE-05" in v for v in res_overlap["violations"])


def test_spec_ledger_gate_06_policy_trace():
    ledger = HRSpecLedger()
    # 缺失制度溯源行
    no_policy = {
        "gross_pay": 20000.0,
        "net_pay": 15000.0,
        "total_deductions": 5000.0,
        "statutory_base": 20000.0,
    }
    res_no = ledger.verify_gate_compliance("payroll_calc", no_policy)
    assert res_no["compliant"] is False
    assert any("GATE-06" in v for v in res_no["violations"])

    # 携带制度溯源行
    with_policy = {
        "gross_pay": 20000.0,
        "net_pay": 15000.0,
        "total_deductions": 5000.0,
        "statutory_base": 20000.0,
        "source_policy": "京人社发〔2026〕12号社保缴费基数上下限及法定免税额标准",
    }
    res_with = ledger.verify_gate_compliance("payroll_calc", with_policy)
    assert res_with["compliant"] is True


def test_spec_ledger_gate_07_expense_consistency():
    ledger = HRSpecLedger()
    # 报销总额不一致
    bad_expense = {
        "total_claimed_amount": 1000.0,
        "expense_details": [
            {"item": "打车费", "amount": 200.0},
            {"item": "招待餐费", "amount": 600.0},  # 合计 800 != 1000
        ],
    }
    res_bad = ledger.verify_gate_compliance("claim", bad_expense)
    assert res_bad["compliant"] is False
    assert any("GATE-07" in v for v in res_bad["violations"])

    # 合规报销
    good_expense = {
        "total_claimed_amount": 800.0,
        "expense_details": [
            {"item": "打车费", "amount": 200.0},
            {"item": "招待餐费", "amount": 600.0},
        ],
    }
    res_good = ledger.verify_gate_compliance("claim", good_expense)
    assert res_good["compliant"] is True


def test_spec_ledger_gate_08_handoff_redline():
    ledger = HRSpecLedger()
    # 擅自发薪无 handoff
    direct_payout = {
        "action": "execute_payout",
        "amount": 50000.0,
    }
    res_payout = ledger.verify_gate_compliance("payroll_payout", direct_payout)
    assert res_payout["compliant"] is False
    assert any("GATE-08" in v for v in res_payout["violations"])

    # 包含向财务移交的 handoff
    handoff_payout = {
        "action": "execute_payout",
        "amount": 50000.0,
        "handoff_declared": True,
        "handoff_to": "R03 蛙财神 · 财务与清算总监",
    }
    res_handoff = ledger.verify_gate_compliance("payroll_payout", handoff_payout)
    assert res_handoff["compliant"] is True


# =========================================================================
# L05 质感去劣化引擎测试 (HRSlopGuard / SlopGuard)
# =========================================================================

def test_slop_guard_audit_and_clean():
    guard = HRSlopGuard()
    dirty_text = "本月团队整体稳定，目前按需招聘，新员工表现良好，考勤正常，相关细节待定，管理层高度重视。"
    audit_res = guard.audit(dirty_text)

    assert audit_res["has_slop"] is True
    assert audit_res["slop_count"] >= 5
    assert audit_res["status"] in ("HEALED", "WARN")
    assert "TOR" in audit_res["cleaned_text"]
    assert "PRA" or "OTA" in audit_res["cleaned_text"]
    assert "R16 蛙人事" in audit_res["cleaned_text"]

    cleaned = guard.clean(dirty_text)
    assert "团队整体稳定" not in cleaned
    assert "相关细节待定" not in cleaned

    # 测试审计报告渲染
    report = guard.generate_diff_report(audit_res)
    assert "Anti-Slop Report" in report
    assert "套话检出数" in report


def test_slop_guard_clean_text():
    guard = SlopGuard()
    clean_text = "经实算本月离职流动率 TOR 为 1.2%，薪酬记录准度 PRA 达 100.0%，由 R16 蛙人事完成 24 小时内归档。"
    audit_res = guard.audit(clean_text)
    assert audit_res["has_slop"] is False
    assert audit_res["slop_count"] == 0
    assert audit_res["actionability_score"] >= 80.0
    assert audit_res["status"] == "PASS"


# =========================================================================
# L06 横向决策层测试 (HRScenarioMatrix / ScenarioMatrix)
# =========================================================================

def test_scenario_matrix_generation():
    matrix = HRScenarioMatrix()
    scenarios = matrix.generate(
        role_title="高级全栈工程师",
        headcount=2,
        base_monthly_salary=20000.0,
    )
    assert len(scenarios) == 3

    # 验证方案代号与名称
    ids = [sc["id"] for sc in scenarios]
    assert "SCN_A_CONTINGENT" in ids
    assert "SCN_B_FTE" in ids
    assert "SCN_C_GRADUATE" in ids

    # 验证方案 B 为推荐全职方案
    rec = [sc for sc in scenarios if sc["is_recommended"]]
    assert len(rec) == 1
    assert rec[0]["id"] == "SCN_B_FTE"
    assert rec[0]["roi_score"] == 9.5

    # 验证 5 维量化指标
    for sc in scenarios:
        assert "lead_time_days" in sc
        assert "monthly_cost_per_person" in sc
        assert "total_monthly_cost" in sc
        assert "turnover_risk" in sc
        assert "retention_value" in sc
        assert "roi_score" in sc
        assert sc["headcount"] == 2
        assert sc["total_monthly_cost"] == round(sc["monthly_cost_per_person"] * 2, 2)


def test_scenario_matrix_markdown_rendering():
    matrix = ScenarioMatrix()
    scenarios = matrix.generate(role_title="人事专员", headcount=1, base_monthly_salary=10000.0)
    md = matrix.render_markdown(scenarios)
    assert "用工决策三维裂变权衡看板" in md
    assert "SCN_A_CONTINGENT" in md
    assert "SCN_B_FTE" in md
    assert "SCN_C_GRADUATE" in md
    assert "⭐ 推荐" in md
    assert "决策专家建议" in md
