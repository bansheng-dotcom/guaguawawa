#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R19 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能 14 动作（含脏数据·越界·主观放行必须 FAIL）/ 契约(T6) /
对抗评审(T7，含三条 R19 红线) / 案例库(T8) / 阈值外置(T9) / harness / demo /
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

from skills import (s01_tracking, s02_registry, s03_evaluation, s04_trace,  # noqa: E402
                    s05_release, s06_monitor, s07_modelcard)
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
    t.check("角色 r19", m.get("role") == "r19", str(m.get("role")))
    t.check("输入端口 dataset/model",
            m.get("inputs") == ["dataset", "model"], str(m.get("inputs")))
    t.check("输出端口 experiment_log/evaluation",
            m.get("outputs") == ["experiment_log", "evaluation"], str(m.get("outputs")))
    t.check("7 个能力域（registry）", len(m.get("capabilities", [])) == 7,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 实验与运行追踪")
    r = s01_tracking._validate_experiment(c.load_json(_ex("tracking_experiment.json")))
    t.check("experiment 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("experiment use_case=genai", r["use_case"] == "genai", str(r["use_case"]))
    r = s01_tracking._validate_experiment(c.load_json(_ex("tracking_experiment_dirty.json")))
    t.check("experiment 脏数据拦截", not r["ok"])
    t.check("experiment 拦截用例越界", any("用例类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_tracking._validate_run(c.load_json(_ex("tracking_run.json")))
    t.check("run 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("run metric_count=3", r["metric_count"] == 3, str(r["metric_count"]))
    r = s01_tracking._validate_run(c.load_json(_ex("tracking_run_dirty.json")))
    t.check("run 脏数据拦截", not r["ok"])
    t.check("run 拦截空指标", any("指标" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("run 拦截空环境", any("环境" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 模型注册与版本")
    r = s02_registry._validate_register(c.load_json(_ex("registry_register.json")))
    t.check("register 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("register stage=staging", r["stage"] == "staging", str(r["stage"]))
    r = s02_registry._validate_register(c.load_json(_ex("registry_register_dirty.json")))
    t.check("register 脏数据拦截", not r["ok"])
    t.check("register 拦截阶段越界", any("阶段" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("register 拦截来源越界", any("来源" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s02_registry._validate_version(c.load_json(_ex("registry_version.json")))
    t.check("version 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("version version_count=3", r["version_count"] == 3, str(r["version_count"]))
    r = s02_registry._validate_version(c.load_json(_ex("registry_version_dirty.json")))
    t.check("version 脏数据拦截", not r["ok"])
    t.check("version 拦截多 production", any("production" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 评估数据与评分器")
    r = s03_evaluation._validate_dataset(c.load_json(_ex("evaluation_dataset.json")))
    t.check("dataset 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("dataset record_count=3", r["record_count"] == 3, str(r["record_count"]))
    r = s03_evaluation._validate_dataset(c.load_json(_ex("evaluation_dataset_dirty.json")))
    t.check("dataset 脏数据拦截", not r["ok"])
    t.check("dataset 拦截缺 ground truth",
            any("expectations" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s03_evaluation._validate_scorer(c.load_json(_ex("evaluation_scorer.json")))
    t.check("scorer 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("scorer scorer_type=llm_judge", r["scorer_type"] == "llm_judge",
            str(r["scorer_type"]))
    r = s03_evaluation._validate_scorer(c.load_json(_ex("evaluation_scorer_dirty.json")))
    t.check("scorer 脏数据拦截", not r["ok"])
    t.check("scorer 拦截类型越界", any("评分器类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("scorer 拦截来源越界", any("反馈来源" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 Agent Trace 与调试")
    r = s04_trace._validate_analyze(c.load_json(_ex("trace_analyze.json")))
    t.check("analyze 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("analyze span_count=3", r["span_count"] == 3, str(r["span_count"]))
    r = s04_trace._validate_analyze(c.load_json(_ex("trace_analyze_dirty.json")))
    t.check("analyze 脏数据拦截", not r["ok"])
    t.check("analyze 拦截 span 类型越界",
            any("span 类型" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("analyze 拦截悬空 parent",
            any("parent" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("analyze 拦截 ERROR 未定位错误 span",
            any("错误 span" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s04_trace._validate_retrieval(c.load_json(_ex("trace_retrieval.json")))
    t.check("retrieval 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s04_trace._validate_retrieval(c.load_json(_ex("trace_retrieval_dirty.json")))
    t.check("retrieval 脏数据拦截", not r["ok"])
    t.check("retrieval 拦截无条件", any("检索条件" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("retrieval 拦截时间窗倒挂", any("顺序" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 回归与发布候选")
    r = s05_release._validate_regression(c.load_json(_ex("release_regression.json")))
    t.check("regression 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("regression diagnosis_layer=instruction",
            r["diagnosis_layer"] == "instruction", str(r["diagnosis_layer"]))
    r = s05_release._validate_regression(c.load_json(_ex("release_regression_dirty.json")))
    t.check("regression 脏数据拦截", not r["ok"])
    t.check("regression 拦截诊断层越界",
            any("诊断层" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("regression 拦截 pass_after=false",
            any("pass_after" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("regression 拦截 existing_green=false",
            any("existing_green" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s05_release._validate_candidate(c.load_json(_ex("release_candidate.json")))
    t.check("candidate 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("candidate verdict=PASS", r["verdict"] == "PASS", str(r["verdict"]))
    r = s05_release._validate_candidate(c.load_json(_ex("release_candidate_dirty.json")))
    t.check("candidate 脏数据拦截", not r["ok"])
    t.check("candidate 拦截裁决越界", any("裁决" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("candidate 拦截空证据", any("证据" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 模型监控接口")
    r = s06_monitor._validate_metrics(c.load_json(_ex("monitor_metrics.json")))
    t.check("metrics 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("metrics metric_name=latency", r["metric_name"] == "latency",
            str(r["metric_name"]))
    r = s06_monitor._validate_metrics(c.load_json(_ex("monitor_metrics_dirty.json")))
    t.check("metrics 脏数据拦截", not r["ok"])
    t.check("metrics 拦截指标名越界", any("指标名" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("metrics 拦截视图越界", any("指标视图" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_monitor._validate_drift(c.load_json(_ex("monitor_drift.json")))
    t.check("drift 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("drift alert_count=1", r["alert_count"] == 1, str(r["alert_count"]))
    r = s06_monitor._validate_drift(c.load_json(_ex("monitor_drift_dirty.json")))
    t.check("drift 脏数据拦截", not r["ok"])
    t.check("drift 拦截阈值不可量化",
            any("阈值可量化" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("drift 拦截缺责任方", any("责任方" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 模型卡与资产证据")
    r = s07_modelcard._validate_card(c.load_json(_ex("modelcard_card.json")))
    t.check("card 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("card risk_tier=medium", r["risk_tier"] == "medium", str(r["risk_tier"]))
    r = s07_modelcard._validate_card(c.load_json(_ex("modelcard_card_dirty.json")))
    t.check("card 脏数据拦截", not r["ok"])
    t.check("card 拦截空限制", any("限制" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("card 拦截风险越界", any("风险分层" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("card 拦截许可越界", any("许可" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s07_modelcard._validate_asset(c.load_json(_ex("modelcard_asset.json")))
    t.check("asset 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("asset asset_count=3", r["asset_count"] == 3, str(r["asset_count"]))
    r = s07_modelcard._validate_asset(c.load_json(_ex("modelcard_asset_dirty.json")))
    t.check("asset 脏数据拦截", not r["ok"])
    t.check("asset 拦截空路径", any("路径" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("asset 拦截缺 run 绑定", any("run_id" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("T6 契约")
    t.check("7 技能登记", len(contracts.skill_names()) == 7,
            str(contracts.skill_names()))
    total_actions = sum(len(contracts.actions(s)) for s in contracts.skill_names())
    t.check("14 动作登记", total_actions == 14, str(total_actions))
    for s in contracts.skill_names():
        for a in contracts.actions(s):
            vi = contracts.validate_input(s, a, {})
            t.check(f"{s}/{a} 输入契约拒绝空对象", not vi["ok"], str(vi["errors"]))
    vo = contracts.validate_output("tracking", "run",
                                   s01_tracking._validate_run(
                                       c.load_json(_ex("tracking_run.json"))))
    t.check("输出契约校验干净产出通过", vo["ok"], str(vo["errors"]))
    vo = contracts.validate_output("tracking", "run", {"ok": True})
    t.check("输出契约拒绝缺 checks", not vo["ok"], str(vo["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审（含三条 R19 红线）")
    good_packet = {"skill": "release", "action": "candidate",
                   "result": s05_release._validate_candidate(
                       c.load_json(_ex("release_candidate.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"model_name": "m1", "checks": [],
                                           "summary": "训练时用了 api_key=sk-xxxx 访问"}})
    t.check("红线1 拦截凭据入工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "credential_gate",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"candidate_id": "c1", "checks": [],
                                           "summary": "新版试了几个问题效果不错，直接上线吧"}})
    t.check("红线2 拦截主观放行", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "fake_pass",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"candidate_id": "c1", "checks": [],
                                           "summary": "给出模型效果与用户增长的业务归因"}})
    t.check("红线3 拦截业务归因越界", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "稍后补充"}})
    t.check("评审拦截无具体工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"candidate_id": "c1", "checks": [],
                                           "summary": "上线须评估证据，我主观感觉不错但已声明 handoff",
                                           "handoff": "证据待补，移交复核"}})
    t.check("已声明 handoff 的主观结论通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"candidate_id": "c1", "checks": [],
                                           "summary": "业务归因需移交 R06",
                                           "handoff": "R06"}})
    t.check("已声明 handoff 的统计越界通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 2 个", len(lst) == 2, str([x["case_id"] for x in lst]))
    for cid in ("regression-gate", "model-release"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("regression-gate")
    t.check("案例阈值可覆盖全局",
            merged["release"].get("require_regression_on_pass") is True,
            str(merged["release"].get("require_regression_on_pass")))
    t.check("案例覆盖不破坏全局键",
            merged["monitor"]["metric_views"] == ["TRACES", "SPANS", "ASSESSMENTS"],
            str(merged["monitor"].get("metric_views")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("tracking 用例白名单外置", len(th["tracking"]["use_cases"]) == 2)
    t.check("tracking 实验类型外置", len(th["tracking"]["experiment_kinds"]) == 2)
    t.check("registry 阶段白名单外置", len(th["registry"]["stages"]) == 4)
    t.check("registry 来源白名单外置", len(th["registry"]["model_sources"]) == 4)
    t.check("evaluation 评分器类型外置", len(th["evaluation"]["scorer_types"]) == 3)
    t.check("evaluation 反馈来源外置", len(th["evaluation"]["feedback_sources"]) == 4)
    t.check("trace 状态白名单外置", len(th["trace"]["trace_states"]) == 4)
    t.check("trace span 类型外置", len(th["trace"]["span_types"]) == 9)
    t.check("release 裁决白名单外置", len(th["release"]["verdicts"]) == 3)
    t.check("release 诊断层外置", len(th["release"]["diagnosis_layers"]) == 6)
    t.check("monitor 指标名外置", len(th["monitor"]["metric_names"]) == 4)
    t.check("modelcard 风险分层外置", len(th["modelcard"]["risk_tiers"]) == 3)
    t.check("review 三条红线词外置",
            bool(th["review"]["credential_words"])
            and bool(th["review"]["fake_pass_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("concrete_keys 不含 ok/checks",
            "ok" not in th["review"]["concrete_keys"]
            and "checks" not in th["review"]["concrete_keys"],
            str(th["review"]["concrete_keys"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r19_harness_")
    good_path = os.path.join(tmp, "tracking_run.json")
    c.write_json(good_path, c.load_json(_ex("tracking_run.json")))
    h = harness.run_validator("tracking_run", good_path)
    t.check("harness tracking_run 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("tracking_run", _ex("tracking_run_dirty.json"))
    t.check("harness tracking_run 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("tracking_run", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    t.check("14 个门禁全部登记", len(harness._VALIDATORS) == 14,
            str(len(harness._VALIDATORS)))
    code, rl = run_agent("harness", "runlog", "--n", "5")
    t.check("harness runlog 可读", code == 0 or "runlog" in rl, str(rl)[:120])

    # ------------------------------------------------------------------ #
    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0
            and len(demo.get("demo_artifacts", {})) == 14,
            str(len(demo.get("demo_artifacts", {}))))
    code, _ = run_agent("case", "get", "--case", "regression-gate")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 7)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("evaluation_scorer.json"), "data", note="")
    task = protocol.Task(title="评估客服助手评分器",
                         owner="r19",
                         intent="帮我看看这个客服助手评分器合不合格，评测口径对不对",
                         inputs=[inp], acceptance=["evaluation 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 evaluation", res.get("skill") == "evaluation",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：发布→release/candidate
    inp2 = protocol.Port(_ex("release_candidate.json"), "data", note="")
    task2 = protocol.Task(title="发布候选裁决", owner="r19",
                          intent="这个新版能不能放行上线，裁决和证据够不够",
                          inputs=[inp2], acceptance=["release 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 发布→release", res2.get("skill") == "release",
            str(res2.get("skill")))

    # 意图路由：模型卡→modelcard/card
    inp3 = protocol.Port(_ex("modelcard_card.json"), "data", note="")
    task3 = protocol.Task(title="登记模型卡", owner="r19",
                          intent="帮我看这份模型卡用途限制风险分层许可全不全",
                          inputs=[inp3], acceptance=["modelcard 门禁通过"])
    ws.create_task(task3)
    code, res3 = run_agent("run", "--task", task3.task_id)
    t.check("意图路由 模型卡→modelcard", res3.get("skill") == "modelcard",
            str(res3.get("skill")))

    # ------------------------------------------------------------------ #
    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    bad_rows = [r["skill"] + ":" + ",".join(r.get("notes", []))
                for r in matrix["matrix"] if not r["ok"]]
    t.check("闭环 28 行全绿", matrix["ok"],
            f"passed={matrix['passed']}/{matrix['total']} bad={bad_rows[:3]}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")
    n_clean = sum(1 for r in matrix["matrix"] if r["expect_ok"])
    n_dirty = sum(1 for r in matrix["matrix"] if not r["expect_ok"])
    t.check("闭环 14 干净 + 14 脏", n_clean == 14 and n_dirty == 14,
            f"clean={n_clean} dirty={n_dirty}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R19 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
