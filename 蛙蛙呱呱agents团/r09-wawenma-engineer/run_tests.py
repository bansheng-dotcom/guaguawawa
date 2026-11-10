# -*- coding: utf-8 -*-
"""R09 蛙稳码（代码工程官）全量断言测试。

分层（对齐 r05 口径）：
T01 注册/manifest/路由/交付物/阈值
T02 全动作 CLI 冒烟（16 动作）
T03-T10 逐技能语义（8 技能 × clean/dirty 对拍）
T11 对抗评审（test_skipped/irreversible/concrete/scope/evidence 五检查）
T12 契约登记表（输入/输出双向校验）
T13 验证器（materials/testreport/plan/runlog）
T14 案例库（list/validate/steps expect 对拍）
T15 CLI 协议（脏夹具 exit:1 / meta 命令 / 未知命令 exit:2）
T16 verify_loop 闭环矩阵

运行：python run_tests.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

EX = os.path.join(_HERE, "examples")

# 16 动作（skill, action, 输入文件名）
ACTIONS = [
    ("spec", "spec", "spec_spec.json"),
    ("spec", "arch", "spec_arch.json"),
    ("data_api", "schema", "data_api_schema.json"),
    ("data_api", "api", "data_api_api.json"),
    ("fullstack", "feature", "fullstack_feature.json"),
    ("fullstack", "auth", "fullstack_auth.json"),
    ("crossplatform", "build", "crossplatform_build.json"),
    ("crossplatform", "platform", "crossplatform_platform.json"),
    ("testing", "suites", "testing_suites.json"),
    ("testing", "browser", "testing_browser.json"),
    ("debug", "debug", "debug_debug.json"),
    ("debug", "refactor", "debug_refactor.json"),
    ("ops", "migration", "ops_migration.json"),
    ("ops", "security", "ops_security.json"),
    ("special", "mcp", "special_mcp.json"),
    ("special", "godot", "special_godot.json"),
]

# 16 脏夹具（语义负例：ok=false / exit 1）
DIRTY = [
    ("spec", "spec", "spec_spec_dirty.json"),
    ("spec", "arch", "spec_arch_dirty.json"),
    ("data_api", "schema", "data_api_schema_dirty.json"),
    ("data_api", "api", "data_api_api_dirty.json"),
    ("fullstack", "feature", "fullstack_feature_dirty.json"),
    ("fullstack", "auth", "fullstack_auth_dirty.json"),
    ("crossplatform", "build", "crossplatform_build_dirty.json"),
    ("crossplatform", "platform", "crossplatform_platform_dirty.json"),
    ("testing", "suites", "testing_suites_dirty.json"),
    ("testing", "browser", "testing_browser_dirty.json"),
    ("debug", "debug", "debug_debug_dirty.json"),
    ("debug", "refactor", "debug_refactor_dirty.json"),
    ("ops", "migration", "ops_migration_dirty.json"),
    ("ops", "security", "ops_security_dirty.json"),
    ("special", "mcp", "special_mcp_dirty.json"),
    ("special", "godot", "special_godot_dirty.json"),
]


# --------------------------------------------------------------------------- #
# 辅助：子进程调用
# --------------------------------------------------------------------------- #
def run_cli(skill, action, input_path, extra=None):
    cmd = [sys.executable, "agent.py", skill, action, "--input", input_path]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    result = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            result = json.loads(line[len("__AGENT_RESULT__ "):])
            break
    return result, proc.returncode


def run_cli_json(args_list):
    proc = subprocess.run([sys.executable, "agent.py"] + args_list, cwd=_HERE,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60)
    marker = "__AGENT_RESULT__ "
    for line in (proc.stdout or "").splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):]), proc.returncode
            except ValueError:
                pass
    try:
        return json.loads(proc.stdout), proc.returncode
    except (ValueError, TypeError):
        return None, proc.returncode


def result_of(skill, action, input_name):
    """模块直调（不经子进程），供契约/评审复用同一份产出。"""
    import argparse
    from skills import SKILL_BY_NAME
    args = argparse.Namespace(action=action, input=os.path.join(EX, input_name))
    mod = SKILL_BY_NAME[skill]
    return mod.run(args)


# --------------------------------------------------------------------------- #
# T01 注册 / manifest / 路由 / 交付物 / 阈值
# --------------------------------------------------------------------------- #
class T01(unittest.TestCase):
    def test_registration(self):
        from skills import SKILLS, SKILL_BY_NAME
        names = [m.NAME for m in SKILLS]
        self.assertEqual(names, ["spec", "data_api", "fullstack",
                                 "crossplatform", "testing", "debug",
                                 "ops", "special"])
        self.assertEqual(len(SKILL_BY_NAME), 8)
        for m in SKILLS:
            self.assertTrue(m.DESC)
            self.assertTrue(m.ACTIONS)
            self.assertEqual(len(m.ACTIONS), 2)

    def test_manifest(self):
        import agent
        mf = agent.make_manifest()
        self.assertEqual(mf["role"], "r09")
        self.assertEqual(mf["skill_count"], 8)
        self.assertEqual(mf["action_count"], 16)
        self.assertEqual(len(mf["contracts"]), 16)
        self.assertIn("spec/spec", mf["contracts"])
        self.assertEqual(len(mf["intent_routes"]), 16)
        self.assertEqual(mf["boundary"]["never"][0], "跳过测试制造假通过")

    def test_routes(self):
        import agent
        hits = [
            ("技术规格", "spec", "spec"),
            ("架构拓扑", "spec", "arch"),
            ("数据库 schema", "data_api", "schema"),
            ("api 契约", "data_api", "api"),
            ("端到端全栈", "fullstack", "feature"),
            ("登录认证", "fullstack", "auth"),
            ("构建打包", "crossplatform", "build"),
            ("flutter 跨端", "crossplatform", "platform"),
            ("单元测试覆盖率", "testing", "suites"),
            ("playwright 浏览器验证", "testing", "browser"),
            ("调试根因", "debug", "debug"),
            ("性能重构", "debug", "refactor"),
            ("数据迁移", "ops", "migration"),
            ("cve 安全审计", "ops", "security"),
            ("mcp 工具", "special", "mcp"),
            ("godot 工程", "special", "godot"),
            # P2.1：关键词全未命中不再静默落到 spec/spec，交 L02 内核澄清
            ("完全无关的意图", "__clarify__", "clarify"),
        ]
        for intent, s, a in hits:
            routed = agent.route_intent(intent)
            self.assertEqual(routed[:2], (s, a), intent)

    def test_deliverables(self):
        for p in ["SKILL.md", "contracts.py", "review.py", "cases.py",
                  "harness.py", "verify_loop.py", "run_tests.py",
                  "experience/thresholds.json", "experience/plan_schema.json"]:
            self.assertTrue(os.path.isfile(os.path.join(_HERE, p)), p)
        for i in range(1, 9):
            d = os.path.join(_HERE, "references", f"s0{i}")
            self.assertTrue(os.path.isdir(d), d)

    def test_thresholds(self):
        from skills import _common as c
        th = c.load_thresholds()
        for sec in ["spec", "data_api", "fullstack", "crossplatform",
                    "testing", "debug", "ops", "special", "review"]:
            self.assertIn(sec, th, sec)
        self.assertIn("topology_types", th["spec"])
        self.assertIn("module_required", th["spec"])
        self.assertIn("column_types", th["data_api"])
        self.assertIn("http_methods", th["data_api"])
        self.assertIn("auth_methods", th["fullstack"])
        self.assertIn("platforms", th["crossplatform"])
        self.assertIn("build_statuses", th["crossplatform"])
        self.assertIn("suite_types", th["testing"])
        self.assertIn("coverage_min", th["testing"])
        self.assertIn("flow_results", th["testing"])
        self.assertIn("min_repro_steps", th["debug"])
        self.assertIn("irreversible_ops", th["ops"])
        self.assertIn("cve_severities", th["ops"])
        self.assertIn("mcp_transports", th["special"])
        self.assertIn("irreversible_words", th["review"])
        self.assertIn("scope_terms", th["review"])
        self.assertIn("concrete_keys", th["review"])
        self.assertIn("evidence_keys", th["review"])


# --------------------------------------------------------------------------- #
# T02 全动作 CLI 冒烟
# --------------------------------------------------------------------------- #
class T02(unittest.TestCase):
    def test_all_actions_ok(self):
        for s, a, f in ACTIONS:
            res, code = run_cli(s, a, os.path.join(EX, f))
            self.assertIsNotNone(res, f"{s}/{a} 无 __AGENT_RESULT__")
            self.assertTrue(res["ok"], f"{s}/{a} 应 ok=true：{res.get('next')}")
            self.assertEqual(code, 0, f"{s}/{a} 应 exit 0")
            self.assertEqual(res["verdict"], "PASS")

    def test_missing_input(self):
        for s, a, _ in ACTIONS[:3]:
            res, code = run_cli(s, a, os.path.join(EX, "not_exist.json"))
            self.assertFalse(res["ok"])
            self.assertEqual(code, 1)


# --------------------------------------------------------------------------- #
# T03 spec
# --------------------------------------------------------------------------- #
class T03(unittest.TestCase):
    def test_spec_clean(self):
        from skills import s01_spec
        data = json.load(open(os.path.join(EX, "spec_spec.json"), encoding="utf-8"))
        out = s01_spec.spec(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["module_count"], 2)
        self.assertTrue(out["boundary_ok"])

    def test_spec_dirty(self):
        from skills import s01_spec
        data = json.load(open(os.path.join(EX, "spec_spec_dirty.json"), encoding="utf-8"))
        out = s01_spec.spec(data)
        self.assertFalse(out["ok"])
        self.assertFalse(out["boundary_ok"])

    def test_arch_clean(self):
        from skills import s01_spec
        data = json.load(open(os.path.join(EX, "spec_arch.json"), encoding="utf-8"))
        out = s01_spec.arch(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["service_count"], 3)
        self.assertEqual(out["edge_count"], 3)
        self.assertEqual(out["dangling_edges"], [])

    def test_arch_dirty(self):
        from skills import s01_spec
        data = json.load(open(os.path.join(EX, "spec_arch_dirty.json"), encoding="utf-8"))
        out = s01_spec.arch(data)
        self.assertFalse(out["ok"])
        self.assertTrue(out["dangling_edges"])


# --------------------------------------------------------------------------- #
# T04 data_api
# --------------------------------------------------------------------------- #
class T04(unittest.TestCase):
    def test_schema_clean(self):
        from skills import s02_data_api
        data = json.load(open(os.path.join(EX, "data_api_schema.json"), encoding="utf-8"))
        out = s02_data_api.schema(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["table_count"], 2)
        self.assertEqual(out["column_count"], 5)

    def test_schema_dirty(self):
        from skills import s02_data_api
        data = json.load(open(os.path.join(EX, "data_api_schema_dirty.json"), encoding="utf-8"))
        out = s02_data_api.schema(data)
        self.assertFalse(out["ok"])

    def test_api_clean(self):
        from skills import s02_data_api
        data = json.load(open(os.path.join(EX, "data_api_api.json"), encoding="utf-8"))
        out = s02_data_api.api(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["endpoint_count"], 2)
        self.assertEqual(out["error_codes_total"], 3)

    def test_api_dirty(self):
        from skills import s02_data_api
        data = json.load(open(os.path.join(EX, "data_api_api_dirty.json"), encoding="utf-8"))
        out = s02_data_api.api(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T05 fullstack
# --------------------------------------------------------------------------- #
class T05(unittest.TestCase):
    def test_feature_clean(self):
        from skills import s03_fullstack
        data = json.load(open(os.path.join(EX, "fullstack_feature.json"), encoding="utf-8"))
        out = s03_fullstack.feature(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["component_count"], 2)
        self.assertEqual(out["service_count"], 2)
        self.assertEqual(out["e2e_coverage"], 1.0)

    def test_feature_dirty(self):
        from skills import s03_fullstack
        data = json.load(open(os.path.join(EX, "fullstack_feature_dirty.json"), encoding="utf-8"))
        out = s03_fullstack.feature(data)
        self.assertFalse(out["ok"])
        self.assertLess(out["e2e_coverage"], 1.0)

    def test_auth_clean(self):
        from skills import s03_fullstack
        data = json.load(open(os.path.join(EX, "fullstack_auth.json"), encoding="utf-8"))
        out = s03_fullstack.auth(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["auth_method"], "jwt")
        self.assertEqual(out["protected_count"], 2)

    def test_auth_dirty(self):
        from skills import s03_fullstack
        data = json.load(open(os.path.join(EX, "fullstack_auth_dirty.json"), encoding="utf-8"))
        out = s03_fullstack.auth(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T06 crossplatform
# --------------------------------------------------------------------------- #
class T06(unittest.TestCase):
    def test_build_clean(self):
        from skills import s04_crossplatform
        data = json.load(open(os.path.join(EX, "crossplatform_build.json"), encoding="utf-8"))
        out = s04_crossplatform.build(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["target_count"], 3)
        self.assertEqual(out["skipped"], 0)

    def test_build_dirty(self):
        from skills import s04_crossplatform
        data = json.load(open(os.path.join(EX, "crossplatform_build_dirty.json"), encoding="utf-8"))
        out = s04_crossplatform.build(data)
        self.assertFalse(out["ok"])
        self.assertEqual(out["skipped"], 1)

    def test_platform_clean(self):
        from skills import s04_crossplatform
        data = json.load(open(os.path.join(EX, "crossplatform_platform.json"), encoding="utf-8"))
        out = s04_crossplatform.platform(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["target_count"], 3)
        self.assertEqual(out["diff_count"], 2)

    def test_platform_dirty(self):
        from skills import s04_crossplatform
        data = json.load(open(os.path.join(EX, "crossplatform_platform_dirty.json"), encoding="utf-8"))
        out = s04_crossplatform.platform(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T07 testing
# --------------------------------------------------------------------------- #
class T07(unittest.TestCase):
    def test_suites_clean(self):
        from skills import s05_testing
        data = json.load(open(os.path.join(EX, "testing_suites.json"), encoding="utf-8"))
        out = s05_testing.suites(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["suite_count"], 3)
        self.assertEqual(out["skipped"], 0)
        self.assertEqual(out["coverage"], 0.87)

    def test_suites_dirty(self):
        from skills import s05_testing
        data = json.load(open(os.path.join(EX, "testing_suites_dirty.json"), encoding="utf-8"))
        out = s05_testing.suites(data)
        self.assertFalse(out["ok"])
        self.assertEqual(out["skipped"], 5)

    def test_browser_clean(self):
        from skills import s05_testing
        data = json.load(open(os.path.join(EX, "testing_browser.json"), encoding="utf-8"))
        out = s05_testing.browser(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["flow_count"], 3)
        self.assertEqual(out["passed"], 3)
        self.assertEqual(out["flaky"], 0)

    def test_browser_dirty(self):
        from skills import s05_testing
        data = json.load(open(os.path.join(EX, "testing_browser_dirty.json"), encoding="utf-8"))
        out = s05_testing.browser(data)
        self.assertFalse(out["ok"])
        self.assertEqual(out["flaky"], 1)


# --------------------------------------------------------------------------- #
# T08 debug
# --------------------------------------------------------------------------- #
class T08(unittest.TestCase):
    def test_debug_clean(self):
        from skills import s06_debug
        data = json.load(open(os.path.join(EX, "debug_debug.json"), encoding="utf-8"))
        out = s06_debug.debug(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["repro_step_count"], 4)
        self.assertTrue(out["root_cause"])

    def test_debug_dirty(self):
        from skills import s06_debug
        data = json.load(open(os.path.join(EX, "debug_debug_dirty.json"), encoding="utf-8"))
        out = s06_debug.debug(data)
        self.assertFalse(out["ok"])

    def test_refactor_clean(self):
        from skills import s06_debug
        data = json.load(open(os.path.join(EX, "debug_refactor.json"), encoding="utf-8"))
        out = s06_debug.refactor(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["hotspot_count"], 2)
        self.assertEqual(out["regression_count"], 2)

    def test_refactor_dirty(self):
        from skills import s06_debug
        data = json.load(open(os.path.join(EX, "debug_refactor_dirty.json"), encoding="utf-8"))
        out = s06_debug.refactor(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T09 ops
# --------------------------------------------------------------------------- #
class T09(unittest.TestCase):
    def test_migration_clean(self):
        from skills import s07_ops
        data = json.load(open(os.path.join(EX, "ops_migration.json"), encoding="utf-8"))
        out = s07_ops.migration(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["step_count"], 3)
        self.assertEqual(out["irreversible_found"], [])
        self.assertEqual(out["rollback_steps"], 2)

    def test_migration_dirty(self):
        from skills import s07_ops
        data = json.load(open(os.path.join(EX, "ops_migration_dirty.json"), encoding="utf-8"))
        out = s07_ops.migration(data)
        self.assertFalse(out["ok"])
        self.assertTrue(out["irreversible_found"])

    def test_security_clean(self):
        from skills import s07_ops
        data = json.load(open(os.path.join(EX, "ops_security.json"), encoding="utf-8"))
        out = s07_ops.security(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["dependency_count"], 2)
        self.assertEqual(out["leaked_key_count"], 0)

    def test_security_dirty(self):
        from skills import s07_ops
        data = json.load(open(os.path.join(EX, "ops_security_dirty.json"), encoding="utf-8"))
        out = s07_ops.security(data)
        self.assertFalse(out["ok"])
        self.assertEqual(out["leaked_key_count"], 1)


# --------------------------------------------------------------------------- #
# T10 special
# --------------------------------------------------------------------------- #
class T10(unittest.TestCase):
    def test_mcp_clean(self):
        from skills import s08_special
        data = json.load(open(os.path.join(EX, "special_mcp.json"), encoding="utf-8"))
        out = s08_special.mcp(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["transport"], "stdio")
        self.assertEqual(out["tool_count"], 2)

    def test_mcp_dirty(self):
        from skills import s08_special
        data = json.load(open(os.path.join(EX, "special_mcp_dirty.json"), encoding="utf-8"))
        out = s08_special.mcp(data)
        self.assertFalse(out["ok"])

    def test_godot_clean(self):
        from skills import s08_special
        data = json.load(open(os.path.join(EX, "special_godot.json"), encoding="utf-8"))
        out = s08_special.godot(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["scene_count"], 2)
        self.assertEqual(out["script_count"], 2)

    def test_godot_dirty(self):
        from skills import s08_special
        data = json.load(open(os.path.join(EX, "special_godot_dirty.json"), encoding="utf-8"))
        out = s08_special.godot(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T11 对抗评审
# --------------------------------------------------------------------------- #
class T11(unittest.TestCase):
    def _packet(self, name):
        return json.load(open(os.path.join(EX, name), encoding="utf-8"))

    def test_review_clean(self):
        import review
        out = review.review_packet(self._packet("review_clean.json"))
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["verdict"], "PASS")

    def test_test_skipped_gate(self):
        import review
        out = review.review_packet(self._packet("review_test_skipped.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "react")
        self.assertEqual(out["failure_category"], "review:test_skipped")

    def test_irreversible_gate(self):
        import review
        out = review.review_packet(self._packet("review_irreversible.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "writer")
        self.assertEqual(out["failure_category"], "review:irreversible")

    def test_concrete_artifact(self):
        import review
        out = review.review_packet(self._packet("review_no_concrete.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "controller")
        self.assertEqual(out["failure_category"], "review:concrete_artifact")

    def test_scope_boundary(self):
        import review
        out = review.review_packet(self._packet("review_scope.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "writer")
        self.assertEqual(out["failure_category"], "review:scope")

    def test_evidence_gate(self):
        import review
        out = review.review_packet(self._packet("review_no_evidence.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "react")
        self.assertEqual(out["failure_category"], "review:evidence")

    def test_msg_not_scanned(self):
        import review
        packet = {"skill": "ops", "action": "migration",
                  "result": {"ok": True, "verdict": "PASS",
                             "step_count": 1, "irreversible_found": [],
                             "rollback_steps": 1,
                             "summary": "迁移计划合规",
                             "checks": [{"ok": False, "msg": "含 drop table 建议补充授权",
                                         "dim": "d", "sev": "HIGH"}],
                             "next": "x"}}
        out = review.review_packet(packet)
        self.assertTrue(out["ok"], "msg 中的禁词不应触发评审失败")


# --------------------------------------------------------------------------- #
# T12 契约登记表
# --------------------------------------------------------------------------- #
class T12(unittest.TestCase):
    def test_registry_complete(self):
        import contracts
        self.assertEqual(contracts.skill_names(),
                         ["spec", "data_api", "fullstack", "crossplatform",
                          "testing", "debug", "ops", "special"])
        for s in contracts.skill_names():
            self.assertEqual(len(contracts.actions(s)), 2, s)
        from skills import SKILLS
        for m in SKILLS:
            self.assertEqual(sorted(m.ACTIONS), sorted(contracts.actions(m.NAME)),
                             f"{m.NAME} ACTIONS 与契约不对齐")

    def test_input_validation(self):
        import contracts
        for s, a, f in ACTIONS:
            data = json.load(open(os.path.join(EX, f), encoding="utf-8"))
            v = contracts.validate_input(s, a, data)
            self.assertTrue(v["ok"], f"{s}/{a} 干净输入应过契约：{v['errors']}")

    def test_input_validation_negative(self):
        import contracts
        cases = [
            ("spec", "spec", {}),
            ("data_api", "schema", {"tables": [{"name": "t"}]}),
            ("testing", "suites", {"suites": [{"suite_type": "unit"}]}),
            ("ops", "migration", {"steps": [{"operation": "x"}]}),
        ]
        for s, a, data in cases:
            v = contracts.validate_input(s, a, data)
            self.assertFalse(v["ok"], f"{s}/{a} 负例应拒绝")

    def test_output_validation(self):
        import contracts
        for s, a, f in ACTIONS:
            out = result_of(s, a, f)
            v = contracts.validate_output(s, a, out)
            self.assertTrue(v["ok"], f"{s}/{a} 干净产出应过契约：{v['errors']}")

    def test_output_validation_negative(self):
        import contracts
        v = contracts.validate_output("spec", "spec", {"ok": True, "checks": []})
        self.assertFalse(v["ok"])
        v = contracts.validate_output("unknown", "x", {})
        self.assertFalse(v["ok"])


# --------------------------------------------------------------------------- #
# T13 验证器
# --------------------------------------------------------------------------- #
class T13(unittest.TestCase):
    def test_materials(self):
        import harness
        good = harness.validate_materials(os.path.join(EX, "materials_good.json"))
        self.assertTrue(good["ok"])
        self.assertEqual(good["grade"], "PASS")
        bad = harness.validate_materials(os.path.join(EX, "materials_bad.json"))
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["grade"], "BLOCKED")
        self.assertTrue(bad["missing_required"])

    def test_testreport(self):
        import harness
        good = harness.validate_testreport(os.path.join(EX, "testreport_good.json"))
        self.assertTrue(good["ok"])
        bad = harness.validate_testreport(os.path.join(EX, "testreport_bad.json"))
        self.assertFalse(bad["ok"])

    def test_plan(self):
        import harness
        good = harness.validate_plan(os.path.join(EX, "plan_good.json"))
        self.assertTrue(good["ok"], good)
        bad = harness.validate_plan(os.path.join(EX, "plan_bad.json"))
        self.assertFalse(bad["ok"])

    def test_runlog(self):
        import harness
        out = harness.validate_runlog(3)
        self.assertTrue(out["ok"])
        self.assertIn("rows", out)


# --------------------------------------------------------------------------- #
# T14 案例库
# --------------------------------------------------------------------------- #
class T14(unittest.TestCase):
    def test_list_and_validate(self):
        import cases
        rows = cases.list_cases()
        ids = {r["case_id"] for r in rows}
        self.assertTrue({"fullstack-delivery", "refactor-guard"}.issubset(ids))
        for r in rows:
            v = cases.validate_case(r["case_id"])
            self.assertTrue(v["ok"], f"{r['case_id']}: {v['errors']}")

    def test_fullstack_delivery_steps(self):
        import cases
        from skills import SKILL_BY_NAME
        import argparse
        case = cases.load_case("fullstack-delivery")
        self.assertEqual(len(case["steps"]), 4)
        for step in case["steps"]:
            args = argparse.Namespace(action=step["action"],
                                      input=os.path.normpath(os.path.join(
                                          case["case_dir"], step["input"])))
            out = SKILL_BY_NAME[step["skill"]].run(args)
            for k, expected in step["expect"].items():
                self.assertEqual(out.get(k), expected,
                                 f"{step['skill']}/{step['action']} expect[{k}]")

    def test_refactor_guard_steps(self):
        import cases
        from skills import SKILL_BY_NAME
        import argparse
        case = cases.load_case("refactor-guard")
        self.assertEqual(len(case["steps"]), 2)
        for step in case["steps"]:
            args = argparse.Namespace(action=step["action"],
                                      input=os.path.normpath(os.path.join(
                                          case["case_dir"], step["input"])))
            out = SKILL_BY_NAME[step["skill"]].run(args)
            for k, expected in step["expect"].items():
                self.assertEqual(out.get(k), expected,
                                 f"{step['skill']}/{step['action']} expect[{k}]")


# --------------------------------------------------------------------------- #
# T15 CLI 协议
# --------------------------------------------------------------------------- #
class T15(unittest.TestCase):
    def test_dirty_fixtures_exit_1(self):
        for s, a, f in DIRTY:
            res, code = run_cli(s, a, os.path.join(EX, f))
            self.assertIsNotNone(res, f"{s}/{a} 无输出")
            self.assertFalse(res["ok"], f"{s}/{a} 脏数据应 ok=false")
            self.assertEqual(code, 1, f"{s}/{a} 脏数据应 exit 1")

    def test_manifest_cli(self):
        mf, code = run_cli_json(["manifest"])
        self.assertEqual(code, 0)
        self.assertEqual(mf["role"], "r09")

    def test_demo_cli(self):
        proc = subprocess.run([sys.executable, "agent.py", "demo"], cwd=_HERE,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
        self.assertIn("[demo]", proc.stdout)
        self.assertEqual(proc.returncode, 0)

    def test_contract_cli(self):
        rows, code = run_cli_json(["contract", "list"])
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 16)
        v, code = run_cli_json(["contract", "validate", "--skill", "spec",
                                "--action", "spec",
                                "--output", os.path.join(EX, "spec_spec.json")])
        self.assertEqual(code, 1, "原始输入 JSON 不是合法 result，应 exit 1")

    def test_review_cli(self):
        v, code = run_cli_json(["review", "--packet",
                                os.path.join(EX, "review_test_skipped.json")])
        self.assertEqual(code, 1)
        self.assertEqual(v["route"], "react")
        v, code = run_cli_json(["review", "--packet",
                                os.path.join(EX, "review_clean.json")])
        self.assertEqual(code, 0)

    def test_case_cli(self):
        rows, code = run_cli_json(["case"])
        self.assertEqual(code, 0)
        self.assertGreaterEqual(len(rows), 2)
        v, code = run_cli_json(["case", "fullstack-delivery"])
        self.assertEqual(code, 0)
        self.assertTrue(v["validate"]["ok"])

    def test_harness_cli(self):
        v, code = run_cli_json(["harness", "materials",
                                "--input", os.path.join(EX, "materials_bad.json")])
        self.assertEqual(code, 1)
        self.assertEqual(v["grade"], "BLOCKED")

    def test_unknown_command(self):
        proc = subprocess.run([sys.executable, "agent.py", "nope"], cwd=_HERE,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        self.assertEqual(proc.returncode, 2)


# --------------------------------------------------------------------------- #
# T16 verify_loop 闭环矩阵
# --------------------------------------------------------------------------- #
class T16(unittest.TestCase):
    def test_verify_loop_all_green(self):
        import verify_loop
        out = verify_loop.run_all()
        self.assertTrue(out["ok"], f"闭环矩阵有红：\n" +
                        json.dumps([r for r in out["matrix"] if not r.get("ok")],
                                   ensure_ascii=False, indent=2))
        self.assertEqual(out["total"], 32)
        self.assertEqual(out["failed"], 0)
        self.assertEqual(out["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
