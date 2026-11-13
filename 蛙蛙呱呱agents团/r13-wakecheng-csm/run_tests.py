#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R13 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 8 技能 16 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / demo / run_task /
重依赖探测(probe 恒 ok=true 如实降级) / verify_loop 闭环矩阵(T15)。

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

from skills import (s01_crm, s02_pipeline, s03_activity, s04_support,  # noqa: E402
                    s05_voc, s06_health, s07_knowledge, s08_automation)
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
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": (proc.stdout or "")[-4000:],
                             "_stderr": (proc.stderr or "")[-2000:]}


def _ex(name):
    return os.path.join(HERE, "examples", name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("8 个技能", len(m.get("skills", [])) == 8, str(len(m.get("skills", []))))
    t.check("角色 r13", m.get("role") == "r13")
    t.check("输入端口 lead/order_status",
            m.get("inputs") == ["lead", "order_status"])
    t.check("输出端口 crm_record/voc",
            m.get("outputs") == ["crm_record", "voc"])
    t.check("8 个能力域", len(m.get("capabilities", [])) == 8,
            str(len(m.get("capabilities", []))))

    t.section("S01 客户与联系人管理")
    r = s01_crm._validate_person(c.load_json(_ex("person.json")))
    t.check("person 干净通过", r["ok"], str(r.get("checks")))
    t.check("person channel_count=2", r["channel_count"] == 2, str(r["channel_count"]))
    t.check("person timeline_count=3", r["timeline_count"] == 3, str(r["timeline_count"]))
    t.check("person 脏数据拦截",
            not s01_crm._validate_person(c.load_json(_ex("person_dirty.json")))["ok"])
    t.check("person 渠道越界拦截",
            not s01_crm._validate_person(
                {"person": {"name": "a", "lifecycle": "lead",
                            "channels": [{"type": "fax", "value": "1"}],
                            "timeline": []}})["ok"])
    r = s01_crm._validate_company(c.load_json(_ex("company.json")))
    t.check("company 干净通过", r["ok"], str(r.get("checks")))
    t.check("company person_count=2", r["person_count"] == 2, str(r["person_count"]))
    t.check("company opp_count=1", r["opp_count"] == 1, str(r["opp_count"]))
    t.check("company 脏数据拦截",
            not s01_crm._validate_company(
                c.load_json(_ex("company_dirty.json")))["ok"])

    t.section("S02 销售管道")
    r = s02_pipeline._validate_pipeline(c.load_json(_ex("pipeline.json")))
    t.check("pipeline 干净通过", r["ok"], str(r.get("checks")))
    t.check("pipeline opp_count=4", r["opp_count"] == 4, str(r["opp_count"]))
    t.check("pipeline stage_count=4", r["stage_count"] == 4, str(r["stage_count"]))
    t.check("pipeline 加权值=890000",
            abs(r["weighted_value"] - 890000.0) < 0.01, str(r["weighted_value"]))
    t.check("pipeline HHI=0.4199",
            abs(r["concentration_hhi"] - 0.4199) < 0.001, str(r["concentration_hhi"]))
    t.check("pipeline 脏数据拦截",
            not s02_pipeline._validate_pipeline(
                c.load_json(_ex("pipeline_dirty.json")))["ok"])
    t.check("pipeline 集中度越界拦截",
            not s02_pipeline._validate_pipeline(
                {"opportunities": [
                    {"name": "a", "stage": "NEW", "amount": 900000,
                     "company": "唯一客户", "owner": "x", "next_step": "y"},
                    {"name": "b", "stage": "MEETING", "amount": 100000,
                     "company": "其它", "owner": "x", "next_step": "y"}]})["ok"])
    r = s02_pipeline._validate_opp(c.load_json(_ex("opp.json")))
    t.check("opp 干净通过", r["ok"], str(r.get("checks")))
    t.check("opp 加权值=360000",
            abs(r["weighted_value"] - 360000.0) < 0.01, str(r["weighted_value"]))
    t.check("opp 脏数据拦截",
            not s02_pipeline._validate_opp(c.load_json(_ex("opp_dirty.json")))["ok"])

    t.section("S03 销售活动与跟进")
    r = s03_activity._validate_activity(c.load_json(_ex("activity.json")))
    t.check("activity 干净通过", r["ok"], str(r.get("checks")))
    t.check("activity activity_count=3", r["activity_count"] == 3)
    t.check("activity overdue_count=0", r["overdue_count"] == 0)
    t.check("activity 脏数据拦截",
            not s03_activity._validate_activity(
                c.load_json(_ex("activity_dirty.json")))["ok"])
    r = s03_activity._validate_log(c.load_json(_ex("log.json")))
    t.check("log 干净通过", r["ok"], str(r.get("checks")))
    t.check("log 脏数据拦截",
            not s03_activity._validate_log(c.load_json(_ex("log_dirty.json")))["ok"])

    t.section("S04 全渠道客服")
    r = s04_support._validate_inbox(c.load_json(_ex("inbox.json")))
    t.check("inbox 干净通过", r["ok"], str(r.get("checks")))
    t.check("inbox ticket_count=4", r["ticket_count"] == 4)
    t.check("inbox avg_csat=4.5", abs(r["avg_csat"] - 4.5) < 0.01, str(r["avg_csat"]))
    t.check("inbox 脏数据拦截",
            not s04_support._validate_inbox(c.load_json(_ex("inbox_dirty.json")))["ok"])
    t.check("inbox CSAT 低分拦截",
            not s04_support._validate_inbox(
                {"conversations": [{"id": "a", "channel": "email",
                                    "status": "resolved", "csat": 2}]})["ok"])
    r = s04_support._validate_ticket(c.load_json(_ex("ticket.json")))
    t.check("ticket 干净通过", r["ok"], str(r.get("checks")))
    t.check("ticket message_count=3", r["message_count"] == 3)
    t.check("ticket 脏数据拦截",
            not s04_support._validate_ticket(
                c.load_json(_ex("ticket_dirty.json")))["ok"])

    t.section("S05 客户反馈与 VOC")
    r = s05_voc._validate_survey(c.load_json(_ex("survey.json")))
    t.check("survey 干净通过", r["ok"], str(r.get("checks")))
    t.check("survey element_count=3", r["element_count"] == 3)
    t.check("survey 脏数据拦截",
            not s05_voc._validate_survey(c.load_json(_ex("survey_dirty.json")))["ok"])
    r = s05_voc._validate_voc(c.load_json(_ex("voc.json")))
    t.check("voc 干净通过", r["ok"], str(r.get("checks")))
    t.check("voc NPS=20.0", abs(r["nps_score"] - 20.0) < 0.01, str(r["nps_score"]))
    t.check("voc promoter=5", r["promoter_count"] == 5, str(r["promoter_count"]))
    t.check("voc detractor=3", r["detractor_count"] == 3, str(r["detractor_count"]))
    t.check("voc theme_count>=1", r["theme_count"] >= 1, str(r["theme_count"]))
    t.check("voc 脏数据拦截",
            not s05_voc._validate_voc(c.load_json(_ex("voc_dirty.json")))["ok"])

    t.section("S06 客户健康与续约")
    r = s06_health._validate_health(c.load_json(_ex("health.json")))
    t.check("health 干净通过", r["ok"], str(r.get("checks")))
    t.check("health customer_count=4", r["customer_count"] == 4)
    t.check("health avg_health=66.4", abs(r["avg_health"] - 66.4) < 0.01, str(r["avg_health"]))
    t.check("health at_risk_count=1", r["at_risk_count"] == 1, str(r["at_risk_count"]))
    t.check("health 续约候选=云启科技",
            r["renewal_candidates"] == ["云启科技"], str(r["renewal_candidates"]))
    t.check("health 脏数据拦截",
            not s06_health._validate_health(c.load_json(_ex("health_dirty.json")))["ok"])
    r = s06_health._validate_risk(c.load_json(_ex("risk.json")))
    t.check("risk 干净通过", r["ok"], str(r.get("checks")))
    t.check("risk 健康分=79.0", abs(r["health_score"] - 79.0) < 0.01, str(r["health_score"]))
    t.check("risk band=healthy", r["band"] == "healthy", str(r["band"]))
    t.check("risk 单维崩坏却判 healthy 拦截",
            not s06_health._validate_risk(
                c.load_json(_ex("risk_dirty.json")))["ok"])

    t.section("S07 服务知识与升级")
    r = s07_knowledge._validate_faq(c.load_json(_ex("faq.json")))
    t.check("faq 干净通过", r["ok"], str(r.get("checks")))
    t.check("faq faq_count=3", r["faq_count"] == 3)
    t.check("faq 脏数据拦截（重复 + 短答 + 缺 owner）",
            not s07_knowledge._validate_faq(c.load_json(_ex("faq_dirty.json")))["ok"])
    r = s07_knowledge._validate_escalation(c.load_json(_ex("escalation.json")))
    t.check("escalation 干净通过", r["ok"], str(r.get("checks")))
    t.check("escalation route=r07", r["route"] == "r07", str(r["route"]))
    t.check("escalation 脏数据拦截（越界路由 + 缺证据）",
            not s07_knowledge._validate_escalation(
                c.load_json(_ex("escalation_dirty.json")))["ok"])

    t.section("S08 客户运营自动化接口")
    r = s08_automation._validate_automation(c.load_json(_ex("automation.json")))
    t.check("automation 干净通过", r["ok"], str(r.get("checks")))
    t.check("automation field_count=2", r["field_count"] == 2)
    t.check("automation high_risk=false", r["high_risk"] is False)
    t.check("automation 敏感字段禁入拦截",
            not s08_automation._validate_automation(
                c.load_json(_ex("automation_dirty.json")))["ok"])
    t.check("automation 高危动作缺审批点拦截",
            not s08_automation._validate_automation(
                {"trigger": "manual", "condition": "c", "action": "automatic refund",
                 "owner": "r13", "approval_point": "", "audit": "a",
                 "fields": []})["ok"])
    probe = s08_automation._probe()
    t.check("automation probe 恒 ok=true（如实降级）",
            probe["ok"] and probe["verdict"] == "PASS", f"status={probe.get('status')}")
    t.check("automation probe 带 status", probe.get("status") in ("ready", "blocked"))

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 8 技能", len(names) == 8, str(len(names)))
    total_actions = sum(len(contracts.actions(s)) for s in names)
    t.check("契约覆盖 16 动作", total_actions == 16, str(total_actions))
    v = contracts.validate_output("pipeline", "pipeline",
                                  s02_pipeline._validate_pipeline(
                                      c.load_json(_ex("pipeline.json"))))
    t.check("契约校验 pipeline 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截",
            not contracts.validate_output("pipeline", "pipeline", {"ok": True})["ok"])
    t.check("契约校验未知动作拦截",
            not contracts.validate_output("pipeline", "nope", {"ok": True})["ok"])
    t.check("契约校验未知技能拦截",
            not contracts.validate_output("nope", "pipeline", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "pipeline", "action": "pipeline",
                   "result": s02_pipeline._validate_pipeline(
                       c.load_json(_ex("pipeline.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "承诺退款并保证效果"}})
    t.check("评审拦截擅自承诺退款/效果", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "unauthorized_promise",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "summary": "我来定投放策略和广告预算"}})
    t.check("评审拦截越界定投放策略", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "summary": "爬取个人信息补充客户画像"}})
    t.check("评审拦截未授权采集", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "privacy_unauthorized",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "这里内容待定，稍后补充"}})
    t.check("评审拦截无具体产物", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 >= 2 个", len(lst) >= 2, str([x["case_id"] for x in lst]))
    for cid in ("pipeline-rescue", "renewal-health"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    if "churn-warning" in [x["case_id"] for x in lst]:
        vc = cases.validate_case("churn-warning")
        t.check("churn-warning 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("pipeline-rescue")
    t.check("案例阈值可覆盖全局", merged["pipeline"]["stall_days_max"] == 10,
            str(merged["pipeline"].get("stall_days_max")))

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("pipeline 阶段白名单外置", len(th["pipeline"]["stages"]) == 7)
    t.check("support 渠道白名单外置", len(th["support"]["channel_types"]) == 9)
    t.check("voc 题型白名单外置（17 种官方题型）",
            len(th["voc"]["element_types"]) == 17)
    t.check("health 权重外置", sum(th["health"]["weights"].values()) == 100)
    t.check("knowledge 升级路由外置", len(th["knowledge"]["escalation_routes"]) == 4)
    t.check("automation 敏感字段禁入外置",
            "api_key" in th["automation"]["forbidden_fields"])
    t.check("review 红线词外置", bool(th["review"]["promise_words"])
            and bool(th["review"]["scope_terms"])
            and bool(th["review"]["privacy_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r13_harness_")
    good_path = os.path.join(tmp, "pipeline.json")
    c.write_json(good_path, c.load_json(_ex("pipeline.json")))
    h = harness.run_validator("pipeline", good_path)
    t.check("harness pipeline 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"opportunities": []})
    h = harness.run_validator("pipeline", bad_path)
    t.check("harness pipeline 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("pipeline", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    pr = harness.probe("automation")
    t.check("harness probe automation 恒 PASS", pr["ok"] and pr["grade"] == "PASS")
    t.check("15 个门禁全部登记", len(harness._VALIDATORS) == 15,
            str(len(harness._VALIDATORS)))

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4,
            str(demo.get("demo_artifacts", {}).keys()))

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(os.path.join(HERE, "examples", "pipeline.json"), "data", note="")
    task = protocol.Task(title="看一下销售管道健康度", owner="r13",
                         intent="帮我看一下销售管道，哪些商机停滞了、加权预测多少",
                         inputs=[inp], acceptance=["pipeline 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 pipeline", res.get("skill") == "pipeline",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    t.check("闭环 30 行全绿", matrix["ok"],
            f"passed={matrix['passed']}/{matrix['total']} "
            f"bad={[r['skill'] + ':' + ','.join(r.get('notes', [])) for r in matrix['matrix'] if not r['ok']][:3]}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R13 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
