# -*- coding: utf-8 -*-
"""R04 蛙挑刺（独立评审官）验收测试。

跑法：
    python run_tests.py [--kwd 过滤词]
输出：逐项 PASS/FAIL，最后汇总「全部通过: N assertions」。

覆盖（T1-T14 样板）：
    T01 注册/manifest/意图路由/交付物厚度/阈值外置
    T02 全部 15 动作 CLI 冒烟（运行/结果结构/退出码）
    T03-T09 七技能逐动作：模块级语义断言 + 脏数据负例
    T10 对抗评审五检查（身份红线/修复红线/证据链/降级/禁词）
    T11 契约登记表：输入/输出 schema 双向校验
    T12 确定性验证器：materials/verdict/plan/runlog
    T13 案例库：结构门禁 + 两案例全部步骤 expect 数字对拍
    T14 CLI 协议：脏夹具退出码/manifest/demo/contract/review/case/harness
    T15 verify_loop 闭环矩阵（契约×执行×结构×评审门）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from skills import SKILLS                                      # noqa: E402
from skills import _common as c                                 # noqa: E402
from skills import s01_artifact, s02_gate, s03_criteria         # noqa: E402
from skills import s04_quality, s05_facts, s06_strengths        # noqa: E402
from skills import s07_human                                    # noqa: E402
import agent                                                    # noqa: E402
import contracts                                               # noqa: E402
import review as review_lib                                     # noqa: E402
import cases as cases_lib                                       # noqa: E402
import harness as harness_lib                                   # noqa: E402
import verify_loop                                              # noqa: E402

TOOL = os.path.join(HERE, "agent.py")
EX = os.path.join(HERE, "examples")
CASES = os.path.join(HERE, "cases")
RESULT_MARK = "__AGENT_RESULT__ "

# 15 动作 ×（技能, 动作, 附加 CLI 参数）
ACTIONS = [
    ("artifact", "inventory", []),
    ("artifact", "verify", []),
    ("gate", "run", []),
    ("gate", "audit", []),
    ("criteria", "review", []),
    ("criteria", "delta", ["--state", os.path.join(EX, "criteria_delta_state.json")]),
    ("quality", "critique", []),
    ("quality", "converge", ["--compare", os.path.join(EX, "quality_converge_v2.json")]),
    ("facts", "check", []),
    ("facts", "trace", ["--text", os.path.join(EX, "facts_trace_source.txt")]),
    ("strengths", "mark", []),
    ("strengths", "recheck", ["--new", os.path.join(EX, "strengths_recheck_new.json")]),
    ("human", "package", []),
    ("human", "ingest", []),
    ("human", "ack", []),
]

# 12 个脏数据负例（全部必须以退出码 1 + ok:false 收场）
DIRTY = [
    ("artifact", "inventory", "artifact_inventory_dirty.json", []),
    ("artifact", "verify", "artifact_verify_dirty.json", []),
    ("gate", "run", "gate_run_dirty.json", []),
    ("gate", "audit", "gate_audit_dirty.json", []),
    ("criteria", "review", "criteria_review_dirty.json", []),
    ("quality", "critique", "quality_critique_dirty.json", []),
    ("facts", "check", "facts_check_dirty.json", []),
    ("strengths", "mark", "strengths_mark_dirty.json", []),
    ("strengths", "recheck", "strengths_recheck_dirty.json",
     ["--new", os.path.join(EX, "strengths_recheck_new_dirty.json")]),
    ("human", "package", "human_package_dirty.json", []),
    ("human", "ingest", "human_ingest_dirty.json", []),
    ("human", "ack", "human_ack_dirty.json", []),
]


def load(path):
    return c.load_json(path)


def fx(name):
    return os.path.join(EX, name)


def run_cli(skill, action, input_path, extra=None):
    """跑技能子命令，解析 __AGENT_RESULT__ 行。"""
    args = ([sys.executable, TOOL, skill, action, "--input", input_path]
            + list(extra or []))
    cp = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", cwd=HERE, timeout=120)
    result = None
    for line in (cp.stdout or "").splitlines():
        if line.startswith(RESULT_MARK):
            result = json.loads(line[len(RESULT_MARK):])
            break
    return result, cp.returncode


def run_cli_json(args_list):
    """跑 meta 子命令（manifest/contract/review/case/harness），整体 stdout 是 JSON。"""
    cp = subprocess.run([sys.executable, TOOL] + args_list, capture_output=True,
                        text=True, encoding="utf-8", errors="replace", cwd=HERE,
                        timeout=120)
    try:
        return json.loads(cp.stdout or ""), cp.returncode
    except ValueError:
        return None, cp.returncode


def result_of(skill, action):
    """模块直调：拿某动作对干净夹具的产出（供契约/评审复用）。"""
    if (skill, action) == ("artifact", "inventory"):
        return s01_artifact.inventory(load(fx("artifact_inventory.json")), EX)
    if (skill, action) == ("artifact", "verify"):
        return s01_artifact.verify(load(fx("artifact_verify.json")), EX)
    if (skill, action) == ("gate", "run"):
        return s02_gate.run_gates(load(fx("gate_run.json")))
    if (skill, action) == ("gate", "audit"):
        return s02_gate.audit(load(fx("gate_audit.json")))
    if (skill, action) == ("criteria", "review"):
        return s03_criteria.review(load(fx("criteria_review.json")))
    if (skill, action) == ("criteria", "delta"):
        return s03_criteria.delta(load(fx("criteria_delta.json")),
                                  load(fx("criteria_delta_state.json")))
    if (skill, action) == ("quality", "critique"):
        return s04_quality.critique(load(fx("quality_critique.json")))
    if (skill, action) == ("quality", "converge"):
        return s04_quality.converge(load(fx("quality_converge.json")),
                                    load(fx("quality_converge_v2.json")))
    if (skill, action) == ("facts", "check"):
        return s05_facts.check(load(fx("facts_check.json")))
    if (skill, action) == ("facts", "trace"):
        return s05_facts.trace(load(fx("facts_trace.json")),
                               c.load_text(fx("facts_trace_source.txt")))
    if (skill, action) == ("strengths", "mark"):
        return s06_strengths.mark(load(fx("strengths_mark.json")))
    if (skill, action) == ("strengths", "recheck"):
        return s06_strengths.recheck(load(fx("strengths_recheck.json")),
                                     load(fx("strengths_recheck_new.json")))
    if (skill, action) == ("human", "package"):
        return s07_human.package(load(fx("human_package.json")))
    if (skill, action) == ("human", "ingest"):
        return s07_human.ingest(load(fx("human_ingest.json")))
    if (skill, action) == ("human", "ack"):
        return s07_human.ack(load(fx("human_ack.json")))
    raise KeyError(f"{skill}.{action}")


# --------------------------------------------------------------------------- #
# T01 注册 / manifest / 意图路由 / 交付物厚度 / 阈值外置
# --------------------------------------------------------------------------- #
class T01(unittest.TestCase):

    def test_skills_registered(self):
        self.assertEqual(len(SKILLS), 7)
        self.assertEqual([m.NAME for m in SKILLS],
                         ["artifact", "gate", "criteria", "quality",
                          "facts", "strengths", "human"])

    def test_every_skill_exposes_api(self):
        for m in SKILLS:
            with self.subTest(m.NAME):
                self.assertTrue(m.NAME and m.DESC)
                self.assertGreaterEqual(len(m.ACTIONS), 2)
                self.assertTrue(callable(m.add_parser))
                self.assertTrue(callable(m.run))

    def test_action_count(self):
        self.assertEqual(sum(len(m.ACTIONS) for m in SKILLS), 15)

    def test_manifest(self):
        d = agent.make_manifest()
        self.assertEqual(d["role"], "r04")
        self.assertEqual(d["skill_count"], 7)
        self.assertEqual(d["action_count"], 15)
        self.assertEqual(len(d["contracts"]), 15)
        self.assertEqual(len(d["intent_routes"]), 15)
        self.assertIn("评审者==生产者（身份红线）", d["boundary"]["never"])
        self.assertEqual(sorted(d["cases"]),
                         ["harness-audit", "landing-acceptance"])
        for s in d["skills"]:
            self.assertTrue(s["actions"])

    def test_route_intent(self):
        routes = [
            ("三级证据链核验一下", "artifact", "verify"),
            ("物料核验", "artifact", "inventory"),
            ("门禁强度审计", "gate", "audit"),
            ("跑门禁", "gate", "run"),
            ("判据对照", "criteria", "delta"),
            ("外置判据审查", "criteria", "review"),
            ("收敛了吗", "quality", "converge"),
            ("禁词扫描", "quality", "critique"),
            ("单数字回溯", "facts", "trace"),
            ("事实核查", "facts", "check"),
            ("保留优点", "strengths", "mark"),
            ("复评修改", "strengths", "recheck"),
            ("staged 资产确认", "human", "ack"),
            ("批次校验", "human", "ingest"),
            ("发起人工评审", "human", "package"),
            # P2.1：关键词全未命中不再静默落到 criteria/review，交 L02 内核澄清
            ("完全无关的意图", "__clarify__", "clarify"),
        ]
        for text, skill, action in routes:
            with self.subTest(text):
                s, a, _ = agent.route_intent(text)
                self.assertEqual((s, a), (skill, action))

    def test_route_extra_args(self):
        _, _, extra = agent.route_intent("判据对照")
        self.assertIn("state", extra)
        _, _, extra = agent.route_intent("收敛了吗")
        self.assertIn("compare", extra)
        _, _, extra = agent.route_intent("单数字回溯")
        self.assertIn("text", extra)
        _, _, extra = agent.route_intent("复评修改")
        self.assertIn("new", extra)
        _, _, extra = agent.route_intent("物料核验")
        self.assertEqual(extra, {})

    def test_deliverables_exist(self):
        # T14 交付物厚度：SKILL.md / 7 references / 阈值外置 / 案例经验包
        self.assertGreater(os.path.getsize(os.path.join(HERE, "SKILL.md")), 1000)
        names = ["artifact", "gate", "criteria", "quality", "facts",
                 "strengths", "human"]
        for i, n in enumerate(names, start=1):
            p = os.path.join(HERE, "references", f"s0{i}-{n}.md")
            self.assertTrue(os.path.isfile(p), p)
            self.assertGreater(os.path.getsize(p), 500, p)
        for p in ("experience/thresholds.json", "experience/plan_schema.json"):
            self.assertTrue(os.path.isfile(os.path.join(HERE, p)), p)
        for case in ("landing-acceptance", "harness-audit"):
            for f in ("case.json", "semantic_layer.json",
                      "experience/good_summaries.md",
                      "experience/priority_rules.md",
                      "experience/thresholds.json"):
                self.assertTrue(os.path.isfile(os.path.join(CASES, case, f)),
                                os.path.join(case, f))

    def test_thresholds_externalized(self):
        th = c.load_thresholds()
        self.assertEqual(th["artifact"]["levels"],
                         ["L1_EXISTS", "L2_SUBSTANTIVE", "L3_WIRED"])
        self.assertEqual(len(th["strength"]["patterns"]), 7)
        self.assertEqual(sorted(th["strength"]["patterns"]),
                         [f"STRENGTH-00{i}" for i in range(1, 8)])
        self.assertGreaterEqual(th["gate"]["timeout_s"], 1)
        self.assertEqual(th["criteria"]["statuses"], ["pass", "warn", "fail"])
        self.assertIn("should", th["quality"]["hedge_words"])
        self.assertIn("完美", th["quality"]["absolutist_words"])
        self.assertEqual(th["facts"]["source_type_whitelist"],
                         ["primary", "secondary", "unsourced"])
        self.assertEqual(th["strengths"]["keep_required_fields"],
                         ["id", "what", "why_keep", "evidence"])
        self.assertEqual(th["human"]["comment_kinds"], ["selection", "element"])
        self.assertEqual(th["human"]["edit_kinds"], ["edited", "deleted", "moved"])
        self.assertEqual(th["review"]["verdict_enum"], ["PASS", "FAIL", "BLOCKED"])
        self.assertTrue(th["review"]["evidence_keys"])
        self.assertTrue(th["review"]["conclusion_keys"])
        # gate/audit 的证据键必须登记（PASS 须证据链）
        self.assertIn("evaluated_patterns", th["review"]["evidence_keys"])


# --------------------------------------------------------------------------- #
# T02 全动作 CLI 冒烟
# --------------------------------------------------------------------------- #
class T02(unittest.TestCase):

    def test_all_actions_run(self):
        for skill, action, extra in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                result, rc = run_cli(skill, action, fx(f"{skill}_{action}.json"),
                                     extra)
                self.assertIsNotNone(result, f"{skill}.{action} 崩溃")
                self.assertTrue(result["ok"], f"{skill}.{action} 未通过")
                self.assertIn("checks", result)
                self.assertEqual(rc, 0)

    def test_missing_input_handled(self):
        result, rc = run_cli("artifact", "inventory", fx("not_exist.json"))
        self.assertIsNotNone(result)
        self.assertFalse(result["ok"])
        self.assertIn("not found", result["error"])
        self.assertEqual(rc, 1)

    def test_missing_state_file_handled(self):
        result, rc = run_cli("criteria", "delta", fx("criteria_delta.json"),
                             ["--state", fx("not_exist.json")])
        self.assertIsNotNone(result)
        self.assertFalse(result["ok"])
        self.assertIn("not found", result["error"])
        self.assertEqual(rc, 1)


# --------------------------------------------------------------------------- #
# T03 artifact：inventory / verify 三级证据链
# --------------------------------------------------------------------------- #
class T03(unittest.TestCase):

    def test_inventory_clean(self):
        out = s01_artifact.inventory(load(fx("artifact_inventory.json")), EX)
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "COMPLETE")
        self.assertEqual(out["item_count"], 3)
        self.assertEqual(out["missing_required_count"], 0)
        # 可选缺失不拉红：没有任何失败检查
        self.assertFalse([ch for ch in out["checks"] if not ch["ok"]])

    def test_inventory_optional_missing_is_info(self):
        out = s01_artifact.inventory(load(fx("artifact_inventory.json")), EX)
        infos = [ch for ch in out["checks"]
                 if ch["sev"] == "INFO"
                 and ch.get("path") == "references/optional-notes.md"]
        self.assertEqual(len(infos), 1)
        self.assertTrue(infos[0]["ok"])

    def test_inventory_dirty_blocked(self):
        out = s01_artifact.inventory(load(fx("artifact_inventory_dirty.json")), EX)
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "BLOCKED")
        self.assertEqual(out["missing_required_count"], 1)
        self.assertEqual(out["missing_required"][0]["path"],
                         "experience/__missing_required__.json")

    def test_inventory_empty_items(self):
        out = s01_artifact.inventory({"items": []}, EX)
        self.assertFalse(out["ok"])
        self.assertEqual(out["checks"][0]["sev"], "CRITICAL")

    def test_verify_clean(self):
        out = s01_artifact.verify(load(fx("artifact_verify.json")), EX)
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "COMPLETE")
        self.assertEqual(out["passed_count"], out["artifact_count"])
        self.assertEqual(out["stub_hit_count"], 0)

    def test_verify_dirty_incomplete(self):
        out = s01_artifact.verify(load(fx("artifact_verify_dirty.json")), EX)
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "INCOMPLETE")
        self.assertEqual(out["stub_hit_count"], 1)
        levels = [g["level"] for g in out["gaps"]]
        for lv in ("L1_EXISTS", "L2_SUBSTANTIVE", "L3_WIRED"):
            self.assertIn(lv, levels)

    def test_scan_stub_marker(self):
        th = c.load_thresholds()["artifact"]
        hits = s01_artifact._scan_stub("x = 1  # TODO: fix later", "code", th)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["rule"], "stub_marker")
        self.assertEqual(hits[0]["marker"], "TODO")

    def test_scan_stub_empty_function(self):
        th = c.load_thresholds()["artifact"]
        hits = s01_artifact._scan_stub("def f():\n    pass\n", "code", th)
        self.assertEqual(hits[0]["rule"], "empty_function_body")

    def test_scan_stub_raise_not_implemented(self):
        th = c.load_thresholds()["artifact"]
        hits = s01_artifact._scan_stub("def f():\n    raise NotImplementedError\n",
                                       "code", th)
        self.assertEqual(hits[0]["rule"], "raise_not_implemented")

    def test_scan_stub_test_skip(self):
        th = c.load_thresholds()["artifact"]
        hits = s01_artifact._scan_stub("xit('broken thing')", "test", th)
        self.assertEqual(hits[0]["rule"], "test_skip_marker")

    def test_scan_stub_sole_statement(self):
        th = c.load_thresholds()["artifact"]
        hits = s01_artifact._scan_stub("pass", "code", th)
        self.assertEqual(hits[0]["rule"], "sole_stub_statement")

    def test_scan_stub_clean(self):
        th = c.load_thresholds()["artifact"]
        self.assertEqual(s01_artifact._scan_stub("print('hello world')\n",
                                                 "code", th), [])

    def test_effective_content_priority(self):
        # content 声明 > 磁盘读取 > exists 声明
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.txt")
            c.write_text(p, "FILE_CONTENT")
            eff = s01_artifact._effective_content(
                {"path": p, "content": "DECLARED"}, None)
            self.assertEqual(eff["content"], "DECLARED")
            self.assertEqual(eff["size_bytes"], len("DECLARED"))
            eff2 = s01_artifact._effective_content({"path": p}, None)
            self.assertEqual(eff2["content"], "FILE_CONTENT")
            eff3 = s01_artifact._effective_content(
                {"path": "nope.txt", "exists": True, "size_bytes": 10}, None)
            self.assertTrue(eff3["exists"])
            self.assertEqual(eff3["size_bytes"], 10)

    def test_verify_l1_missing(self):
        out = s01_artifact.verify({"artifacts": [
            {"path": "no/such/file.txt", "type": "code"}]}, EX)
        self.assertEqual(out["verdict"], "INCOMPLETE")
        self.assertEqual(out["gaps"][0]["level"], "L1_EXISTS")
        self.assertEqual(out["gaps"][0]["reason"], "文件不存在")

    def test_verify_l2_stub(self):
        out = s01_artifact.verify({"artifacts": [
            {"path": "a.py", "content": "def f():\n    pass\n",
             "references": ["b.py"]}]}, None)
        self.assertEqual(out["gaps"][0]["level"], "L2_SUBSTANTIVE")

    def test_verify_l3_island(self):
        out = s01_artifact.verify({"artifacts": [
            {"path": "a.py", "content": "print('real code')\n"}]}, None)
        self.assertEqual(out["gaps"][0]["level"], "L3_WIRED")

    def test_verify_l3_ways(self):
        cases = [
            ({"path": "main.py", "content": "print(1)\n", "entry_point": True},
             "entry_point"),
            ({"path": "a.py", "content": "print(1)\n",
              "references": ["x.py", "y.py"]}, "referenced_by:2"),
            ({"path": "a.py", "content": "print(1)\n", "tested": ["t_a.py"]},
             "tested_by:1"),
        ]
        for art, expect in cases:
            with self.subTest(art["path"]):
                out = s01_artifact.verify({"artifacts": [art]}, None)
                self.assertTrue(out["ok"])
                rec = out["per_artifact"][art["path"]]
                self.assertEqual(rec["l3_wired"]["reason"], expect)

    def test_verify_empty_manifest(self):
        out = s01_artifact.verify({"artifacts": []}, None)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T04 gate：run（退出码唯一信号）/ audit（STRENGTH-001..007）
# --------------------------------------------------------------------------- #
class T04(unittest.TestCase):

    def test_run_one_skipped(self):
        rec = s02_gate._run_one({"name": "g", "command": "NONE"},
                                c.load_thresholds()["gate"])
        self.assertEqual(rec["status"], "SKIPPED")
        self.assertIsNone(rec["exit_code"])

    def test_run_one_pass(self):
        rec = s02_gate._run_one(
            {"name": "g", "command": f'"{sys.executable}" -c "print(42)"'},
            c.load_thresholds()["gate"])
        self.assertEqual(rec["status"], "PASS")
        self.assertEqual(rec["exit_code"], 0)
        self.assertIn("42", rec["stdout"])

    def test_run_one_fail(self):
        rec = s02_gate._run_one(
            {"name": "g",
             "command": f'"{sys.executable}" -c "import sys; sys.exit(3)"'},
            c.load_thresholds()["gate"])
        self.assertEqual(rec["status"], "FAIL")
        self.assertEqual(rec["exit_code"], 3)

    def test_run_one_timeout(self):
        rec = s02_gate._run_one(
            {"name": "g",
             "command": f'"{sys.executable}" -c "import time; time.sleep(20)"',
             "timeout_s": 1},
            c.load_thresholds()["gate"])
        self.assertEqual(rec["status"], "FAIL")
        self.assertEqual(rec["reason"], "TIMEOUT")
        self.assertTrue(rec["timeout"])
        self.assertLess(rec["elapsed_ms"], 10000)

    def test_run_dirty_overall(self):
        out = s02_gate.run_gates(load(fx("gate_run_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["overall"], "FAIL")
        self.assertEqual(out["pass_count"], 1)
        self.assertEqual(out["fail_count"], 2)
        self.assertEqual(out["skipped_count"], 0)
        reasons = [r.get("reason") for r in out["records"]
                   if r["status"] == "FAIL"]
        self.assertIn("TIMEOUT", reasons)

    def test_run_all_skipped_overall_pass(self):
        out = s02_gate.run_gates({"gates": [{"name": "a", "command": "NONE"},
                                            {"name": "b", "command": ""}]})
        self.assertTrue(out["ok"])
        self.assertEqual(out["overall"], "PASS")
        self.assertEqual(out["skipped_count"], 2)
        self.assertEqual(out["executed_count"], 0)

    def test_run_empty_gates(self):
        out = s02_gate.run_gates({"gates": []})
        self.assertFalse(out["ok"])

    def test_audit_v1_patterns(self):
        out = s02_gate.audit(load(os.path.join(CASES, "harness-audit",
                                               "harness-evidence-v1.json")))
        self.assertFalse(out["ok"])
        self.assertEqual([f["id"] for f in out["findings"]],
                         ["STRENGTH-001", "STRENGTH-007"])
        self.assertEqual(out["error_count"], 2)
        self.assertEqual(out["warning_count"], 0)
        self.assertEqual(out["score"], 70)
        self.assertEqual(out["tier"], "at-risk")
        self.assertEqual(out["verdict"], "FAIL")

    def test_audit_v2_clean(self):
        out = s02_gate.audit(load(os.path.join(CASES, "harness-audit",
                                               "harness-evidence-v2.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["error_count"], 0)
        self.assertEqual(out["score"], 100)
        self.assertEqual(out["tier"], "solid")
        self.assertEqual(out["verdict"], "PASS")

    def test_audit_pattern_matrix(self):
        triggers = [
            ({"docs": ["this gate never blocks deploys"]},
             "STRENGTH-001", "error"),
            ({"baseline": {"auto_update": "auto"}},
             "STRENGTH-002", "error"),
            ({"skip_categories": [{"name": "flaky"}, {"name": "slow"},
                                   {"name": "wip"}]},
             "STRENGTH-003", "warning"),
            ({"layers": [{"name": "l1"}]}, "STRENGTH-004", "error"),
            ({"default_tier": "theatre"}, "STRENGTH-005", "warning"),
            ({"baseline_update_pr": {"auto_approve": True}},
             "STRENGTH-006", "error"),
            ({"baseline_update_pr": {"auto_approve": False, "reviewers": []}},
             "STRENGTH-006", "error"),
            ({"snapshot": {"passed": True, "checks": ["lint"], "signals": {}}},
             "STRENGTH-007", "error"),
        ]
        for ev, pid, sev in triggers:
            with self.subTest(pid):
                out = s02_gate.audit(ev)
                self.assertEqual([f["id"] for f in out["findings"]], [pid])
                self.assertEqual(out["findings"][0]["severity"], sev)

    def test_audit_score_math(self):
        # 1 error → 100-15=85（solid 下限），但 error 存活即 FAIL
        out = s02_gate.audit({"docs": ["gate never blocks"]})
        self.assertEqual(out["score"], 85)
        self.assertEqual(out["tier"], "solid")
        self.assertEqual(out["verdict"], "FAIL")
        self.assertFalse(out["ok"])
        # 1 warning → 95：warning 不阻断结论（verdict=PASS），
        # 但 WARN 检查仍在 → ok=False（退出码非 0，提醒健康度）
        out = s02_gate.audit({"default_tier": "theatre"})
        self.assertEqual(out["score"], 95)
        self.assertEqual(out["verdict"], "PASS")
        self.assertFalse(out["ok"])

    def test_audit_score_clamp(self):
        out = s02_gate.audit({"docs": ["never blocks"] * 8})
        self.assertEqual(out["score"], 0)
        self.assertEqual(out["tier"], "theatre")

    def test_audit_not_evaluable(self):
        out = s02_gate.audit({})
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "NOT_EVALUABLE")
        self.assertIsNone(out["score"])

    def test_audit_string_items(self):
        # STRENGTH-001 对纯字符串项健壮（升级踩坑）
        out = s02_gate.audit({"hooks": ["this hook always exits 0"]})
        self.assertEqual([f["id"] for f in out["findings"]], ["STRENGTH-001"])


# --------------------------------------------------------------------------- #
# T05 criteria：review 三态 / delta 对照
# --------------------------------------------------------------------------- #
class T05(unittest.TestCase):

    def _th(self):
        return c.load_thresholds()["criteria"]

    def test_evidence_specific(self):
        f = s03_criteria._evidence_specific
        th = self._th()
        self.assertTrue(f("src/landing.py:42", th))
        self.assertTrue(f("conversion_rate.value", th))
        self.assertTrue(f("verified: 3 次真实运行", th))
        self.assertTrue(f("not verified: 缺运行记录", th))
        self.assertFalse(f("已检查，看起来没问题", th))
        self.assertFalse(f("", th))

    def test_judge_statuses(self):
        j = s03_criteria._judge
        th = self._th()
        self.assertEqual(j({"id": "c1", "evidence": "a.py:1"}, th)["status"],
                         "pass")
        self.assertEqual(j({"id": "c2", "evidence": "a.py:1", "partial": True},
                           th)["status"], "warn")
        self.assertEqual(j({"id": "c3"}, th)["reason"], "no_evidence")
        self.assertEqual(j({"id": "c4", "evidence": "a.py:1", "issues": ["x"]},
                           th)["reason"], "declared_issues")
        self.assertEqual(j({"id": "c5", "evidence": "看起来对"}, th)["reason"],
                         "evidence_not_specific")

    def test_review_clean(self):
        out = s03_criteria.review(load(fx("criteria_review.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["counts"]["fail"], 0)
        self.assertEqual(sum(out["counts"].values()),
                         len(out["criteria_results"]))

    def test_review_dirty(self):
        out = s03_criteria.review(load(fx("criteria_review_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(out["counts"], {"pass": 1, "warn": 0, "fail": 2})
        reasons = [r["reason"] for r in out["criteria_results"]]
        self.assertIn("no_evidence", reasons)
        self.assertIn("evidence_not_specific", reasons)

    def test_review_empty(self):
        out = s03_criteria.review({"criteria": []})
        self.assertFalse(out["ok"])

    def test_delta_fixed_new_remaining(self):
        out = s03_criteria.delta(load(fx("criteria_delta.json")),
                                 load(fx("criteria_delta_state.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["fixed_count"], 1)
        self.assertEqual(out["new_count"], 0)
        self.assertEqual(out["remaining_count"], 0)
        self.assertEqual(out["verdict"], "PASS")

    def test_delta_by_id_not_order(self):
        # 两轮顺序不同：按 id 对照，不按序
        cur = {"criteria": [
            {"id": "b", "evidence": "x.py:1"},
            {"id": "a", "evidence": "x.py:2"},
            {"id": "c"},
        ]}
        prev = {"criteria_results": [
            {"id": "a", "status": "fail"},
            {"id": "b", "status": "pass"},
            {"id": "c", "status": "fail"},
        ]}
        out = s03_criteria.delta(cur, prev)
        self.assertEqual(out["delta"]["fixed"], ["a"])
        self.assertEqual(out["delta"]["new"], [])
        self.assertEqual(out["delta"]["remaining"], ["c"])


# --------------------------------------------------------------------------- #
# T06 quality：critique 三查 / converge 收敛
# --------------------------------------------------------------------------- #
class T06(unittest.TestCase):

    def test_critique_clean(self):
        out = s04_quality.critique(load(fx("quality_critique.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["error_count"], 0)
        self.assertTrue(all(x["status"] == "verified"
                            for x in out["claims_checked"]))

    def test_critique_dirty(self):
        out = s04_quality.critique(load(fx("quality_critique_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(out["error_count"], 4)
        self.assertEqual(len(out["claims_checked"]), 3)
        self.assertEqual(sum(1 for x in out["claims_checked"]
                             if x["status"] == "verified"), 1)

    def test_critique_hedge(self):
        out = s04_quality.critique({"claims": [
            {"id": "c1", "text": "登录功能 This should work fine",
             "kind": "completion", "evidence_refs": ["run.json:1"]}]})
        self.assertEqual(out["error_count"], 1)
        self.assertEqual(out["findings"][0]["check"], "hedge_language")
        self.assertEqual(out["claims_checked"][0]["status"], "not_verified")

    def test_critique_hedge_chinese(self):
        out = s04_quality.critique({"claims": [
            {"id": "c1", "text": "应该没问题", "kind": "note",
             "evidence_refs": ["a.json"]}]})
        self.assertEqual(out["error_count"], 1)
        self.assertEqual(out["findings"][0]["check"], "hedge_language")

    def test_critique_completion_without_evidence(self):
        out = s04_quality.critique({"claims": [
            {"id": "c1", "text": "登录功能已完成", "kind": "completion"}]})
        self.assertEqual(out["error_count"], 1)
        self.assertEqual(out["findings"][0]["check"],
                         "completion_without_evidence")

    def test_critique_absolutist(self):
        out = s04_quality.critique({"claims": [
            {"id": "c1", "text": "全部测试通过", "kind": "completion"}]})
        self.assertEqual(out["error_count"], 2)
        checks = {f["check"] for f in out["findings"]}
        self.assertIn("absolutist_without_evidence", checks)
        self.assertIn("completion_without_evidence", checks)

    def test_critique_absolutist_with_evidence_ok(self):
        out = s04_quality.critique({"claims": [
            {"id": "c1", "text": "全部测试通过", "kind": "completion",
             "evidence_refs": ["run.json:1"]}]})
        self.assertEqual(out["error_count"], 0)
        self.assertTrue(out["ok"])

    def test_findings_soundness_schema(self):
        out = s04_quality.critique(load(fx("quality_critique_dirty.json")))
        for f in out["findings"]:
            with self.subTest(f["id"]):
                for k in ("id", "check", "title", "detail", "severity",
                          "autoFixable", "suggestedFix", "evidence"):
                    self.assertIn(k, f)

    def test_critique_empty(self):
        out = s04_quality.critique({"claims": []})
        self.assertFalse(out["ok"])

    def test_converge_iterating(self):
        out = s04_quality.converge(load(fx("quality_converge.json")),
                                    load(fx("quality_converge_v2.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "ITERATING")
        self.assertFalse(out["converged"])

    def test_converge_semantics(self):
        # t2 >= t1 即 converged（不再下降）；还在降 → ITERATING
        self.assertEqual(s04_quality.converge({"findings": 3},
                                              {"findings": 3})["verdict"],
                         "CONVERGED")
        self.assertEqual(s04_quality.converge({"findings": 3},
                                              {"findings": 4})["verdict"],
                         "CONVERGED")
        self.assertEqual(s04_quality.converge({"findings": 3},
                                              {"findings": 1})["verdict"],
                         "ITERATING")
        out = s04_quality.converge({}, {"findings": 1})
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "INVALID")
        self.assertIsNone(out["converged"])


# --------------------------------------------------------------------------- #
# T07 facts：check 五维 / trace 回溯
# --------------------------------------------------------------------------- #
class T07(unittest.TestCase):

    def test_compress(self):
        self.assertEqual(s05_facts._compress("12,345.6"), "12345.6")
        self.assertEqual(s05_facts._compress("1 234"), "1234")

    def test_trace_one(self):
        t = s05_facts._trace_one("12345.6", "GMV 达 12345.6 万元")
        self.assertEqual(t["status"], "verified")
        self.assertTrue(t["source_snippet"])
        t = s05_facts._trace_one("12,345.6", "GMV 达 12345.6 万元")
        self.assertEqual(t["status"], "drift")
        t = s05_facts._trace_one("99999", "GMV 达 12345.6 万元")
        self.assertEqual(t["status"], "hallucinated")
        self.assertEqual(t["source_snippet"], "")

    def test_trace_clean_fixture(self):
        out = s05_facts.trace(load(fx("facts_trace.json")),
                              c.load_text(fx("facts_trace_source.txt")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["hallucinated_count"], 0)
        self.assertEqual(out["drift_count"], 0)
        self.assertEqual(out["verified_count"], 2)

    def test_trace_empty(self):
        out = s05_facts.trace({"numbers": []}, "text")
        self.assertFalse(out["ok"])

    def test_check_clean(self):
        out = s05_facts.check(load(fx("facts_check.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["violations"], [])
        self.assertEqual(out["verdict"], "PASS")

    def test_check_dirty_five_dimensions(self):
        out = s05_facts.check(load(fx("facts_check_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(out["violation_count"], 5)
        self.assertEqual(out["blocking_count"], 4)
        self.assertEqual(out["warn_count"], 1)
        rules = [v["rule"] for v in out["violations"]]
        for rule in ("hallucinated", "unsourced", "citation_missing",
                     "precision_drift", "coverage_gap"):
            self.assertIn(rule, rules)
        dims = out["dimension_results"]
        for d in ("traceability", "source_quality", "citation", "precision",
                  "coverage"):
            self.assertEqual(len(dims[d]["violations"]), 1)

    def test_check_medium_not_blocking(self):
        # coverage_gap=medium 不在 blocking 档：整体 PASS 但记 1 违例
        out = s05_facts.check({"facts": [
            {"id": "F1", "claim": "留存率", "numbers": ["42"],
             "source": "留存率 42% 的原文", "source_type": "primary",
             "key_assertions": ["不存在的断言"]}]})
        self.assertEqual(out["violation_count"], 1)
        self.assertEqual(out["violations"][0]["severity"], "medium")
        self.assertEqual(out["blocking_count"], 0)
        self.assertEqual(out["verdict"], "PASS")   # medium 不阻断结论
        # WARN 检查仍在 → ok=False（非绿但放行 verdict）

    def test_check_unsourced(self):
        out = s05_facts.check({"facts": [
            {"id": "F1", "claim": "无来源事实", "numbers": [],
             "source": "", "source_type": "unsourced",
             "key_assertions": []}]})
        rules = [v["rule"] for v in out["violations"]]
        self.assertIn("unsourced", rules)
        self.assertIn("citation_missing", rules)
        self.assertEqual(out["verdict"], "FAIL")

    def test_check_invalid_source_type(self):
        out = s05_facts.check({"facts": [
            {"id": "F1", "claim": "x", "numbers": [],
             "source": "s", "source_type": "internal",
             "key_assertions": []}]})
        self.assertEqual(out["violations"][0]["rule"], "invalid_source_type")

    def test_check_empty(self):
        out = s05_facts.check({"facts": []})
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T08 strengths：mark / recheck 三查
# --------------------------------------------------------------------------- #
class T08(unittest.TestCase):

    def test_mark_clean(self):
        out = s06_strengths.mark(load(fx("strengths_mark.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["invalid"], [])

    def test_mark_dirty_missing_why(self):
        out = s06_strengths.mark(load(fx("strengths_mark_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(out["invalid"][0]["id"], "K1")
        self.assertEqual(out["invalid"][0]["missing_fields"], ["why_keep"])

    def test_mark_empty(self):
        out = s06_strengths.mark({"keep_list": []})
        self.assertFalse(out["ok"])

    def test_recheck_clean(self):
        out = s06_strengths.recheck(load(fx("strengths_recheck.json")),
                                     load(fx("strengths_recheck_new.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["recheck_verdict"], "PASS")
        self.assertEqual(out["downgrades"], [])
        self.assertEqual(out["untraceable_new_fails"], [])
        self.assertEqual(out["resurfaced_resolved"], [])

    def test_recheck_dirty(self):
        out = s06_strengths.recheck(
            load(fx("strengths_recheck_dirty.json")),
            load(fx("strengths_recheck_new_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["recheck_verdict"], "FAIL")
        self.assertEqual(len(out["downgrades"]), 1)
        self.assertEqual(out["downgrades"][0]["keep_id"], "K1")
        self.assertFalse(out["downgrades"][0]["documented"])
        self.assertEqual([x["id"] for x in out["untraceable_new_fails"]],
                         ["NF1", "NF3"])
        self.assertEqual([x["id"] for x in out["resurfaced_resolved"]], ["PF1"])

    def test_recheck_resolved_not_resurfaced(self):
        # 上一轮已 resolved、本轮不再报 → 不算重报
        prev = {"keep_list": [{"id": "K1", "what": "x", "why_keep": "y",
                               "evidence": "a.md:1"}],
                "findings": [{"id": "PF1", "severity": "error",
                              "resolved": True}]}
        new = {"keep_list": [{"id": "K1", "what": "x", "why_keep": "y",
                              "evidence": "a.md:1"}],
               "findings": []}
        out = s06_strengths.recheck(prev, new)
        self.assertEqual(out["recheck_verdict"], "PASS")
        self.assertEqual(out["resurfaced_resolved"], [])


# --------------------------------------------------------------------------- #
# T09 human：package 身份红线 / ingest 契约 / ack 归档
# --------------------------------------------------------------------------- #
class T09(unittest.TestCase):

    def test_package_clean(self):
        out = s07_human.package(load(fx("human_package.json")))
        self.assertTrue(out["ok"])
        self.assertFalse(out["self_review_blocked"])
        self.assertTrue(out["package_valid"])
        self.assertEqual(out["producer"], "r08")
        self.assertEqual(out["reviewer"], "r04")

    def test_package_identity_redline(self):
        out = s07_human.package(load(fx("human_package_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertTrue(out["self_review_blocked"])
        self.assertFalse(out["package_valid"])
        self.assertEqual(out["producer"], out["reviewer"])

    def test_package_missing_field(self):
        data = load(fx("human_package.json"))
        del data["deadline"]
        out = s07_human.package(data)
        self.assertFalse(out["ok"])
        self.assertFalse(out["package_valid"])
        dims = [ch["dim"] for ch in out["checks"] if not ch["ok"]]
        self.assertIn("human:package:deadline", dims)

    def test_ingest_clean(self):
        out = s07_human.ingest(load(fx("human_ingest.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["violations"], [])
        self.assertTrue(out["edits_saved"])
        actions = [p.get("action") for p in out["applied_plan"]]
        self.assertIn("apply_verbatim", actions)
        self.assertIn("remove_block", actions)
        self.assertIn("relocate_block", actions)
        self.assertIn("re_read_files", actions)
        self.assertEqual(out["comments_total"], 2)
        self.assertEqual(out["edits_total"], 3)

    def test_ingest_dirty_rules(self):
        out = s07_human.ingest(load(fx("human_ingest_dirty.json")))
        self.assertFalse(out["ok"])
        rules = [v["rule"] for v in out["violations"]]
        for rule in ("invalid_comment_kind", "anchor_missing",
                     "invalid_edit_kind", "after_missing",
                     "moved_missing_locator"):
            self.assertIn(rule, rules)
        self.assertEqual(out["comments_total"], 2)
        self.assertEqual(out["edits_total"], 3)
        self.assertFalse(out["edits_saved"])

    def test_ingest_edits_saved_reread(self):
        out = s07_human.ingest({"status": "feedback", "pages": [
            {"file": "a.md", "edits_saved": True, "comments": [],
             "edits": []}]})
        self.assertTrue(out["ok"])
        self.assertTrue(out["edits_saved"])
        actions = [p.get("action") for p in out["applied_plan"]]
        self.assertIn("re_read_files", actions)

    def test_ingest_truncated_reread(self):
        out = s07_human.ingest({"status": "feedback", "pages": [
            {"file": "a.md", "edits": [
                {"label": "e1", "kind": "edited", "after": "改后文本",
                 "truncated": True}]}]})
        plan = [p for p in out["applied_plan"]
                if p.get("action") == "apply_verbatim"][0]
        self.assertTrue(plan["truncated"])
        self.assertTrue(plan["re_read_required"])

    def test_ingest_anchor_mismatch(self):
        out = s07_human.ingest({"status": "feedback", "pages": [
            {"file": "a.md", "comments": [
                {"kind": "selection", "quote": "原文", "feedback": "f",
                 "anchor": {"prefix": "p", "quote": "不一致", "suffix": "s"}}],
             "edits": []}]})
        rules = [v["rule"] for v in out["violations"]]
        self.assertIn("anchor_quote_mismatch", rules)

    def test_ingest_empty_batch(self):
        out = s07_human.ingest({"status": "feedback", "pages": []})
        self.assertFalse(out["ok"])
        self.assertEqual(out["violations"][0]["rule"], "empty_batch")

    def test_ack_clean(self):
        out = s07_human.ack(load(fx("human_ack.json")))
        self.assertTrue(out["ok"])
        self.assertEqual(out["ack_status"], "ACKED")
        self.assertTrue(out["acknowledged"])
        self.assertEqual(out["uncopied"], [])

    def test_ack_dirty_blocked(self):
        out = s07_human.ack(load(fx("human_ack_dirty.json")))
        self.assertFalse(out["ok"])
        self.assertEqual(out["ack_status"], "BLOCKED")
        self.assertEqual(len(out["uncopied"]), 1)
        self.assertEqual(out["uncopied"][0]["path"], "staged/annotated.html")

    def test_ack_no_staged(self):
        out = s07_human.ack({"staged_assets": []})
        self.assertTrue(out["ok"])
        self.assertTrue(out["acknowledged"])


# --------------------------------------------------------------------------- #
# T10 对抗评审五检查（身份红线/修复红线/证据链/降级/禁词）
# --------------------------------------------------------------------------- #
class T10(unittest.TestCase):

    def _pkt(self, result):
        return review_lib.review_packet({"skill": "x", "action": "y",
                                         "result": result})

    def test_review_clean(self):
        out = review_lib.review_packet(
            {"skill": "criteria", "action": "review",
             "result": load(fx("review_result_clean.json"))})
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")
        self.assertIsNone(out["failure_category"])

    def test_review_dirty_evidence_gate(self):
        out = review_lib.review_packet(
            {"skill": "criteria", "action": "review",
             "result": load(fx("review_result_dirty.json"))})
        self.assertFalse(out["ok"])
        self.assertEqual(out["failure_category"], "evidence_gate")
        self.assertEqual(out["route"], "react")

    def test_self_review_gate(self):
        out = self._pkt({"producer": "r08", "reviewer": "r08",
                         "verdict": "PASS", "evidence": ["e"]})
        self.assertFalse(out["ok"])
        self.assertEqual(out["failure_category"], "self_review_gate")
        self.assertEqual(out["route"], "react")

    def test_never_fixes(self):
        out = self._pkt({"verdict": "FAIL", "findings": [],
                         "applied_fixes": ["x"]})
        self.assertFalse(out["ok"])
        self.assertEqual(out["failure_category"], "never_fixes")

    def test_hedge_words_route_writer(self):
        out = self._pkt({"verdict": "PASS", "evidence": ["e"],
                         "summary": "This should be fine"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["failure_category"], "hedge_words")
        self.assertEqual(out["route"], "writer")

    def test_keep_list_integrity(self):
        out = self._pkt({"verdict": "FAIL",
                         "downgrades": [{"keep_id": "K1",
                                         "new_status": "FAIL"}]})
        self.assertFalse(out["ok"])
        self.assertEqual(out["failure_category"], "keep_list_integrity")

    def test_keep_downgrade_with_reason_ok(self):
        out = self._pkt({"verdict": "FAIL",
                         "downgrades": [{"keep_id": "K1", "new_status": "FAIL",
                                         "resolution_reason": "上游接口变更"}]})
        self.assertTrue(out["ok"])

    def test_hedge_not_scanned_in_msg(self):
        # msg/detail 不扫禁词，只扫结论键（R06 教训）
        out = self._pkt({"verdict": "PASS", "evidence": ["e"],
                         "msg": "用户原文写着 should work"})
        self.assertTrue(out["ok"])

    def test_priority_identity_first(self):
        out = self._pkt({"producer": "a", "reviewer": "a", "verdict": "FAIL",
                         "applied_fixes": ["x"]})
        self.assertEqual(out["failure_category"], "self_review_gate")

    def test_pass_without_evidence(self):
        out = self._pkt({"verdict": "PASS", "summary": "all good"})
        self.assertEqual(out["failure_category"], "evidence_gate")


# --------------------------------------------------------------------------- #
# T11 契约登记表：输入/输出 schema 双向校验
# --------------------------------------------------------------------------- #
class T11(unittest.TestCase):

    def test_registry_complete(self):
        self.assertEqual(contracts.skill_names(),
                         ["artifact", "gate", "criteria", "quality", "facts",
                          "strengths", "human"])
        expect = {"artifact": 2, "gate": 2, "criteria": 2, "quality": 2,
                  "facts": 2, "strengths": 2, "human": 3}
        for s, n in expect.items():
            self.assertEqual(len(contracts.actions(s)), n)
        for m in SKILLS:
            self.assertEqual(sorted(contracts.actions(m.NAME)),
                             sorted(m.ACTIONS.keys()))

    def test_validate_input_all_clean(self):
        for skill, action, _ in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                data = load(fx(f"{skill}_{action}.json"))
                v = contracts.validate_input(skill, action, data)
                self.assertTrue(v["ok"], v["errors"])

    def test_validate_input_negative(self):
        v = contracts.validate_input("gate", "run", {"gates": "not-a-list"})
        self.assertFalse(v["ok"])
        v = contracts.validate_input("artifact", "inventory", {})
        self.assertFalse(v["ok"])
        v = contracts.validate_input("human", "package", {"producer": "a"})
        self.assertFalse(v["ok"])

    def test_validate_output_all_clean(self):
        for skill, action, _ in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                result = result_of(skill, action)
                v = contracts.validate_output(skill, action, result)
                self.assertTrue(v["ok"], v["errors"])

    def test_validate_output_negative(self):
        # 输出契约硬口径：ok:boolean + checks:array 缺一即 fail
        v = contracts.validate_output("artifact", "inventory", {"ok": True})
        self.assertFalse(v["ok"])
        v = contracts.validate_output("gate", "run", {"checks": []})
        self.assertFalse(v["ok"])

    def test_unknown_contract(self):
        v = contracts.validate_input("nope", "x", {})
        self.assertFalse(v["ok"])
        v = contracts.validate_output("artifact", "nope",
                                      {"ok": True, "checks": []})
        self.assertFalse(v["ok"])


# --------------------------------------------------------------------------- #
# T12 确定性验证器：materials / verdict / plan / runlog
# --------------------------------------------------------------------------- #
class T12(unittest.TestCase):

    def test_materials_clean(self):
        out = harness_lib.validate_materials(fx("artifact_inventory.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["grade"], "PASS")
        self.assertEqual(out["verdict"], "COMPLETE")

    def test_materials_dirty_blocked(self):
        out = harness_lib.validate_materials(fx("artifact_inventory_dirty.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["grade"], "BLOCKED")
        self.assertEqual(out["missing_required_count"], 1)

    def test_verdict_clean(self):
        out = harness_lib.validate_verdict(fx("review_result_clean.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["grade"], "PASS")
        self.assertTrue(out["has_evidence_chain"])

    def test_verdict_dirty(self):
        out = harness_lib.validate_verdict(fx("review_result_dirty.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["grade"], "FAIL")

    def _vd(self, data):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "v.json")
            c.write_json(p, data)
            return harness_lib.validate_verdict(p)

    def test_verdict_rules(self):
        self.assertFalse(self._vd({"verdict": "MAYBE"})["ok"])      # 枚举外
        self.assertFalse(self._vd({"verdict": "PASS"})["ok"])       # PASS 无证据链
        self.assertTrue(self._vd({"verdict": "PASS", "findings": [],
                                  "evidence": ["e"]})["ok"])
        self.assertFalse(self._vd({"verdict": "BLOCKED",
                                    "findings": []})["ok"])         # BLOCKED 无理由
        self.assertTrue(self._vd({"verdict": "BLOCKED",
                                  "blocked_reason": "缺输入",
                                  "findings": []})["ok"])
        self.assertFalse(self._vd({"verdict": "FAIL",
                                    "findings": [{"id": "F1"}]})["ok"])

    def test_plan_good_and_bad(self):
        out = harness_lib.validate_plan(fx("plan_good.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["grade"], "PASS")
        out = harness_lib.validate_plan(fx("plan_bad.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["grade"], "FAIL")
        dims = [ch["dim"] for ch in out["checks"] if not ch["ok"]]
        self.assertIn("plan:analytical_step", dims)
        self.assertIn("plan:stop_condition", dims)

    def test_runlog(self):
        agent.ws.log_run("r04-tests", {"skill": "tests/runlog", "ok": True})
        out = harness_lib.validate_runlog(5)
        self.assertTrue(out["ok"])
        rows = out["rows"]
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[-1]["skill"], "tests/runlog")
        self.assertIn("ts", rows[-1])


# --------------------------------------------------------------------------- #
# T13 案例库：结构门禁 + 全步骤 expect 数字对拍
# --------------------------------------------------------------------------- #
class T13(unittest.TestCase):

    def test_list_and_validate(self):
        rows = cases_lib.list_cases()
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(r["case_id"] for r in rows),
                         ["harness-audit", "landing-acceptance"])
        for r in rows:
            v = cases_lib.validate_case(r["case_id"])
            self.assertTrue(v["ok"], v["errors"])

    def test_landing_case_steps(self):
        L = os.path.join(CASES, "landing-acceptance")
        # step1 判据三态评审
        r1 = s03_criteria.review(load(os.path.join(L, "landing-criteria-v1.json")))
        self.assertEqual(r1["counts"], {"pass": 2, "warn": 1, "fail": 1})
        self.assertEqual(r1["verdict"], "FAIL")
        self.assertEqual(
            {x["id"]: x["reason"] for x in r1["criteria_results"]}["AC-04"],
            "no_evidence")
        # step2 完成声明三查
        r2 = s04_quality.critique(load(os.path.join(L, "landing-claims-v1.json")))
        self.assertEqual(len(r2["claims_checked"]), 3)
        self.assertEqual(sum(1 for x in r2["claims_checked"]
                             if x["status"] == "verified"), 1)
        self.assertEqual(r2["error_count"], 4)
        self.assertEqual(r2["verdict"], "FAIL")
        # step3 评审包（身份红线通过）
        r3 = s07_human.package(load(os.path.join(L, "landing-package-request.json")))
        self.assertFalse(r3["self_review_blocked"])
        self.assertTrue(r3["package_valid"])
        self.assertEqual(r3["producer"], "r08")
        self.assertEqual(r3["reviewer"], "r04")
        # step4 R08 修复后复评
        r4 = s04_quality.critique(load(os.path.join(L, "landing-claims-v2.json")))
        self.assertEqual(len(r4["claims_checked"]), 2)
        self.assertEqual(sum(1 for x in r4["claims_checked"]
                             if x["status"] == "verified"), 2)
        self.assertEqual(r4["error_count"], 0)
        self.assertEqual(r4["verdict"], "PASS")
        # step5 收敛判定
        r5 = s04_quality.converge(load(os.path.join(L, "landing-findings-v1.json")),
                                  load(os.path.join(L, "landing-findings-v2.json")))
        self.assertEqual(r5["v1_count"], 4)
        self.assertEqual(r5["v2_count"], 0)
        self.assertFalse(r5["converged"])
        self.assertEqual(r5["verdict"], "ITERATING")
        # step6 优点复检
        r6 = s06_strengths.recheck(
            load(os.path.join(L, "landing-prev-critique.json")),
            load(os.path.join(L, "landing-recheck-new.json")))
        self.assertEqual(r6["recheck_verdict"], "PASS")
        self.assertEqual(len(r6["downgrades"]), 0)
        self.assertEqual(len(r6["untraceable_new_fails"]), 0)

    def test_harness_audit_case_steps(self):
        HA = os.path.join(CASES, "harness-audit")
        a1 = s02_gate.audit(load(os.path.join(HA, "harness-evidence-v1.json")))
        self.assertEqual([f["id"] for f in a1["findings"]],
                         ["STRENGTH-001", "STRENGTH-007"])
        self.assertEqual(a1["error_count"], 2)
        self.assertEqual(a1["warning_count"], 0)
        self.assertEqual(a1["score"], 70)
        self.assertEqual(a1["tier"], "at-risk")
        self.assertEqual(a1["verdict"], "FAIL")
        a2 = s02_gate.audit(load(os.path.join(HA, "harness-evidence-v2.json")))
        self.assertEqual(a2["findings"], [])
        self.assertEqual(a2["score"], 100)
        self.assertEqual(a2["tier"], "solid")
        self.assertEqual(a2["verdict"], "PASS")

    def test_load_case_meta(self):
        case = cases_lib.load_case("landing-acceptance")
        self.assertEqual(len(case["steps"]), 6)
        self.assertIn("semantic_layer", case)
        for k in ("artifact_type", "terms", "gates", "boundary"):
            self.assertIn(k, case["semantic_layer"])
        v = cases_lib.validate_case("landing-acceptance")
        self.assertEqual(len(v["cartridges"]), 8)


# --------------------------------------------------------------------------- #
# T14 CLI 协议：脏夹具退出码 / manifest / demo / contract / review / case / harness
# --------------------------------------------------------------------------- #
class T14(unittest.TestCase):

    def test_dirty_fixtures_exit_1(self):
        for skill, action, name, extra in DIRTY:
            with self.subTest(name):
                result, rc = run_cli(skill, action, fx(name), extra)
                self.assertIsNotNone(result, name)
                self.assertFalse(result["ok"])
                self.assertEqual(rc, 1)

    def test_manifest_cli(self):
        data, rc = run_cli_json(["manifest"])
        self.assertEqual(rc, 0)
        self.assertEqual(data["role"], "r04")
        self.assertEqual(data["action_count"], 15)

    def test_demo_cli(self):
        cp = subprocess.run([sys.executable, TOOL, "demo"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=HERE, timeout=120)
        self.assertEqual(cp.returncode, 0)

    def test_contract_cli(self):
        data, rc = run_cli_json(["contract", "list"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(data), 15)
        with tempfile.TemporaryDirectory() as td:
            result, _ = run_cli("artifact", "inventory",
                                fx("artifact_inventory.json"))
            p = os.path.join(td, "r.json")
            c.write_json(p, result)
            data, rc = run_cli_json(["contract", "validate",
                                     "--skill", "artifact",
                                     "--action", "inventory",
                                     "--output", p])
            self.assertEqual(rc, 0)
            self.assertTrue(data["ok"])
            # 缺 checks 的输出 → exit 1
            c.write_json(p, {"ok": True})
            data, rc = run_cli_json(["contract", "validate",
                                     "--skill", "artifact",
                                     "--action", "inventory",
                                     "--output", p])
            self.assertEqual(rc, 1)
            self.assertFalse(data["ok"])

    def test_review_cli(self):
        with tempfile.TemporaryDirectory() as td:
            pkt = {"skill": "criteria", "action": "review",
                   "result": load(fx("review_result_clean.json"))}
            p = os.path.join(td, "pkt.json")
            c.write_json(p, pkt)
            data, rc = run_cli_json(["review", "--packet", p])
            self.assertEqual(rc, 0)
            self.assertEqual(data["verdict"], "PASS")
            pkt["result"] = load(fx("review_result_dirty.json"))
            c.write_json(p, pkt)
            data, rc = run_cli_json(["review", "--packet", p])
            self.assertEqual(rc, 1)
            self.assertEqual(data["failure_category"], "evidence_gate")

    def test_case_cli(self):
        data, rc = run_cli_json(["case"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(data), 2)
        data, rc = run_cli_json(["case", "landing-acceptance"])
        self.assertEqual(rc, 0)
        self.assertTrue(data["validate"]["ok"])

    def test_harness_cli(self):
        _, rc = run_cli_json(["harness", "materials",
                              "--input", fx("artifact_inventory.json")])
        self.assertEqual(rc, 0)
        _, rc = run_cli_json(["harness", "materials",
                              "--input", fx("artifact_inventory_dirty.json")])
        self.assertEqual(rc, 1)
        _, rc = run_cli_json(["harness", "verdict",
                              "--input", fx("review_result_clean.json")])
        self.assertEqual(rc, 0)
        _, rc = run_cli_json(["harness", "verdict",
                              "--input", fx("review_result_dirty.json")])
        self.assertEqual(rc, 1)
        _, rc = run_cli_json(["harness", "plan",
                              "--input", fx("plan_good.json")])
        self.assertEqual(rc, 0)
        _, rc = run_cli_json(["harness", "plan",
                              "--input", fx("plan_bad.json")])
        self.assertEqual(rc, 1)
        data, rc = run_cli_json(["harness", "runlog", "--n", "3"])
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(len(data["rows"]), 1)

    def test_harness_missing_input(self):
        data, rc = run_cli_json(["harness", "materials",
                                 "--input", fx("not_exist.json")])
        self.assertEqual(rc, 1)
        self.assertFalse(data["ok"])
        self.assertIn("not found", data["error"])

    def test_unknown_skill_exit_2(self):
        cp = subprocess.run([sys.executable, TOOL, "nope"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=HERE, timeout=60)
        self.assertEqual(cp.returncode, 2)


# --------------------------------------------------------------------------- #
# T15 verify_loop 闭环矩阵（契约×执行×结构×评审门）
# --------------------------------------------------------------------------- #
class T15(unittest.TestCase):

    def test_matrix_all_green(self):
        out = verify_loop.run_matrix()
        self.assertTrue(out["ok"])
        self.assertEqual(out["total"], 15)
        self.assertEqual(out["passed"], 15)
        self.assertEqual(out["failed"], 0)
        self.assertEqual(out["verdict"], "PASS")


if __name__ == "__main__":
    argv = sys.argv[1:]
    kwd = argv[0] if argv else None
    # 统计真实断言数：包装所有 assertX 方法
    _count = {"n": 0}
    _assert_methods = [m for m in dir(unittest.TestCase) if m.startswith("assert")]
    _orig = {m: getattr(unittest.TestCase, m) for m in _assert_methods}

    def _wrap(name):
        orig = _orig[name]

        def f(self, *a, **k):
            _count["n"] += 1
            return orig(self, *a, **k)
        return f

    for name in _assert_methods:
        setattr(unittest.TestCase, name, _wrap(name))

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (T01, T02, T03, T04, T05, T06, T07, T08, T09, T10,
                T11, T12, T13, T14, T15):
        tests = loader.loadTestsFromTestCase(cls)
        if kwd:
            filtered = unittest.TestSuite()
            for t in tests:
                if kwd.lower() in t.id().lower():
                    filtered.addTest(t)
            tests = filtered
        suite.addTests(tests)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    total = res.testsRun
    passed = total - len(res.failures) - len(res.errors)
    n = _count["n"]
    if res.wasSuccessful():
        print(f"\n全部通过: {n} assertions（{passed} 项测试）")
    else:
        print(f"\n通过 {passed} 项（{n} assertions），失败 {total - passed} 项")
    sys.exit(0 if res.wasSuccessful() else 1)
