#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R20 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能 14 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7，含三条 R20 红线) / 案例库(T8) / 阈值外置(T9) / harness / demo /
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

from skills import (s01_monitor, s02_alert, s03_statuspage, s04_backup,  # noqa: E402
                    s05_restore, s06_dr, s07_postmortem)
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
    t.check("角色 r20", m.get("role") == "r20", str(m.get("role")))
    t.check("输入端口 topology/asset_list",
            m.get("inputs") == ["topology", "asset_list"], str(m.get("inputs")))
    t.check("输出端口 monitor_config/backup_repo",
            m.get("outputs") == ["monitor_config", "backup_repo"], str(m.get("outputs")))
    t.check("7 个能力域（registry）", len(m.get("capabilities", [])) == 7,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 可用性监控")
    r = s01_monitor._validate_monitor(c.load_json(_ex("monitor.json")))
    t.check("monitor 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("monitor type=http", r["monitor_type"] == "http", str(r["monitor_type"]))
    r = s01_monitor._validate_monitor(c.load_json(_ex("monitor_dirty.json")))
    t.check("monitor 脏数据拦截", not r["ok"])
    t.check("monitor 拦截空 ID", any("ID 非空" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_monitor._validate_uptime(c.load_json(_ex("uptime.json")))
    t.check("uptime 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("uptime ratio=0.999", abs(r["uptime_ratio"] - 0.999) < 1e-6,
            str(r["uptime_ratio"]))
    r = s01_monitor._validate_uptime(c.load_json(_ex("uptime_dirty.json")))
    t.check("uptime 脏数据拦截", not r["ok"])
    t.check("uptime 拦截 up>total", any("∈" in x or "成功次数" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 告警与升级")
    r = s02_alert._validate_alert(c.load_json(_ex("alert.json")))
    t.check("alert 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("alert count=1", r["alert_count"] == 1, str(r["alert_count"]))
    r = s02_alert._validate_alert(c.load_json(_ex("alert_dirty.json")))
    t.check("alert 脏数据拦截", not r["ok"])
    t.check("alert 拦截严重度越界", any("严重度" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s02_alert._validate_escalation(c.load_json(_ex("escalation.json")))
    t.check("escalation 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("escalation count=2", r["escalation_count"] == 2, str(r["escalation_count"]))
    r = s02_alert._validate_escalation(c.load_json(_ex("escalation_dirty.json")))
    t.check("escalation 脏数据拦截", not r["ok"])
    t.check("escalation 拦截 level 非单调", any("单调" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 状态页与事件沟通")
    r = s03_statuspage._validate_statuspage(c.load_json(_ex("statuspage.json")))
    t.check("statuspage 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("statuspage component_count=2", r["component_count"] == 2,
            str(r["component_count"]))
    r = s03_statuspage._validate_statuspage(c.load_json(_ex("statuspage_dirty.json")))
    t.check("statuspage 脏数据拦截", not r["ok"])
    t.check("statuspage 拦截状态越界", any("白名单" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s03_statuspage._validate_incident(c.load_json(_ex("incident.json")))
    t.check("incident 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("incident timeline_count=3", r["timeline_count"] == 3,
            str(r["timeline_count"]))
    r = s03_statuspage._validate_incident(c.load_json(_ex("incident_dirty.json")))
    t.check("incident 脏数据拦截", not r["ok"])
    t.check("incident 拦截时序倒挂", any("单调" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 加密增量备份")
    r = s04_backup._validate_backup(c.load_json(_ex("backup.json")))
    t.check("backup 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("backup encrypted=True", r["encrypted"] is True, str(r["encrypted"]))
    r = s04_backup._validate_backup(c.load_json(_ex("backup_dirty.json")))
    t.check("backup 脏数据拦截", not r["ok"])
    t.check("backup 拦截未加密", any("加密" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s04_backup._validate_snapshot(c.load_json(_ex("snapshot.json")))
    t.check("snapshot 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("snapshot count=2", r["snapshot_count"] == 2, str(r["snapshot_count"]))
    r = s04_backup._validate_snapshot(c.load_json(_ex("snapshot_dirty.json")))
    t.check("snapshot 脏数据拦截", not r["ok"])
    t.check("snapshot 拦截重复 ID", any("唯一" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 恢复演练")
    r = s05_restore._validate_restore(c.load_json(_ex("restore.json")))
    t.check("restore 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("restore target=snapshot", r["target"] == "snapshot", str(r["target"]))
    r = s05_restore._validate_restore(c.load_json(_ex("restore_dirty.json")))
    t.check("restore 脏数据拦截", not r["ok"])
    t.check("restore 拦截空快照", any("快照" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s05_restore._validate_drill(c.load_json(_ex("drill.json")))
    t.check("drill 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("drill restored_count=150", r["restored_count"] == 150,
            str(r["restored_count"]))
    r = s05_restore._validate_drill(c.load_json(_ex("drill_dirty.json")))
    t.check("drill 脏数据拦截", not r["ok"])
    t.check("drill 拦截 0 文件", any("> 0" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 灾难恢复与回滚")
    r = s06_dr._validate_rpo_rto(c.load_json(_ex("rpo_rto.json")))
    t.check("rpo_rto 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("rpo_rto rpo=1", r["rpo_hours"] == 1, str(r["rpo_hours"]))
    r = s06_dr._validate_rpo_rto(c.load_json(_ex("rpo_rto_dirty.json")))
    t.check("rpo_rto 脏数据拦截", not r["ok"])
    t.check("rpo_rto 拦截 RPO 超限", any("RPO" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_dr._validate_rollback(c.load_json(_ex("rollback.json")))
    t.check("rollback 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("rollback step_count=2", r["step_count"] == 2, str(r["step_count"]))
    r = s06_dr._validate_rollback(c.load_json(_ex("rollback_dirty.json")))
    t.check("rollback 脏数据拦截", not r["ok"])
    t.check("rollback 拦截空计划", any("非空" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 运行复盘")
    r = s07_postmortem._validate_postmortem(c.load_json(_ex("postmortem.json")))
    t.check("postmortem 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("postmortem severity=sev2", r["severity"] == "sev2", str(r["severity"]))
    r = s07_postmortem._validate_postmortem(c.load_json(_ex("postmortem_dirty.json")))
    t.check("postmortem 脏数据拦截", not r["ok"])
    t.check("postmortem 拦截严重度越界", any("严重度" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s07_postmortem._validate_improvement(c.load_json(_ex("improvement.json")))
    t.check("improvement 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("improvement action_count=2", r["action_count"] == 2,
            str(r["action_count"]))
    r = s07_postmortem._validate_improvement(c.load_json(_ex("improvement_dirty.json")))
    t.check("improvement 脏数据拦截", not r["ok"])
    t.check("improvement 拦截未闭环", any("闭环" in x for x in _fail_msgs(r)),
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
    vo = contracts.validate_output("backup", "backup",
                                   s04_backup._validate_backup(
                                       c.load_json(_ex("backup.json"))))
    t.check("输出契约校验干净产出通过", vo["ok"], str(vo["errors"]))
    vo = contracts.validate_output("backup", "backup", {"ok": True})
    t.check("输出契约拒绝缺 checks", not vo["ok"], str(vo["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审（含三条 R20 红线）")
    good_packet = {"skill": "backup", "action": "backup",
                   "result": s04_backup._validate_backup(
                       c.load_json(_ex("backup.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"repo": "/backups/repo", "checks": [],
                                           "summary": "仓库密码是 123456"}})
    t.check("红线1 拦截凭据入工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "credential_gate",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"repo": "/backups/repo", "checks": [],
                                           "summary": "我直接删除快照释放空间了"}})
    t.check("红线2 拦截擅自删除快照", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "execution_gate",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"monitor_id": "m1", "checks": [],
                                           "summary": "给出可用率的统计结论与业务归因"}})
    t.check("红线3 拦截统计结论越界", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "稍后补充"}})
    t.check("评审拦截无具体工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"repo": "/backups/repo", "checks": [],
                                           "summary": "删除快照须人工授权后执行",
                                           "handoff": "R01 审批"}})
    t.check("已声明 handoff 的删除快照产出通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    # SOP §5.10：案例库允许平滑扩容，历史契约用严格超集判据，禁止写死 == 2。
    ids = [x["case_id"] for x in lst]
    t.check("案例列表 >= 2 个（超集判据）", len(lst) >= 2, str(ids))
    for cid in ("backup-no-restore", "incident-escalation", "sla-incident"):
        t.check(f"案例存在 {cid}", cid in ids, str(ids))
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("monitor 监控类型白名单外置", len(th["monitor"]["monitor_types"]) == 5)
    t.check("alert 严重度白名单外置", len(th["alert"]["severities"]) == 3)
    t.check("alert 渠道白名单外置", len(th["alert"]["channels"]) == 5)
    t.check("statuspage 组件状态白名单外置", len(th["statuspage"]["component_statuses"]) == 4)
    t.check("backup 保留策略白名单外置", len(th["backup"]["retention_policies"]) == 6)
    t.check("restore 恢复目标白名单外置", len(th["restore"]["restore_targets"]) == 4)
    t.check("dr 恢复类型白名单外置", len(th["dr"]["recovery_types"]) == 3)
    t.check("dr RTO 上限外置", th["dr"]["rto_max_hours"] == 24)
    t.check("postmortem 严重度白名单外置", len(th["postmortem"]["severities"]) == 3)
    t.check("review 三条红线词外置",
            bool(th["review"]["credential_words"])
            and bool(th["review"]["execution_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("concrete_keys 不含 ok/checks",
            "ok" not in th["review"]["concrete_keys"]
            and "checks" not in th["review"]["concrete_keys"],
            str(th["review"]["concrete_keys"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r20_harness_")
    good_path = os.path.join(tmp, "backup.json")
    c.write_json(good_path, c.load_json(_ex("backup.json")))
    h = harness.run_validator("backup", good_path)
    t.check("harness backup 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("backup", _ex("backup_dirty.json"))
    t.check("harness backup 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("backup", os.path.join(tmp, "missing.json"))
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
    code, _ = run_agent("case", "get", "--case", "backup-no-restore")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 7)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("backup.json"), "data", note="")
    task = protocol.Task(title="检查备份仓是否加密",
                         owner="r20",
                         intent="帮我看这个备份仓加密了没、排除规则对不对",
                         inputs=[inp], acceptance=["backup 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 backup", res.get("skill") == "backup",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：恢复演练→restore/drill
    inp2 = protocol.Port(_ex("drill.json"), "data", note="")
    task2 = protocol.Task(title="验证能否恢复", owner="r20",
                          intent="帮我做一次恢复演练，看看能不能真恢复出来",
                          inputs=[inp2], acceptance=["drill 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 恢复演练→restore", res2.get("skill") == "restore",
            str(res2.get("skill")))

    # 意图路由：删除快照→dr/rollback（不可逆词优先级）
    inp3 = protocol.Port(_ex("rollback.json"), "data", note="")
    task3 = protocol.Task(title="删快照前确认回滚", owner="r20",
                          intent="我想删除快照释放空间，回滚计划有没有",
                          inputs=[inp3], acceptance=["rollback 门禁通过"])
    ws.create_task(task3)
    code, res3 = run_agent("run", "--task", task3.task_id)
    t.check("意图路由 删除快照→dr/rollback", res3.get("skill") == "dr",
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
    print("全绿 · R20 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
