#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R18 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能 14 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7，含三条 R18 红线) / 案例库(T8) / 阈值外置(T9) / harness / demo /
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

from skills import (s01_elt, s02_transform, s03_pipeline, s04_quality,  # noqa: E402
                    s05_incremental, s06_catalog, s07_ops)
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
    t.check("角色 r18", m.get("role") == "r18", str(m.get("role")))
    t.check("输入端口 source/metrics_spec",
            m.get("inputs") == ["source", "metrics_spec"], str(m.get("inputs")))
    t.check("输出端口 dataset/data_catalog",
            m.get("outputs") == ["dataset", "data_catalog"], str(m.get("outputs")))
    t.check("7 个能力域（registry）", len(m.get("capabilities", [])) == 7,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 数据连接与 ELT")
    r = s01_elt._validate_connection(c.load_json(_ex("connection.json")))
    t.check("connection 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("connection source=source-postgres", r["source_connector"] == "source-postgres",
            str(r["source_connector"]))
    r = s01_elt._validate_connection(c.load_json(_ex("connection_dirty.json")))
    t.check("connection 脏数据拦截", not r["ok"])
    t.check("connection 拦截源前缀", any("source-" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("connection 拦截凭据字段", any("凭据" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_elt._validate_sync(c.load_json(_ex("sync.json")))
    t.check("sync 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("sync stream_count=2", r["stream_count"] == 2, str(r["stream_count"]))
    r = s01_elt._validate_sync(c.load_json(_ex("sync_dirty.json")))
    t.check("sync 脏数据拦截", not r["ok"])
    t.check("sync 拦截缺 cursor", any("cursor" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 数仓转换")
    r = s02_transform._validate_model(c.load_json(_ex("model.json")))
    t.check("model 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("model mode=table", r["mode"] == "table", str(r["mode"]))
    r = s02_transform._validate_model(c.load_json(_ex("model_dirty.json")))
    t.check("model 脏数据拦截", not r["ok"])
    t.check("model 拦截物化越界", any("物化" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s02_transform._validate_test(c.load_json(_ex("test.json")))
    t.check("test 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("test test_count=2", r["test_count"] == 2, str(r["test_count"]))
    r = s02_transform._validate_test(c.load_json(_ex("test_dirty.json")))
    t.check("test 脏数据拦截", not r["ok"])
    t.check("test 拦截 accepted_values 缺值",
            any("accepted_values" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 管道调度")
    r = s03_pipeline._validate_dag(c.load_json(_ex("dag.json")))
    t.check("dag 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("dag task_count=3", r["task_count"] == 3, str(r["task_count"]))
    r = s03_pipeline._validate_dag(c.load_json(_ex("dag_dirty.json")))
    t.check("dag 脏数据拦截", not r["ok"])
    t.check("dag 拦截环", any("无环" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s03_pipeline._validate_run(c.load_json(_ex("run.json")))
    t.check("run 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("run failed_count=0", r["failed_count"] == 0, str(r["failed_count"]))
    r = s03_pipeline._validate_run(c.load_json(_ex("run_dirty.json")))
    t.check("run 脏数据拦截", not r["ok"])
    t.check("run 拦截失败任务", any("失败" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 数据质量门禁")
    r = s04_quality._validate_check(c.load_json(_ex("quality_check.json")))
    t.check("quality_check 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("quality_check row_count=1000", r["row_count"] == 1000, str(r["row_count"]))
    r = s04_quality._validate_check(c.load_json(_ex("quality_check_dirty.json")))
    t.check("quality_check 脏数据拦截", not r["ok"])
    t.check("quality_check 拦截空值率", any("空值率" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s04_quality._validate_fresh(c.load_json(_ex("quality_fresh.json")))
    t.check("quality_fresh 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("quality_fresh age_hours=6", r["age_hours"] == 6, str(r["age_hours"]))
    r = s04_quality._validate_fresh(c.load_json(_ex("quality_fresh_dirty.json")))
    t.check("quality_fresh 脏数据拦截", not r["ok"])
    t.check("quality_fresh 拦截过期", any("年龄" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 批流与增量")
    r = s05_incremental._validate_strategy(c.load_json(_ex("incremental_strategy.json")))
    t.check("strategy 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("strategy mode=incremental", r["mode"] == "incremental", str(r["mode"]))
    r = s05_incremental._validate_strategy(c.load_json(_ex("incremental_strategy_dirty.json")))
    t.check("strategy 脏数据拦截", not r["ok"])
    t.check("strategy 拦截缺水位", any("watermark" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s05_incremental._validate_backfill(c.load_json(_ex("backfill.json")))
    t.check("backfill 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("backfill authorized=True", r["authorized"] is True, str(r["authorized"]))
    r = s05_incremental._validate_backfill(c.load_json(_ex("backfill_dirty.json")))
    t.check("backfill 脏数据拦截", not r["ok"])
    t.check("backfill 拦截区间倒挂", any("顺序" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("backfill 拦截未授权", any("授权" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 数据目录")
    r = s06_catalog._validate_entry(c.load_json(_ex("catalog_entry.json")))
    t.check("entry 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("entry field_count=2", r["field_count"] == 2, str(r["field_count"]))
    r = s06_catalog._validate_entry(c.load_json(_ex("catalog_entry_dirty.json")))
    t.check("entry 脏数据拦截", not r["ok"])
    t.check("entry 拦截字段类型越界", any("字段类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_catalog._validate_lineage(c.load_json(_ex("lineage.json")))
    t.check("lineage 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("lineage table_count=3", r["table_count"] == 3, str(r["table_count"]))
    r = s06_catalog._validate_lineage(c.load_json(_ex("lineage_dirty.json")))
    t.check("lineage 脏数据拦截", not r["ok"])
    t.check("lineage 拦截悬空引用", any("引用完整" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 人工审批运维")
    r = s07_ops._validate_request(c.load_json(_ex("ops_request.json")))
    t.check("request 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("request operation=backfill", r["operation"] == "backfill", str(r["operation"]))
    r = s07_ops._validate_request(c.load_json(_ex("ops_request_dirty.json")))
    t.check("request 脏数据拦截", not r["ok"])
    t.check("request 拦截操作越界", any("白名单" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("request 拦截未授权", any("授权" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s07_ops._validate_alert(c.load_json(_ex("alert.json")))
    t.check("alert 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("alert alert_count=1", r["alert_count"] == 1, str(r["alert_count"]))
    r = s07_ops._validate_alert(c.load_json(_ex("alert_dirty.json")))
    t.check("alert 脏数据拦截", not r["ok"])
    t.check("alert 拦截严重度越界", any("严重度" in x for x in _fail_msgs(r)),
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
    vo = contracts.validate_output("elt", "connection",
                                   s01_elt._validate_connection(
                                       c.load_json(_ex("connection.json"))))
    t.check("输出契约校验干净产出通过", vo["ok"], str(vo["errors"]))
    vo = contracts.validate_output("elt", "connection", {"ok": True})
    t.check("输出契约拒绝缺 checks", not vo["ok"], str(vo["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审（含三条 R18 红线）")
    good_packet = {"skill": "elt", "action": "connection",
                   "result": s01_elt._validate_connection(
                       c.load_json(_ex("connection.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"connection_id": "c1", "checks": [],
                                           "summary": "连接串是 jdbc:mysql://..."}})
    t.check("红线1 拦截凭据入工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "credential_gate",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"operation": "backfill", "checks": [],
                                           "summary": "我直接回填了 2026 全年数据"}})
    t.check("红线2 拦截擅自回填", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "execution_gate",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"table": "orders", "checks": [],
                                           "summary": "给出订单量的统计结论与业务归因"}})
    t.check("红线3 拦截统计结论越界", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "稍后补充"}})
    t.check("评审拦截无具体工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"operation": "backfill", "checks": [],
                                           "summary": "回填须人工授权后执行",
                                           "handoff": "R01 审批"}})
    t.check("已声明 handoff 的回填产出通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"table": "orders", "checks": [],
                                           "summary": "业务归因需移交 R06",
                                           "handoff": "R06"}})
    t.check("已声明 handoff 的统计越界通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    # SOP §5.10：案例库支持平滑扩容，契约用严格超集判据（>=2）+ 新案例存在性校验，
    # 禁止再把案例数写死成 ==2（否则新增 metric-reconcile 就挂红）。
    t.check("案例列表 >= 2 个（严格超集）", len(lst) >= 2,
            str([x["case_id"] for x in lst]))
    for cid in ("pipeline-recovery", "quality-gate", "metric-reconcile"):
        t.check(f"案例 {cid} 仍在库（不丢失）",
                cid in {x["case_id"] for x in lst}, str(lst))
    for cid in ("pipeline-recovery", "quality-gate", "metric-reconcile"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("pipeline-recovery")
    t.check("案例阈值可覆盖全局",
            merged["pipeline"].get("blocking_states") == ["failed", "upstream_failed"],
            str(merged["pipeline"].get("blocking_states")))
    t.check("案例覆盖不破坏全局键",
            merged["quality"]["default_max_null_ratio"] == 0.1,
            str(merged["quality"].get("default_max_null_ratio")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("elt 同步模式白名单外置", len(th["elt"]["sync_modes"]) == 3)
    t.check("transform 物化白名单外置", len(th["transform"]["materializations"]) == 4)
    t.check("transform 测试类型白名单外置", len(th["transform"]["test_types"]) == 4)
    t.check("pipeline 任务状态白名单外置", len(th["pipeline"]["task_states"]) == 6)
    t.check("pipeline 重试上限外置", th["pipeline"]["default_max_retries"] == 3)
    t.check("quality 空值率阈值外置", th["quality"]["default_max_null_ratio"] == 0.1)
    t.check("quality 年龄上限外置", th["quality"]["default_max_age_hours"] == 24)
    t.check("incremental 模式白名单外置", len(th["incremental"]["modes"]) == 4)
    t.check("catalog 字段类型白名单外置", len(th["catalog"]["field_types"]) == 7)
    t.check("ops 操作白名单外置", len(th["ops"]["operations"]) == 4)
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
    # SOP §5.7：临时目录显式约束在 workspace/tmp，禁止依赖系统全局 tempfile 死循环陷阱。
    tmp_root = os.path.join(HERE, "workspace", "tmp")
    os.makedirs(tmp_root, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="r18_harness_", dir=tmp_root)
    good_path = os.path.join(tmp, "quality_check.json")
    c.write_json(good_path, c.load_json(_ex("quality_check.json")))
    h = harness.run_validator("quality_check", good_path)
    t.check("harness quality_check 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("quality_check", _ex("quality_check_dirty.json"))
    t.check("harness quality_check 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("quality_check", os.path.join(tmp, "missing.json"))
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
    code, _ = run_agent("case", "get", "--case", "pipeline-recovery")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 7)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("quality_check.json"), "data", note="")
    task = protocol.Task(title="检查订单表质量",
                         owner="r18",
                         intent="帮我看看这批 orders 数据质量达不达标，空值率重复率有没有超",
                         inputs=[inp], acceptance=["quality 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 quality", res.get("skill") == "quality",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：回填→incremental/backfill
    inp2 = protocol.Port(_ex("backfill.json"), "data", note="")
    task2 = protocol.Task(title="回填历史数据", owner="r18",
                          intent="这个回填方案能不能批，区间对不对授权有没有",
                          inputs=[inp2], acceptance=["backfill 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 回填→incremental", res2.get("skill") == "incremental",
            str(res2.get("skill")))

    # 意图路由：血缘→catalog/lineage
    inp3 = protocol.Port(_ex("lineage.json"), "data", note="")
    task3 = protocol.Task(title="登记数据血缘", owner="r18",
                          intent="帮我看这份血缘表引用全不全、有没有断链",
                          inputs=[inp3], acceptance=["lineage 门禁通过"])
    ws.create_task(task3)
    code, res3 = run_agent("run", "--task", task3.task_id)
    t.check("意图路由 血缘→catalog", res3.get("skill") == "catalog",
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

    # ------------------------------------------------------------------ #
    # 第二轨：十维演进集成测试（SOP §六.4 双轨零破坏门禁）
    # ------------------------------------------------------------------ #
    t.section("T16 十维演进集成测试（第二轨）")
    evo_env = dict(os.environ)
    evo_env["PYTHONIOENCODING"] = "utf-8"
    evo = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_evolution_l01_l10"],
        cwd=HERE, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=evo_env)
    evo_tail = ((evo.stdout or "") + (evo.stderr or ""))[-600:]
    t.check("演进集成测试 ALL GREEN", evo.returncode == 0, evo_tail)
    try:
        from engines import available_layers
        layers = available_layers()
    except Exception as exc:  # noqa: BLE001
        layers = []
        t.check("engines 包可导入", False, str(exc))
    t.check("引擎层逐级落地（>=3 且不倒退）", len(layers) >= 3, str(layers))
    t.check("十轮演进执行器存在",
            os.path.exists(os.path.join(HERE, "auto_evolve_runner.py")))

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R18 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
