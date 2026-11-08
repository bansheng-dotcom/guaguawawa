#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R12 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 9 技能（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / plan / demo / run_task /
重依赖探测(probe 恒 ok=true 如实降级)。

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

from skills import (s01_diagnose, s02_loops, s03_outreach, s04_partner,  # noqa: E402
                    s05_launch, s06_paid, s07_retention, s08_revops,
                    s09_selfmedia)
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
    out = proc.stdout
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": out[-4000:], "_stderr": proc.stderr[-2000:]}


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
    t.check("9 个技能", len(m.get("skills", [])) == 9, str(len(m.get("skills", []))))
    t.check("角色 r12", m.get("role") == "r12")
    t.check("输入端口 content_draft/product",
            m.get("inputs") == ["content_draft", "product"])
    t.check("输出端口 growth_plan/channel_assets",
            m.get("outputs") == ["growth_plan", "channel_assets"])

    t.section("S01 增长诊断与基线")
    diag = c.load_json(_ex("diagnose.json"))
    r = s01_diagnose._validate_diagnose(diag)
    t.check("diagnose 干净通过", r["ok"])
    t.check("diagnose funnel_count=5", r["funnel_count"] == 5)
    t.check("diagnose signal_count=4", r["signal_count"] == 4)
    t.check("diagnose 漏斗越界拦截",
            not s01_diagnose._validate_diagnose(
                {"northstar": {"primary": "a", "secondary": "b"},
                 "funnel": ["获客", "随便"], "pmf_signals": ["留存率"]})["ok"])
    t.check("diagnose 北极星缺辅指标拦截",
            not s01_diagnose._validate_diagnose(
                {"northstar": {"primary": "a"},
                 "funnel": ["获客"], "pmf_signals": ["留存率"]})["ok"])
    unit = c.load_json(_ex("unit.json"))
    r = s01_diagnose._validate_unit(unit)
    t.check("unit 干净通过", r["ok"], str(r.get("checks")))
    t.check("unit ltv=1600", abs(r["ltv"] - 1600.0) < 0.01, str(r["ltv"]))
    t.check("unit cac=150", abs(r["cac"] - 150.0) < 0.01, str(r["cac"]))
    t.check("unit ltv_cac=10.67", abs(r["ltv_cac"] - 10.6667) < 0.01, str(r["ltv_cac"]))
    t.check("unit 除零拦截",
            not s01_diagnose._validate_unit(
                {"arpa": 100, "gross_margin": 0.8, "churn_rate": 0.05,
                 "spend": 30000, "new_customers": 0})["ok"])

    t.section("S02 增长循环与自然获客")
    flywheel = c.load_json(_ex("flywheel.json"))
    r = s02_loops._validate_flywheel(flywheel)
    t.check("flywheel 干净通过", r["ok"])
    t.check("flywheel ring_count=5", r["ring_count"] == 5)
    t.check("flywheel 缺环拦截",
            not s02_loops._validate_flywheel(
                {"rings": ["获客", "激活"], "loop": {"trigger": "t"}})["ok"])
    content = c.load_json(_ex("content.json"))
    r = s02_loops._validate_content(content)
    t.check("content 干净通过", r["ok"])
    t.check("content channel_count=5", r["channel_count"] == 5)
    t.check("content 渠道越界拦截",
            not s02_loops._validate_content(
                {"channels": ["贴吧"], "flywheel_link": "x"})["ok"])

    t.section("S03 冷启动与外联")
    coldemail = c.load_json(_ex("coldemail.json"))
    r = s03_outreach._validate_coldemail(coldemail)
    t.check("coldemail 干净通过", r["ok"])
    t.check("coldemail ai_tell_count=0", r["ai_tell_count"] == 0)
    t.check("coldemail AI 腔拦截",
            not s03_outreach._validate_coldemail(
                {"observation": "I hope this email finds you well",
                 "problem": "p", "proof": "pr", "ask": "a",
                 "compliance": {"secondary_domain": "d", "opt_out": "o",
                                "postal_address": "pa"}})["ok"])
    t.check("coldemail 合规三件套缺拦截",
            not s03_outreach._validate_coldemail(
                {"observation": "o", "problem": "p", "proof": "pr", "ask": "a",
                 "compliance": {"secondary_domain": "", "opt_out": "",
                                "postal_address": ""}})["ok"])
    sequence = c.load_json(_ex("sequence.json"))
    r = s03_outreach._validate_sequence(sequence)
    t.check("sequence 干净通过", r["ok"])
    t.check("sequence email_count=3", r["email_count"] == 3)
    t.check("sequence 封数不足拦截",
            not s03_outreach._validate_sequence(
                {"emails": [{"subject": "s", "body": "b"}]})["ok"])

    t.section("S04 红人与合作增长")
    influencer = c.load_json(_ex("influencer.json"))
    r = s04_partner._validate_influencer(influencer)
    t.check("influencer 干净通过", r["ok"])
    t.check("influencer tier=micro", r["tier"] == "micro")
    t.check("influencer tier 越界拦截",
            not s04_partner._validate_influencer(
                {"tier": "mega", "disclosure": "#ad", "fraud_signals": []})["ok"])
    t.check("influencer 披露缺失拦截",
            not s04_partner._validate_influencer(
                {"tier": "micro", "disclosure": "看", "fraud_signals": []})["ok"])
    comarketing = c.load_json(_ex("comarketing.json"))
    r = s04_partner._validate_comarketing(comarketing)
    t.check("comarketing 干净通过", r["ok"])
    t.check("comarketing element_count=5", r["element_count"] == 5)
    t.check("comarketing 缺要素拦截",
            not s04_partner._validate_comarketing(
                {"partner": "p", "audience": "a", "offer": "",
                 "channel": "c", "measure": "m"})["ok"])

    t.section("S05 ASO 与发布")
    aso = c.load_json(_ex("aso.json"))
    r = s05_launch._validate_aso(aso)
    t.check("aso 干净通过", r["ok"])
    t.check("aso store=app_store", r["store"] == "app_store")
    t.check("aso 有 grade", r["grade"] in ("A", "B", "C", "D", "F"), str(r["grade"]))
    t.check("aso store 越界拦截",
            not s05_launch._validate_aso(
                {"store": "steam", "title": "t", "subtitle": "s",
                 "scores": {"title": 9, "description": 8, "visual": 8,
                            "rating": 9, "metadata": 8, "conversion": 9}})["ok"])
    ph = c.load_json(_ex("ph.json"))
    r = s05_launch._validate_ph(ph)
    t.check("ph 干净通过", r["ok"])
    t.check("ph stage_count=3", r["stage_count"] == 3)
    t.check("ph 缺要素拦截",
            not s05_launch._validate_ph(
                {"tagline": "t", "maker_comment": "", "first_comment": "",
                 "links": "", "stages": ["预热", "发布日", "后续跟进"]})["ok"])

    t.section("S06 付费投放与 CRO")
    media = c.load_json(_ex("media.json"))
    r = s06_paid._validate_media(media)
    t.check("media 干净通过", r["ok"])
    t.check("media roi=2.0", abs(r["roi"] - 2.0) < 0.01, str(r["roi"]))
    t.check("media 渠道越界拦截",
            not s06_paid._validate_media(
                {"channel": "电视广告", "audience": "a", "creative": "c",
                 "budget": "b", "return": 15000, "spend": 5000})["ok"])
    t.check("media ROI 负拦截",
            not s06_paid._validate_media(
                {"channel": "搜索广告", "audience": "a", "creative": "c",
                 "budget": "b", "return": 5000, "spend": 15000})["ok"])
    cro = c.load_json(_ex("cro.json"))
    r = s06_paid._validate_cro(cro)
    t.check("cro 干净通过", r["ok"])
    t.check("cro significance 超门槛拦截",
            not s06_paid._validate_cro(
                {"hypothesis": "h", "metric": "m", "significance": 0.5})["ok"])

    t.section("S07 激活留存推荐")
    activation = c.load_json(_ex("activation.json"))
    r = s07_retention._validate_activation(activation)
    t.check("activation 干净通过", r["ok"])
    t.check("activation recall_count=3", r["recall_count"] == 3)
    t.check("activation 预警天数超阈值拦截",
            not s07_retention._validate_activation(
                {"aha_moment": "a", "time_to_value": "t", "funnel": "f",
                 "churn_warning_days": 30, "recall_channels": ["邮件"]})["ok"])
    t.check("activation 召回渠道越界拦截",
            not s07_retention._validate_activation(
                {"aha_moment": "a", "time_to_value": "t", "funnel": "f",
                 "churn_warning_days": 14, "recall_channels": ["私信"]})["ok"])
    referral = c.load_json(_ex("referral.json"))
    r = s07_retention._validate_referral(referral)
    t.check("referral 干净通过", r["ok"])
    t.check("referral kfactor=1.5", abs(r["kfactor"] - 1.5) < 0.01, str(r["kfactor"]))
    t.check("referral kfactor<1 拦截",
            not s07_retention._validate_referral(
                {"invites_per_customer": 2, "conversion_rate": 0.1,
                 "incentive_type": "双边"})["ok"])

    t.section("S08 归因与 RevOps")
    attribution = c.load_json(_ex("attribution.json"))
    r = s08_revops._validate_attribution(attribution)
    t.check("attribution 干净通过", r["ok"])
    t.check("attribution model=last_non_direct", r["model"] == "last_non_direct")
    t.check("attribution field_count=6", r["field_count"] == 6)
    t.check("attribution 模型越界拦截",
            not s08_revops._validate_attribution(
                {"model": "gut_feeling", "dedup_source": "d",
                 "tracking_fields": ["event_name"]})["ok"])
    roi = c.load_json(_ex("roi.json"))
    r = s08_revops._validate_roi(roi)
    t.check("roi 干净通过", r["ok"], str(r.get("checks")))
    t.check("roi ltv_cac=10.67", abs(r["ltv_cac"] - 10.6667) < 0.01, str(r["ltv_cac"]))
    t.check("roi 不健康拦截",
            not s08_revops._validate_roi(
                {"arpa": 100, "gross_margin": 0.8, "churn_rate": 0.5,
                 "spend": 30000, "new_customers": 100})["ok"])

    t.section("S09 自媒体运营")
    daily = c.load_json(_ex("daily.json"))
    r = s09_selfmedia._validate_daily(daily)
    t.check("daily 干净通过", r["ok"])
    t.check("daily platform_count=3", r["platform_count"] == 3)
    t.check("daily 平台越界拦截",
            not s09_selfmedia._validate_daily(
                {"date": "2026-11-05",
                 "platform_summary": [{"platform": "抖音国际版",
                                       "month_net_followers": 1}],
                 "conclusion": "c"})["ok"])
    probe = s09_selfmedia._probe()
    t.check("selfmedia probe 恒 ok=true（如实降级）",
            probe["ok"] and probe["verdict"] == "PASS",
            f"status={probe.get('status')}")
    t.check("selfmedia probe 带 status", "status" in probe)

    t.section("T6 契约")
    names = contracts.skill_names()
    t.check("契约覆盖 9 技能", len(names) == 9, str(len(names)))
    v = contracts.validate_output("diagnose", "diagnose",
                                  s01_diagnose._validate_diagnose(diag))
    t.check("契约校验 diagnose 产出通过", v["ok"], str(v.get("errors")))
    t.check("契约校验非法产出拦截",
            not contracts.validate_output("diagnose", "diagnose", {"ok": True})["ok"])
    t.check("契约校验未知动作拦截",
            not contracts.validate_output("diagnose", "nope", {"ok": True})["ok"])
    t.check("契约校验未知技能拦截",
            not contracts.validate_output("nope", "diagnose", {"ok": True})["ok"])

    t.section("T7 对抗评审")
    good_packet = {"skill": "diagnose", "action": "diagnose",
                   "result": s01_diagnose._validate_diagnose(diag)}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"note": "买粉刷量涨粉最快"}})
    t.check("评审拦截刷量伪造增长", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "fake_growth",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "爬取个人信息做采集"}})
    t.check("评审拦截未授权采集", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "privacy_unauthorized",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "note": "负责 CRM 商机与客户续约"}})
    t.check("评审拦截 CRM 越界", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")
    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "这里内容待定，稍后补充"}})
    t.check("评审拦截无具体产物", rev["verdict"] == "FAIL",
            f"category={rev['failure_category']}")

    t.section("T8 案例库")
    t.check("案例列表 2 个", len(cases.list_cases()) == 2, str(cases.list_cases()))
    t.check("growth-engine 结构通过", cases.validate_case("growth-engine")["ok"])
    t.check("organic-loop 结构通过", cases.validate_case("organic-loop")["ok"])

    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("diagnose funnel_stages 白名单外置", len(th["diagnose"]["funnel_stages"]) == 5)
    t.check("revops attribution_models 外置", len(th["revops"]["attribution_models"]) == 7)
    t.check("launch weights 外置", len(th["launch"]["weights"]) == 6)
    t.check("review 红线词外置", bool(th["review"]["fake_growth_words"])
            and bool(th["review"]["privacy_terms"]) and bool(th["review"]["r13_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    t.section("T6 plan 契约门禁")
    pg = harness.validate_plan(_ex("plan_good.json"))
    t.check("plan 干净通过", pg["ok"] and pg.get("grade") == "PASS", str(pg.get("checks")))
    pb = harness.validate_plan(_ex("plan_bad.json"))
    t.check("plan 缺字段拦截", not pb["ok"] and pb.get("grade") == "FAIL")

    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r12_harness_")
    good_diag_path = os.path.join(tmp, "diagnose.json")
    c.write_json(good_diag_path, diag)
    h = harness.run_validator("diagnose", good_diag_path)
    t.check("harness diagnose 门禁 PASS", h["ok"] and h["grade"] == "PASS")
    bad_path = os.path.join(tmp, "bad.json")
    c.write_json(bad_path, {"northstar": {"primary": "a"}})
    h = harness.run_validator("diagnose", bad_path)
    t.check("harness diagnose 门禁 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_diag_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    pr = harness.probe("selfmedia")
    t.check("harness probe selfmedia 恒 PASS", pr["ok"] and pr["grade"] == "PASS")

    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0 and len(demo.get("demo_artifacts", {})) == 4,
            str(demo.get("demo_artifacts", {}).keys()))

    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(os.path.join(HERE, "examples", "diagnose.json"), "data", note="")
    task = protocol.Task(title="做一次增长诊断", owner="r12",
                         intent="帮我做一次增长诊断，看漏斗和 PMF 信号",
                         inputs=[inp], acceptance=["diagnose 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 1, str(len(done.outputs)))

    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    t.check("闭环 34 行全绿", matrix["ok"], f"passed={matrix['passed']}/{matrix['total']}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R12 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
