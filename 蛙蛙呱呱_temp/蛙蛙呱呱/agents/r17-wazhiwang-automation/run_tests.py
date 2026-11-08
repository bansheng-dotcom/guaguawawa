#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R17 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 8 技能 16 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / demo / run_task /
verify_loop 闭环矩阵(T15)。

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

from skills import (s01_integration, s02_webhook, s03_mapping,  # noqa: E402
                    s04_schedule, s05_approval, s06_retry, s07_aiworkflow,
                    s08_audit)
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
    t.check("8 个技能", len(m.get("skills", [])) == 8, str(len(m.get("skills", []))))
    t.check("角色 r17", m.get("role") == "r17", str(m.get("role")))
    t.check("输入端口 rules/fields",
            m.get("inputs") == ["rules", "fields"], str(m.get("inputs")))
    t.check("输出端口 workflow/audit_log",
            m.get("outputs") == ["workflow", "audit_log"], str(m.get("outputs")))
    t.check("8 个能力域", len(m.get("capabilities", [])) == 8,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 SaaS/API 集成")
    r = s01_integration._validate_workflow(c.load_json(_ex("workflow.json")))
    t.check("workflow 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("workflow node_count=3", r["node_count"] == 3, str(r["node_count"]))
    t.check("workflow trigger_count=1", r["trigger_count"] == 1)
    r = s01_integration._validate_workflow(c.load_json(_ex("workflow_dirty.json")))
    t.check("workflow 脏数据拦截", not r["ok"])
    t.check("workflow 拦截悬空边", any("悬空" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s01_integration._validate_credential(c.load_json(_ex("credential.json")))
    t.check("credential 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("credential_count=2", r["credential_count"] == 2)
    r = s01_integration._validate_credential(c.load_json(_ex("credential_dirty.json")))
    t.check("credential 脏数据拦截", not r["ok"])
    t.check("credential 拦截明文密钥", any("明文" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 Webhook 与事件处理")
    r = s02_webhook._validate_webhook(c.load_json(_ex("webhook.json")))
    t.check("webhook 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s02_webhook._validate_webhook(c.load_json(_ex("webhook_dirty.json")))
    t.check("webhook 脏数据拦截", not r["ok"])
    t.check("webhook 拦截 method 越界", any("method" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s02_webhook._validate_event(c.load_json(_ex("event.json")))
    t.check("event 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s02_webhook._validate_event(c.load_json(_ex("event_dirty.json")))
    t.check("event 脏数据拦截", not r["ok"])
    t.check("event 拦截类型越界", any("类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 字段与身份映射")
    r = s03_mapping._validate_mapping(c.load_json(_ex("mapping.json")))
    t.check("mapping 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("mapping_count=2", r["mapping_count"] == 2)
    r = s03_mapping._validate_mapping(c.load_json(_ex("mapping_dirty.json")))
    t.check("mapping 脏数据拦截", not r["ok"])
    t.check("mapping 拦截字段名不合规", any("snake_case" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s03_mapping._validate_table(c.load_json(_ex("table.json")))
    t.check("table 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("table column_count=3", r["column_count"] == 3)
    r = s03_mapping._validate_table(c.load_json(_ex("table_dirty.json")))
    t.check("table 脏数据拦截", not r["ok"])
    t.check("table 拦截保留名列", any("保留名" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 定时与批处理")
    r = s04_schedule._validate_schedule(c.load_json(_ex("schedule.json")))
    t.check("schedule 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s04_schedule._validate_schedule(c.load_json(_ex("schedule_dirty.json")))
    t.check("schedule 脏数据拦截", not r["ok"])
    t.check("schedule 拦截 interval 越界",
            any("interval" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    r = s04_schedule._validate_batch(c.load_json(_ex("batch.json")))
    t.check("batch 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s04_schedule._validate_batch(c.load_json(_ex("batch_dirty.json")))
    t.check("batch 脏数据拦截", not r["ok"])
    t.check("batch 拦截失败无补偿", any("补偿" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 人工审批节点")
    r = s05_approval._validate_approval(c.load_json(_ex("approval.json")))
    t.check("approval 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("approval high_risk_count=1", r["high_risk_count"] == 1)
    r = s05_approval._validate_approval(c.load_json(_ex("approval_dirty.json")))
    t.check("approval 脏数据拦截", not r["ok"])
    t.check("approval 拦截高危无授权", any("授权" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s05_approval._validate_publish(c.load_json(_ex("publish.json")))
    t.check("publish 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s05_approval._validate_publish(c.load_json(_ex("publish_dirty.json")))
    t.check("publish 脏数据拦截", not r["ok"])
    t.check("publish 拦截未验证披露", any("披露" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 失败处理与重试")
    r = s06_retry._validate_retry(c.load_json(_ex("retry.json")))
    t.check("retry 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("retry 幂等已声明", r["idempotency_declared"] is True)
    r = s06_retry._validate_retry(c.load_json(_ex("retry_dirty.json")))
    t.check("retry 脏数据拦截", not r["ok"])
    t.check("retry 拦截写操作无幂等", any("幂等" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s06_retry._validate_errorflow(c.load_json(_ex("errorflow.json")))
    t.check("errorflow 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s06_retry._validate_errorflow(c.load_json(_ex("errorflow_dirty.json")))
    t.check("errorflow 脏数据拦截", not r["ok"])
    t.check("errorflow 拦截未发布", any("发布" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 AI 工作流接入")
    r = s07_aiworkflow._validate_aiagent(c.load_json(_ex("aiagent.json")))
    t.check("aiagent 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s07_aiworkflow._validate_aiagent(c.load_json(_ex("aiagent_dirty.json")))
    t.check("aiagent 脏数据拦截", not r["ok"])
    t.check("aiagent 拦截缺模型", any("model" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s07_aiworkflow._validate_model(c.load_json(_ex("model.json")))
    t.check("model 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s07_aiworkflow._validate_model(c.load_json(_ex("model_dirty.json")))
    t.check("model 脏数据拦截", not r["ok"])
    t.check("model 拦截 agent 无护栏", any("护栏" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S08 自动化审计")
    r = s08_audit._validate_audit(c.load_json(_ex("audit.json")))
    t.check("audit 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s08_audit._validate_audit(c.load_json(_ex("audit_dirty.json")))
    t.check("audit 脏数据拦截", not r["ok"])
    t.check("audit 拦截证据缺字段", any("证据" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s08_audit._validate_runlog(c.load_json(_ex("runlog.json")))
    t.check("runlog 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("runlog success_rate=0.5", r["success_rate"] == 0.5,
            str(r["success_rate"]))
    r = s08_audit._validate_runlog(c.load_json(_ex("runlog_dirty.json")))
    t.check("runlog 脏数据拦截", not r["ok"])
    t.check("runlog 拦截状态越界", any("状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("T6 契约")
    t.check("16 动作契约登记", sum(len(contracts.actions(s))
                                    for s in contracts.skill_names()) == 16,
            str(sum(len(contracts.actions(s)) for s in contracts.skill_names())))
    v = contracts.validate_output(
        "integration", "workflow",
        s01_integration._validate_workflow(c.load_json(_ex("workflow.json"))))
    t.check("工作流产出契约合规", v["ok"], str(v["errors"]))
    v = contracts.validate_input("approval", "publish", {})
    t.check("缺字段输入不合规", not v["ok"], str(v["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审")
    good = s05_approval._validate_publish(c.load_json(_ex("publish.json")))
    rp = review.review_packet({"skill": "approval", "action": "publish",
                               "result": good})
    t.check("干净产出过评审", rp["ok"], str(rp.get("issues")))
    leaky = {"ok": True, "checks": [], "publish_ready": True,
             "narrative": "该工作流已直接发布上线，无需审批"}
    rp2 = review.review_packet({"skill": "approval", "action": "publish",
                                "result": leaky})
    t.check("擅自执行拦截", not rp2["ok"]
            and rp2["failure_category"] == "unauthorized_exec", str(rp2))
    t.check("擅自执行 route=writer", rp2["route"] == "writer", str(rp2["route"]))
    cred_leak = {"ok": True, "checks": [], "credential_count": 1,
                 "narrative": "把 api_key= 写进工作流方便调试"}
    rp3 = review.review_packet({"skill": "integration", "action": "credential",
                                "result": cred_leak})
    t.check("凭据泄露拦截", not rp3["ok"]
            and rp3["failure_category"] == "credential_leak", str(rp3))
    empty = {"ok": True, "checks": [], "next": "一切正常"}
    rp4 = review.review_packet({"skill": "audit", "action": "audit", "result": empty})
    t.check("无工件拦截", not rp4["ok"]
            and rp4["failure_category"] == "artifact_not_concrete", str(rp4))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 2 个", len(lst) == 2, str([x["case_id"] for x in lst]))
    for cid in ("unapproved-publish", "credential-leak"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("unapproved-publish")
    t.check("案例阈值可覆盖全局",
            merged["approval"].get("approval_required_levels") == ["critical"],
            str(merged["approval"].get("approval_required_levels")))
    t.check("案例覆盖不破坏全局键",
            merged["retry"]["max_retries_cap"] == 10,
            str(merged["retry"].get("max_retries_cap")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("触发器类型白名单外置", len(th["integration"]["trigger_types"]) == 9)
    t.check("凭据密钥禁词外置", len(th["integration"]["credential_secret_keys"]) >= 13)
    t.check("webhook method 外置", len(th["webhook"]["methods"]) == 5)
    t.check("事件类型白名单外置", len(th["webhook"]["event_types"]) >= 12)
    t.check("列类型白名单外置", len(th["mapping"]["column_types"]) == 4)
    t.check("保留列外置", len(th["mapping"]["reserved_columns"]) >= 6)
    t.check("调度类型外置", len(th["schedule"]["schedule_types"]) == 3)
    t.check("高危动作外置", len(th["approval"]["high_risk_actions"]) >= 10)
    t.check("重试状态外置", len(th["retry"]["statuses"]) == 7)
    t.check("AI 节点类型外置", len(th["aiworkflow"]["node_types"]) >= 6)
    t.check("审计证据字段外置", len(th["audit"]["required"]) == 5)
    t.check("review 红线词外置", bool(th["review"]["credential_words"])
            and bool(th["review"]["execution_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r17_harness_")
    good_path = os.path.join(tmp, "workflow.json")
    c.write_json(good_path, c.load_json(_ex("workflow.json")))
    h = harness.run_validator("workflow", good_path)
    t.check("harness workflow 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("workflow", _ex("workflow_dirty.json"))
    t.check("harness 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("workflow", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    t.check("16 个门禁全部登记", len(harness._VALIDATORS) == 16,
            str(len(harness._VALIDATORS)))
    code, rl = run_agent("harness", "runlog", "--n", "5")
    t.check("harness runlog 可读", code == 0 or "runlog" in rl, str(rl)[:120])

    # ------------------------------------------------------------------ #
    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0
            and len(demo.get("demo_artifacts", {})) == 16,
            str(demo.get("demo_artifacts", {}).keys()))
    code, _ = run_agent("case", "get", "--case", "unapproved-publish")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 8)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("workflow.json"), "data", note="")
    task = protocol.Task(title="核查工作流结构",
                         owner="r17",
                         intent="帮我核查这个自动化工作流的结构是否合规、能不能集成",
                         inputs=[inp], acceptance=["workflow 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 integration", res.get("skill") == "integration",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：发布→approval/publish
    inp2 = protocol.Port(_ex("publish.json"), "data", note="")
    task2 = protocol.Task(title="发布前门禁核查", owner="r17",
                          intent="这个工作流要发布上线，帮我查下发布前门禁是否通过",
                          inputs=[inp2], acceptance=["publish 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 发布→approval", res2.get("skill") == "approval",
            str(res2.get("skill")))

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
    print("全绿 · R17 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
