#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R16 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能 16 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7，含三条 R16 红线) / 案例库(T8) / 阈值外置(T9) / harness / demo /
run_task / verify_loop 闭环矩阵(T15)。

用法：
    python run_tests.py          # 全量
    python run_tests.py --verbose
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
for p in (HERE, AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

# Windows 中文控制台默认 GBK，直接 print 中文会乱码/抛错（R07 踩坑，全角色同款）。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from skills import (s01_recruit, s02_people, s03_attendance, s04_performance,  # noqa: E402
                    s05_payroll, s06_expense, s07_report)
from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases  # noqa: E402
import harness  # noqa: E402
import verify_loop  # noqa: E402


class T:
    def __init__(self, verbose=False):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.verbose = verbose

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  ok  {name}")
        else:
            self.failed += 1
            self.errors.append((name, detail))
            print(f"FAIL  {name}" + (f"  -> {detail}" if detail else ""))

    def section(self, title):
        print(f"\n== {title} ==")


def run_agent(*args):
    """运行 agent.py 并解析 __AGENT_RESULT__。返回 (exit_code, dict)。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": (proc.stdout or "")[-4000:],
                             "_stderr": (proc.stderr or "")[-2000:]}


def _ex(name):
    return os.path.join(HERE, "examples", name)


def _fail_msgs(r):
    return [x["msg"] for x in r.get("checks", []) if not x["ok"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    # ------------------------------------------------------------------ #
    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("7 个技能", len(m.get("skills", [])) == 7, str(len(m.get("skills", []))))
    t.check("角色 r16", m.get("role") == "r16", str(m.get("role")))
    t.check("输入端口 org_decision/roles",
            m.get("inputs") == ["org_decision", "roles"], str(m.get("inputs")))
    t.check("输出端口 roster/payroll_input",
            m.get("outputs") == ["roster", "payroll_input"], str(m.get("outputs")))
    t.check("7 个能力域", len(m.get("capabilities", [])) == 7,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 招聘与入职")
    r = s01_recruit._validate_opening(c.load_json(_ex("opening.json")))
    t.check("opening 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("vacancies=2", r["vacancies"] == 2, str(r["vacancies"]))
    r = s01_recruit._validate_opening(c.load_json(_ex("opening_dirty.json")))
    t.check("opening 脏数据拦截", not r["ok"])
    t.check("opening 拦截空职位名", any("必填" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("opening 拦截 vacancies=0", any("招聘人数" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_recruit._validate_applicant(c.load_json(_ex("applicant.json")))
    t.check("applicant 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("applicant status=Shortlisted", r["status"] == "Shortlisted", str(r["status"]))
    r = s01_recruit._validate_applicant(c.load_json(_ex("applicant_dirty.json")))
    t.check("applicant 脏数据拦截", not r["ok"])
    t.check("applicant 拦截非法邮箱", any("邮箱" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("applicant 拦截状态越界", any("状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_recruit._validate_offer(c.load_json(_ex("offer.json")))
    t.check("offer 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("offer 前置合法（Shortlisted）", r["status"] == "Accepted", str(r["status"]))
    r = s01_recruit._validate_offer(c.load_json(_ex("offer_dirty.json")))
    t.check("offer 脏数据拦截（跳过筛选）", not r["ok"])
    t.check("offer 拦截前置 Open", any("前置状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 人员与合同档案")
    r = s02_people._validate_employee(c.load_json(_ex("employee.json")))
    t.check("employee 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("employee status=Active", r["status"] == "Active", str(r["status"]))
    r = s02_people._validate_employee(c.load_json(_ex("employee_dirty.json")))
    t.check("employee 脏数据拦截", not r["ok"])
    t.check("employee 拦截时序（出生晚于入职）",
            any("出生早于入职" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("employee 拦截状态越界", any("在职状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("employee 拦截 PII 越界（id_card）",
            any("超必要个人信息" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s02_people._validate_profile(c.load_json(_ex("profile.json")))
    t.check("profile 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("profile contact_count=1", r["contact_count"] == 1, str(r["contact_count"]))
    r = s02_people._validate_profile(c.load_json(_ex("profile_dirty.json")))
    t.check("profile 脏数据拦截", not r["ok"])
    t.check("profile 拦截空联系人字段",
            any("联系人姓名与电话" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("profile 拦截空附件", any("附件" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s02_people._validate_contract(c.load_json(_ex("contract.json")))
    t.check("contract 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("contract days_left=20", r["days_left"] == 20, str(r["days_left"]))
    r = s02_people._validate_contract(c.load_json(_ex("contract_dirty.json")))
    t.check("contract 脏数据拦截（时序倒挂）", not r["ok"])
    t.check("contract 拦截起止顺序",
            any("顺序" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 考勤与休假")
    r = s03_attendance._validate_attendance(c.load_json(_ex("attendance.json")))
    t.check("attendance 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("attendance status=Present", r["status"] == "Present", str(r["status"]))
    r = s03_attendance._validate_attendance(c.load_json(_ex("attendance_dirty.json")))
    t.check("attendance 脏数据拦截", not r["ok"])
    t.check("attendance 拦截空 employee", any("必填" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("attendance 拦截状态越界", any("状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("attendance 拦截工时越界（30>24）",
            any("工作时长" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s03_attendance._validate_leave(c.load_json(_ex("leave.json")))
    t.check("leave 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("leave overlap_count=0", r["overlap_count"] == 0, str(r["overlap_count"]))
    r = s03_attendance._validate_leave(c.load_json(_ex("leave_dirty.json")))
    t.check("leave 脏数据拦截", not r["ok"])
    t.check("leave 拦截天数不恒等", any("天数恒等" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("leave 拦截超余额", any("余额" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("leave 拦截重叠", any("重叠" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 绩效与目标")
    r = s04_performance._validate_appraisal(c.load_json(_ex("appraisal.json")))
    t.check("appraisal 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("appraisal cycle=2026-H2", r["cycle"] == "2026-H2", str(r["cycle"]))
    r = s04_performance._validate_appraisal(c.load_json(_ex("appraisal_dirty.json")))
    t.check("appraisal 脏数据拦截", not r["ok"])
    t.check("appraisal 拦截总分越界（9>5）",
            any("总分" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("appraisal 拦截周期状态越界",
            any("周期状态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("appraisal 拦截 KRA 缺分",
            any("打分数" in x or "打分完" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s04_performance._validate_goal(c.load_json(_ex("goal.json")))
    t.check("goal 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("goal progress=100", r["progress"] == 100, str(r["progress"]))
    r = s04_performance._validate_goal(c.load_json(_ex("goal_dirty.json")))
    t.check("goal 脏数据拦截（伪完成）", not r["ok"])
    t.check("goal 拦截 Completed 不满进度",
            any("已完成" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("goal 拦截 KRA 缺量化",
            any("KRA 引用" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 薪酬准备（L4 制度性幻觉防护）")
    r = s05_payroll._validate_input(c.load_json(_ex("payroll_input.json")))
    t.check("payroll_input 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("payroll component_count=3", r["component_count"] == 3, str(r["component_count"]))
    r = s05_payroll._validate_input(c.load_json(_ex("payroll_input_dirty.json")))
    t.check("payroll_input 脏数据拦截", not r["ok"])
    t.check("payroll_input 拦截频率越界",
            any("频率" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("payroll_input 拦截类型越界",
            any("类型合法" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("payroll_input 拦截无 source",
            any("来源" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s05_payroll._validate_calc(c.load_json(_ex("payroll_calc.json")))
    t.check("payroll_calc 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("payroll 净额=18000", abs(r["net_pay"] - 18000.0) < 0.01, str(r["net_pay"]))
    t.check("payroll 毛额=20000", abs(r["gross_pay"] - 20000.0) < 0.01, str(r["gross_pay"]))
    r = s05_payroll._validate_calc(c.load_json(_ex("payroll_calc_dirty.json")))
    t.check("payroll_calc 脏数据拦截", not r["ok"])
    t.check("payroll 拦截净额不恒等", any("净额恒等" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("payroll 拦截计薪天数越界", any("计薪天数" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("payroll 拦截凭空制度字段（L4）",
            any("可溯源" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 费用与福利")
    r = s06_expense._validate_claim(c.load_json(_ex("claim.json")))
    t.check("claim 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("claim total_amount=350", abs(r["total_amount"] - 350.0) < 0.01,
            str(r["total_amount"]))
    r = s06_expense._validate_claim(c.load_json(_ex("claim_dirty.json")))
    t.check("claim 脏数据拦截", not r["ok"])
    t.check("claim 拦截审批态越界",
            any("审批状态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("claim 拦截金额不恒等", any("金额恒等" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_expense._validate_benefit(c.load_json(_ex("benefit.json")))
    t.check("benefit 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("benefit amount=500", abs(r["amount"] - 500.0) < 0.01, str(r["amount"]))
    r = s06_expense._validate_benefit(c.load_json(_ex("benefit_dirty.json")))
    t.check("benefit 脏数据拦截", not r["ok"])
    t.check("benefit 拦截空周期", any("薪酬周期" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("benefit 拦截超上限", any("上限" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 组织运营报表")
    r = s07_report._validate_headcount(c.load_json(_ex("headcount.json")))
    t.check("headcount 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("headcount=5", r["headcount"] == 5, str(r["headcount"]))
    r = s07_report._validate_headcount(c.load_json(_ex("headcount_dirty.json")))
    t.check("headcount 脏数据拦截（分组不恒等）", not r["ok"])
    t.check("headcount 拦截分组不等总数",
            any("分组计数恒等" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s07_report._validate_report(c.load_json(_ex("report.json")))
    t.check("report 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("report metric_count=3", r["metric_count"] == 3, str(r["metric_count"]))
    r = s07_report._validate_report(c.load_json(_ex("report_dirty.json")))
    t.check("report 脏数据拦截", not r["ok"])
    t.check("report 拦截负值", any("非负" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("report 拦截未知字段", any("白名单" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("report 拦截流动率不恒等", any("流动率恒等" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("T6 契约")
    t.check("7 技能登记", len(contracts.skill_names()) == 7,
            str(contracts.skill_names()))
    total_actions = sum(len(contracts.actions(s)) for s in contracts.skill_names())
    t.check("16 动作登记", total_actions == 16, str(total_actions))
    for s in contracts.skill_names():
        for a in contracts.actions(s):
            vi = contracts.validate_input(s, a, {})
            t.check(f"{s}/{a} 输入契约拒绝空对象", not vi["ok"], str(vi["errors"]))
    vo = contracts.validate_output("recruit", "offer",
                                   s01_recruit._validate_offer(
                                       c.load_json(_ex("offer.json"))))
    t.check("输出契约校验干净产出通过", vo["ok"], str(vo["errors"]))
    vo = contracts.validate_output("recruit", "offer", {"ok": True})
    t.check("输出契约拒绝缺 checks", not vo["ok"], str(vo["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审（含三条 R16 红线）")
    good_packet = {"skill": "recruit", "action": "offer",
                   "result": s01_recruit._validate_offer(
                       c.load_json(_ex("offer.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"payroll_input_count": 1, "checks": [],
                                           "summary": "我直接发薪给员工"}})
    t.check("红线1 拦截擅自发薪", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "unauthorized_hr_action",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"employee_count": 1, "checks": [],
                                           "summary": "收集了身份证号和家庭住址"}})
    t.check("红线2 拦截过度收集个人信息", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "pii_overreach",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"payroll_input_count": 1, "checks": [],
                                           "summary": "给出个税申报结论"}})
    t.check("红线3 拦截税务越界", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "稍后补充"}})
    t.check("评审拦截无具体工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"offer_count": 1, "checks": [],
                                           "summary": "录用需人工授权后执行",
                                           "handoff": "用人部门负责人"}})
    t.check("已声明 handoff 的录用产出通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"payroll_input_count": 1, "checks": [],
                                           "summary": "个税结论需移交",
                                           "handoff": "R03"}})
    t.check("已声明 handoff 的税务越界通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 >= 2 个", len(lst) >= 2, str([x["case_id"] for x in lst]))
    for cid in ("hiring-pipeline", "payroll-preparation"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("hiring-pipeline")
    t.check("案例阈值可覆盖全局",
            merged["offer"].get("accept_prior_statuses") == ["Shortlisted", "Accepted"],
            str(merged["offer"].get("accept_prior_statuses")))
    t.check("案例覆盖不破坏全局键",
            merged["payroll"]["tolerance"] == 0.01,
            str(merged["payroll"].get("tolerance")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("opening 状态白名单外置", len(th["opening"]["statuses"]) == 2)
    t.check("applicant 状态白名单外置", len(th["applicant"]["statuses"]) == 6)
    t.check("offer 状态白名单外置", len(th["offer"]["statuses"]) == 6)
    t.check("offer 前置集合外置",
            th["offer"]["accept_prior_statuses"] == ["Shortlisted", "Accepted"])
    t.check("employee 状态白名单外置", len(th["employee"]["statuses"]) == 4)
    t.check("contract 到期窗口外置", th["contract"]["expiry_window_days"] == 30)
    t.check("attendance 状态白名单外置", len(th["attendance"]["statuses"]) == 5)
    t.check("leave 半日值外置", th["leave"]["half_day_value"] == 0.5)
    t.check("appraisal 评分区间外置",
            th["appraisal"]["score_min"] == 0.0 and th["appraisal"]["score_max"] == 5.0)
    t.check("goal 进度区间外置", th["goal"]["progress_max"] == 100.0)
    t.check("payroll 频率白名单外置", len(th["payroll"]["frequencies"]) == 5)
    t.check("payroll 容差外置", th["payroll"]["tolerance"] == 0.01)
    t.check("expense 双轨状态外置",
            len(th["expense"]["approval_statuses"]) == 4
            and len(th["expense"]["statuses"]) == 7)
    t.check("report 指标白名单外置", len(th["report"]["metric_fields"]) == 5)
    t.check("review 三条红线词外置",
            bool(th["review"]["unauthorized_hr_words"])
            and bool(th["review"]["pii_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r16_harness_")
    good_path = os.path.join(tmp, "leave.json")
    c.write_json(good_path, c.load_json(_ex("leave.json")))
    h = harness.run_validator("leave", good_path)
    t.check("harness leave 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("leave", _ex("leave_dirty.json"))
    t.check("harness leave 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("leave", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    t.check("16 个门禁全部登记", len(harness._VALIDATORS) == 16,
            str(len(harness._VALIDATORS)))
    code, rl = run_agent("harness", "runlog", "--n", "5")
    t.check("harness runlog 可读", code == 0 or "runlog" in rl, str(rl)[:120])

    # ------------------------------------------------------------------ #
    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0
            and len(demo.get("demo_artifacts", {})) == 14,
            str(len(demo.get("demo_artifacts", {}))))
    code, _ = run_agent("case", "get", "--case", "hiring-pipeline")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 7)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("leave.json"), "data", note="")
    task = protocol.Task(title="员工请假三天",
                         owner="r16",
                         intent="员工申请年假三天，帮我看天数对不对、额度够不够",
                         inputs=[inp], acceptance=["leave 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 attendance", res.get("skill") == "attendance",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：录用→recruit
    inp2 = protocol.Port(_ex("offer.json"), "data", note="")
    task2 = protocol.Task(title="录用候选人", owner="r16",
                          intent="帮我看这份录用通知能不能发，候选人前置状态合不合法",
                          inputs=[inp2], acceptance=["recruit 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 录用→recruit", res2.get("skill") == "recruit",
            str(res2.get("skill")))

    # 意图路由：薪酬→payroll
    inp3 = protocol.Port(_ex("payroll_calc.json"), "data", note="")
    task3 = protocol.Task(title="薪酬核算", owner="r16",
                          intent="帮我核算这个月工资，净额对不对",
                          inputs=[inp3], acceptance=["payroll 门禁通过"])
    ws.create_task(task3)
    code, res3 = run_agent("run", "--task", task3.task_id)
    t.check("意图路由 薪酬→payroll", res3.get("skill") == "payroll",
            str(res3.get("skill")))

    # ------------------------------------------------------------------ #
    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    bad_rows = [r["skill"] + ":" + ",".join(r.get("notes", []))
                for r in matrix["matrix"] if not r["ok"]]
    t.check("闭环 32 行全绿", matrix["ok"],
            f"passed={matrix['passed']}/{matrix['total']} bad={bad_rows[:3]}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")
    n_clean = sum(1 for r in matrix["matrix"] if r["expect_ok"])
    n_dirty = sum(1 for r in matrix["matrix"] if not r["expect_ok"])
    t.check("闭环 16 干净 + 16 脏", n_clean == 16 and n_dirty == 16,
            f"clean={n_clean} dirty={n_dirty}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R16 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
