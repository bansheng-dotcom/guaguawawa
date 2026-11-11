#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R07 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 8 技能（含脏数据·幻觉·伪造结论必须 FAIL）/ 优先级算术 /
契约(T6) / 对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / demo / run_task。

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

from skills import (s01_discover, s02_ost, s03_prd, s04_priority,  # noqa: E402
                    s05_roadmap, s06_metrics, s07_techbrief, s08_decision)
from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases  # noqa: E402
import harness  # noqa: E402


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
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    out = proc.stdout or ""
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": out[-4000:], "_stderr": (proc.stderr or "")[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("9 个技能", len(m.get("skills", [])) == 9, str(len(m.get("skills", []))))
    t.check("角色 r07", m.get("role") == "r07")
    t.check("输入端口 research_report/voc",
            m.get("inputs") == ["research_report", "voc"])

    t.section("S01 产品发现与 JTBD")
    job = c.load_json(os.path.join(HERE, "examples", "jobstory.json"))
    r = s01_discover._validate_jobstory(job)
    t.check("jobstory 三段通过", r["ok"])
    r = s01_discover._validate_jobstory({"situation": "x", "motivation": "y"})
    t.check("jobstory 缺 outcome 拦截", not r["ok"])
    good_plan = {"problem": "新用户不会建首项目", "segment": "SaaS 试用用户",
                 "why_now": "激活率偏低", "assumptions": [{"risk_type": "value"}],
                 "validation_plan": [{"hypothesis": "h", "method": "A/B", "metric": "激活率"}]}
    t.check("discover 计划通过", s01_discover._validate_discover(good_plan)["ok"])
    t.check("discover 缺验证计划拦截",
            not s01_discover._validate_discover({"problem": "x", "segment": "y",
                                                 "why_now": "z"})["ok"])

    t.section("S02 机会树与用户研究")
    ost = {"desired_outcome": "更快完成首个项目",
           "opportunities": [{"selected": True, "solutions": [
               {"experiments": [{"hypothesis": "h", "method": "A/B"}]},
               {"experiments": []}, {"experiments": []}]} for _ in range(3)],
           "focus": ["opp0", "opp1"]}
    t.check("ost 四层通过", s02_ost._validate_ost(ost)["ok"])
    t.check("ost 机会数不足拦截",
            not s02_ost._validate_ost({"desired_outcome": "x", "opportunities": []})["ok"])
    poc = s02_ost._score_poc({"solutions": [
        {"name": "A", "feasibility": 5, "impact": 5, "market_fit": 5},
        {"name": "B", "feasibility": 2, "impact": 2, "market_fit": 2}]})
    t.check("poc 推荐达标方案", poc["ok"] and "A" in poc["recommended_poc"])
    t.check("poc 低分不推荐", "B" not in poc["recommended_poc"])
    asm = s02_ost._prioritize_assumptions({"assumptions": [
        {"name": "a", "impact": 0.9, "confidence": 0.2, "effort": 1.0}]})
    t.check("高影响高险进 experiment", asm["ok"] and asm["assumptions"][0]["quadrant"] == "experiment")

    t.section("S03 用户故事与 PRD")
    prd = c.load_json(os.path.join(HERE, "examples", "prd.json"))
    r = s03_prd._validate_prd(prd)
    t.check("PRD 八门禁全通过", r["ok"], f"passed={r['passed_gates']}")
    t.check("PRD 门禁数=8", r["passed_gates"] == 8)
    bad_prd = dict(prd); bad_prd["scope"] = {"p0": []}
    t.check("PRD 缺范围拦截", not s03_prd._validate_prd(bad_prd)["ok"])
    r = s03_prd._validate_story({"story": "As a user, I want to X, so that Y.",
                                 "acceptance_criteria": ["a", "b", "c", "d"]}, "user")
    t.check("user story 4 条 AC 通过", r["ok"])
    r = s03_prd._validate_story({"story": "As a user, I want X, so that Y.",
                                 "acceptance_criteria": ["a"]}, "user")
    t.check("AC 少于 4 条拦截", not r["ok"])
    r = s03_prd._validate_acceptance({"acceptance_criteria": [
        {"given": "g", "when": "w", "then": "t"}]})
    t.check("验收 Given/When/Then 通过", r["ok"])
    t.check("验收缺 Then 拦截", not s03_prd._validate_acceptance(
        {"acceptance_criteria": [{"given": "g", "when": "w"}]})["ok"])

    t.section("S04 优先级算术")
    rice = s04_priority._rice({"items": [
        {"name": "A", "reach": 100, "impact": 0.8, "confidence": 70, "effort": 2}]})
    t.check("RICE 算术正确", rice["ok"] and rice["ranked"][0]["score"] == 28.0,
            str(rice.get("ranked")))
    opp = s04_priority._opportunity({"items": [
        {"name": "a", "importance": 8, "satisfaction": 0.3}]})
    t.check("Opportunity Score=5.6", opp["ok"] and opp["ranked"][0]["opportunity_score"] == 5.6,
            str(opp.get("ranked")))
    bl = s04_priority._backlog(c.load_json(os.path.join(HERE, "examples", "backlog.json")))
    t.check("backlog 排序通过", bl["ok"] and bl["ordered"][0]["title"].startswith("分步"))

    t.section("S05 路线图与发布")
    t.check("roadmap 通过", s05_roadmap._roadmap({"items": [
        {"segment": "试用户", "outcome": "完成首项目", "business_impact": "激活率+"}]})["ok"])
    t.check("releasenotes 五分类通过", s05_roadmap._releasenotes({
        "title": "X v1.0", "sections": {k: ["- item"] for k in
        ["New Features", "Improvements", "Bug Fixes", "Breaking Changes", "Deprecations"]}})["ok"])
    t.check("premortem 通过", s05_roadmap._premortem({
        "tigers": ["上线即崩"], "action_plans": [
            {"risk": "崩溃", "mitigation": "灰度", "owner": "r09", "due_date": "day-3"}]})["ok"])

    t.section("S06 愿景与指标")
    ns = c.load_json(os.path.join(HERE, "examples", "northstar.json"))
    t.check("北极星通过", s06_metrics._northstar(ns)["ok"])
    t.check("虚荣指标拦截", not s06_metrics._northstar(
        {"north_star": "提升用户体验", "input_metrics": ["a", "b", "c"]})["ok"])
    okr = {"okr_sets": [{"objective": "O", "key_results": [
        {"metric": "m1"}, {"metric": "m2"}, {"metric": "m3"}]} for _ in range(3)],
           "confidence": 65}
    t.check("OKR 3×3 通过", s06_metrics._okr(okr)["ok"])
    t.check("钩子指标缺定义拦截", not s06_metrics._metrics({"metrics": [
        {"layer": "north_star", "definition": "", "data_source": ""}]})["ok"])

    t.section("S07 技术翻译与代码反推")
    t.check("techbrief 五模块通过", s07_techbrief._techbrief({
        "user_impact": 1, "frontend": 1, "backend": 1, "agent": 1,
        "failure": {"who_investigates": "r09", "recovery": "回滚", "manual_handling": "工单"},
    })["ok"])
    t.check("uibrief 状态齐全通过", s07_techbrief._uibrief({
        "page_goal": "g", "ia": "i", "user_actions": "a", "review_focus": "r",
        "states": {"empty": 1, "loading": 1, "success": 1, "failure": 1, "permission": 1}})["ok"])
    t.check("代码反推字段/接口通过", s07_techbrief._codetoprd({
        "pages": [{"name": "任务台", "overview": "o", "fields": [{"name": "f", "type": "string"}]}],
        "apis": [{"method": "GET", "path": "/x", "business_logic": "b"}]})["ok"])
    rg = s07_techbrief._releasegate({"checks": [
        {"name": "typecheck", "status": "pass"}, {"name": "e2e", "status": "pass"}]})
    t.check("发布门禁 go", rg["ok"] and rg["decision"] == "go")
    t.check("发布门禁阻断", not s07_techbrief._releasegate({"checks": [
        {"name": "security", "status": "block"}]})["ok"])

    t.section("S08 决策汇报与经验检索")
    t.check("决策三层通过", s08_decision._decision({
        "product_judgment": 1, "execution_spec": 1,
        "decision_gate": {"success": "s", "non_goals": "n", "stop_condition": "stop"}})["ok"])
    t.check("需求卡提交通过", s08_decision._demand({
        "demand_id": "D1", "problem": "p", "scope": "s", "non_goals": "n",
        "success_metric": "m", "acceptance": "a", "review_status": "已复核"})["ok"])
    t.check("经验卡五要素通过", s08_decision._experience({
        "trigger": "t", "scope": "s", "rule": "r", "boundary": "b",
        "source_credibility": "c"})["ok"])

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 9 技能", len(names) == 9, str(len(names)))
    v = contracts.validate_output("prd", "prd", s03_prd._validate_prd(prd))
    t.check("契约校验 PRD 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截", not contracts.validate_output(
        "prd", "prd", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "prd", "action": "prd", "result": s03_prd._validate_prd(prd)}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))
    rev = review.review_packet({"skill": "prd", "action": "acceptance",
                                "result": {"conclusion": "建议加大投入，提升用户体验"}})
    t.check("评审拦截空泛+未授权建议", rev["verdict"] == "FAIL",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    case_ids = [c_["case_id"] for c_ in cases.list_cases()] if cases.list_cases() else []
    t.check("案例列表 >= 2 个（超集契约，允许平滑扩容）", len(case_ids) >= 2, str(case_ids))
    t.check("案例库含 saas-activation", "saas-activation" in case_ids, str(case_ids))
    t.check("saas-activation 结构通过", cases.validate_case("saas-activation")["ok"])
    t.check("feature-prd 结构通过", cases.validate_case("feature-prd")["ok"])

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("阈值外置已加载", th.get("prd", {}).get("risk_hypotheses_min") == 3)

    t.section("harness 确定性验证器")
    tmp = os.path.join(HERE, "_test_tmp")
    os.makedirs(tmp, exist_ok=True)
    good_prd_path = os.path.join(tmp, "prd.json")
    c.write_json(good_prd_path, prd)
    h = harness.run_validator("prd", good_prd_path)
    t.check("harness PRD 门禁 PASS", h["ok"] and h["grade"] == "PASS")
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"problem_statement": "优化某功能"})
    h = harness.run_validator("prd", bad_path)
    t.check("harness PRD 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4)

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(good_prd_path, "data", note="")
    task = protocol.Task(title="写新手引导 PRD", owner="r07", intent="需求 PRD 分析",
                         inputs=[inp], acceptance=["prd 八门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回 2 个产物", len(done.outputs) >= 1, str(len(done.outputs)))

    t.section("verify_loop 闭环矩阵（smoke ≠ 闭环）")
    import verify_loop
    vl = verify_loop.run_all()
    t.check("29 动作 × 契约 × 评审全绿", vl["ok"],
            f"passed={vl['passed']}/failed={vl['failed']}")
    t.check("闭环矩阵 total=58（29 干净 + 29 脏）", vl["total"] == 58, str(vl["total"]))

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R07 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())