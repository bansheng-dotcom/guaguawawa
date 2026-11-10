# -*- coding: utf-8 -*-
"""R05 蛙深远（战略研究官）全量断言测试。

分层（对齐 r04 口径）：
T01 注册/manifest/路由/交付物/阈值
T02 全动作 CLI 冒烟（14 动作）
T03-T09 逐技能语义（7 技能 × clean/dirty 对拍）
T10 对抗评审（unsourced/evidence/decision/scope/hedge 五检查）
T11 契约登记表（输入/输出双向校验）
T12 验证器（materials/verdict/plan/runlog）
T13 案例库（list/validate/steps expect 对拍）
T14 CLI 协议（脏夹具 exit:1 / meta 命令 / 未知命令 exit:2）
T15 verify_loop 闭环矩阵

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

# 14 动作（skill, action, 输入文件名）
ACTIONS = [
    ("research", "ledger", "research_ledger.json"),
    ("research", "report", "research_report.json"),
    ("industry", "landscape", "industry_landscape.json"),
    ("industry", "concentration", "industry_concentration.json"),
    ("competitor", "matrix", "competitor_matrix.json"),
    ("competitor", "battlecard", "competitor_battlecard.json"),
    ("business", "canvas", "business_canvas.json"),
    ("business", "monetize", "business_monetize.json"),
    ("sizing", "size", "sizing_size.json"),
    ("sizing", "sensitivity", "sizing_sensitivity.json"),
    ("scenario", "pestel", "scenario_pestel.json"),
    ("scenario", "premortem", "scenario_premortem.json"),
    ("auto", "plan", "auto_plan.json"),
    ("auto", "track", "auto_track.json"),
]

# 14 脏夹具（语义负例：ok=false / exit 1）
DIRTY = [
    ("research", "ledger", "research_ledger_dirty.json"),
    ("research", "report", "research_report_dirty.json"),
    ("industry", "landscape", "industry_landscape_dirty.json"),
    ("industry", "concentration", "industry_concentration_dirty.json"),
    ("competitor", "matrix", "competitor_matrix_dirty.json"),
    ("competitor", "battlecard", "competitor_battlecard_dirty.json"),
    ("business", "canvas", "business_canvas_dirty.json"),
    ("business", "monetize", "business_monetize_dirty.json"),
    ("sizing", "size", "sizing_size_dirty.json"),
    ("sizing", "sensitivity", "sizing_sensitivity_dirty.json"),
    ("scenario", "pestel", "scenario_pestel_dirty.json"),
    ("scenario", "premortem", "scenario_premortem_dirty.json"),
    ("auto", "plan", "auto_plan_dirty.json"),
    ("auto", "track", "auto_track_dirty.json"),
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
    try:
        return json.loads(proc.stdout), proc.returncode
    except ValueError:
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
        self.assertEqual(names, ["research", "industry", "competitor",
                                 "business", "sizing", "scenario", "auto"])
        self.assertEqual(len(SKILL_BY_NAME), 7)
        for m in SKILLS:
            self.assertTrue(m.DESC)
            self.assertTrue(m.ACTIONS)
            self.assertEqual(len(m.ACTIONS), 2)

    def test_manifest(self):
        import agent
        mf = agent.make_manifest()
        self.assertEqual(mf["role"], "r05")
        self.assertEqual(mf["skill_count"], 7)
        self.assertEqual(mf["action_count"], 14)
        self.assertEqual(len(mf["contracts"]), 14)
        self.assertIn("research/ledger", mf["contracts"])
        self.assertEqual(len(mf["intent_routes"]), 14)
        self.assertEqual(mf["boundary"]["never"][0], "无源断言（claims 必须挂来源）")

    def test_routes(self):
        import agent
        hits = [
            ("证据台账", "research", "ledger"),
            ("研究报告", "research", "report"),
            ("行业地图", "industry", "landscape"),
            ("市场集中度 HHI", "industry", "concentration"),
            ("竞品矩阵", "competitor", "matrix"),
            ("战斗卡", "competitor", "battlecard"),
            ("商业画布", "business", "canvas"),
            ("变现与 LTV", "business", "monetize"),
            ("市场规模 TAM", "sizing", "size"),
            ("敏感性分析", "sizing", "sensitivity"),
            ("PESTEL 宏观", "scenario", "pestel"),
            ("pre-mortem 推演", "scenario", "premortem"),
            ("研究计划", "auto", "plan"),
            ("研究追踪", "auto", "track"),
            # P2.1：关键词全未命中不再静默落到 research/ledger，交 L02 内核澄清
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
        for i in range(1, 8):
            d = os.path.join(_HERE, "references", f"s0{i}")
            self.assertTrue(os.path.isdir(d), d)

    def test_thresholds(self):
        from skills import _common as c
        th = c.load_thresholds()
        for sec in ["research", "industry", "competitor", "business",
                    "sizing", "scenario", "auto", "review"]:
            self.assertIn(sec, th, sec)
        self.assertIn("claim_kinds", th["research"])
        self.assertIn("min_sources_per_claim", th["research"])
        self.assertIn("hhi_thresholds", th["industry"])
        self.assertIn("matrix_value_types", th["competitor"])
        self.assertIn("battlecard_sections", th["competitor"])
        self.assertIn("monetization_types", th["business"])
        self.assertIn("ltv_cac_healthy", th["business"])
        self.assertIn("variance_warning_pct", th["sizing"])
        self.assertIn("pestel_categories", th["scenario"])
        self.assertIn("risk_thresholds", th["scenario"])
        self.assertIn("method_whitelist", th["auto"])
        self.assertIn("hedge_words", th["review"])
        self.assertIn("decision_words", th["review"])
        self.assertIn("scope_violation_words", th["review"])
        self.assertIn("evidence_keys", th["review"])


# --------------------------------------------------------------------------- #
# T02 全动作 CLI 冒烟
# --------------------------------------------------------------------------- #
class T02(unittest.TestCase):
    def test_all_actions_ok(self):
        for s, a, f in ACTIONS:
            res, code = run_cli(s, a, os.path.join(EX, f))
            self.assertIsNotNone(res, f"{s}/{a} 无 __AGENT_RESULT__")
            self.assertTrue(res["ok"], f"{s}/{a} 应 ok=true")
            self.assertEqual(code, 0, f"{s}/{a} 应 exit 0")
            self.assertEqual(res["verdict"], "PASS")

    def test_missing_input(self):
        for s, a, _ in ACTIONS[:3]:
            res, code = run_cli(s, a, os.path.join(EX, "not_exist.json"))
            self.assertFalse(res["ok"])
            self.assertEqual(code, 1)


# --------------------------------------------------------------------------- #
# T03 research
# --------------------------------------------------------------------------- #
class T03(unittest.TestCase):
    def test_ledger_clean(self):
        from skills import s01_research
        data = json.load(open(os.path.join(EX, "research_ledger.json"), encoding="utf-8"))
        out = s01_research.ledger(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["source_count"], 2)
        self.assertEqual(out["claim_count"], 3)
        self.assertEqual(out["orphan_claims"], [])
        self.assertEqual(out["coverage_rate"], 1.0)
        self.assertEqual(out["verdict"], "PASS")

    def test_ledger_dirty(self):
        from skills import s01_research
        data = json.load(open(os.path.join(EX, "research_ledger_dirty.json"), encoding="utf-8"))
        out = s01_research.ledger(data)
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "FAIL")
        self.assertTrue(out["orphan_claims"])

    def test_report_clean(self):
        from skills import s01_research
        data = json.load(open(os.path.join(EX, "research_report.json"), encoding="utf-8"))
        out = s01_research.report(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["sections_checked"], 2)
        self.assertEqual(out["citation_coverage"], 1.0)
        self.assertEqual(out["orphan_claims"], [])

    def test_report_dirty(self):
        from skills import s01_research
        data = json.load(open(os.path.join(EX, "research_report_dirty.json"), encoding="utf-8"))
        out = s01_research.report(data)
        self.assertFalse(out["ok"])
        self.assertTrue(out["orphan_claims"])


# --------------------------------------------------------------------------- #
# T04 industry
# --------------------------------------------------------------------------- #
class T04(unittest.TestCase):
    def test_landscape_clean(self):
        from skills import s02_industry
        data = json.load(open(os.path.join(EX, "industry_landscape.json"), encoding="utf-8"))
        out = s02_industry.landscape(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["player_count"], 4)
        self.assertEqual(out["segment_count"], 3)
        self.assertEqual(out["value_chain_stages"], 3)
        self.assertEqual(len(out["profit_structure"]), 3)

    def test_landscape_dirty(self):
        from skills import s02_industry
        data = json.load(open(os.path.join(EX, "industry_landscape_dirty.json"), encoding="utf-8"))
        out = s02_industry.landscape(data)
        self.assertFalse(out["ok"])

    def test_concentration_clean(self):
        from skills import s02_industry
        data = json.load(open(os.path.join(EX, "industry_concentration.json"), encoding="utf-8"))
        out = s02_industry.concentration(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["hhi"], 2778)
        self.assertEqual(out["cr4"], 92)
        self.assertEqual(out["cr8"], 100)
        self.assertEqual(out["market_structure"], "oligopoly")
        self.assertEqual(out["total_share"], 100)

    def test_concentration_dirty(self):
        from skills import s02_industry
        data = json.load(open(os.path.join(EX, "industry_concentration_dirty.json"), encoding="utf-8"))
        out = s02_industry.concentration(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T05 competitor
# --------------------------------------------------------------------------- #
class T05(unittest.TestCase):
    def test_matrix_clean(self):
        from skills import s03_competitor
        data = json.load(open(os.path.join(EX, "competitor_matrix.json"), encoding="utf-8"))
        out = s03_competitor.matrix(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["competitor_count"], 2)
        self.assertEqual(out["feature_count"], 4)
        self.assertEqual(out["gaps"], [])
        self.assertEqual(out["our_coverage"], 1.0)

    def test_matrix_dirty(self):
        from skills import s03_competitor
        data = json.load(open(os.path.join(EX, "competitor_matrix_dirty.json"), encoding="utf-8"))
        out = s03_competitor.matrix(data)
        self.assertFalse(out["ok"])

    def test_battlecard_clean(self):
        from skills import s03_competitor
        data = json.load(open(os.path.join(EX, "competitor_battlecard.json"), encoding="utf-8"))
        out = s03_competitor.battlecard(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["threat_level"], "high")
        self.assertEqual(out["positioning_overlap"], 0.0)
        self.assertEqual(len(out["battlecard_sections"]), 5)

    def test_battlecard_dirty(self):
        from skills import s03_competitor
        data = json.load(open(os.path.join(EX, "competitor_battlecard_dirty.json"), encoding="utf-8"))
        out = s03_competitor.battlecard(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T06 business
# --------------------------------------------------------------------------- #
class T06(unittest.TestCase):
    def test_canvas_clean(self):
        from skills import s04_business
        data = json.load(open(os.path.join(EX, "business_canvas.json"), encoding="utf-8"))
        out = s04_business.canvas(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["blocks_complete"], 9)
        self.assertEqual(out["fit_gaps"], [])

    def test_canvas_dirty(self):
        from skills import s04_business
        data = json.load(open(os.path.join(EX, "business_canvas_dirty.json"), encoding="utf-8"))
        out = s04_business.canvas(data)
        self.assertFalse(out["ok"])
        self.assertTrue(out["fit_gaps"])

    def test_monetize_clean(self):
        from skills import s04_business
        data = json.load(open(os.path.join(EX, "business_monetize.json"), encoding="utf-8"))
        out = s04_business.monetize(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["gross_margin"], 0.75)
        self.assertEqual(out["ltv_cac_ratio"], 6.0)
        self.assertEqual(round(out["break_even"], 4), 0.8889)

    def test_monetize_dirty(self):
        from skills import s04_business
        data = json.load(open(os.path.join(EX, "business_monetize_dirty.json"), encoding="utf-8"))
        out = s04_business.monetize(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T07 sizing
# --------------------------------------------------------------------------- #
class T07(unittest.TestCase):
    def test_size_clean(self):
        from skills import s05_sizing
        data = json.load(open(os.path.join(EX, "sizing_size.json"), encoding="utf-8"))
        out = s05_sizing.size(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["tam"], 120.0)
        self.assertEqual(out["tam_top"], 120.0)
        self.assertEqual(out["tam_bottom"], 120.0)
        self.assertEqual(out["variance"], 0.0)
        base = [r for r in out["by_scenario"] if r["scenario"] == "base"][0]
        self.assertEqual(base["sam"], 48.0)
        self.assertEqual(base["som"], 4.8)

    def test_size_dirty_variance(self):
        from skills import s05_sizing
        data = json.load(open(os.path.join(EX, "sizing_size_dirty.json"), encoding="utf-8"))
        out = s05_sizing.size(data)
        self.assertFalse(out["ok"])
        self.assertGreaterEqual(out["variance"], 0.5)

    def test_sensitivity_clean(self):
        from skills import s05_sizing
        data = json.load(open(os.path.join(EX, "sizing_sensitivity.json"), encoding="utf-8"))
        out = s05_sizing.sensitivity(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["key_drivers"][0], "客户数")
        self.assertEqual(len(out["sensitivity_matrix"]), 3)

    def test_sensitivity_dirty(self):
        from skills import s05_sizing
        data = json.load(open(os.path.join(EX, "sizing_sensitivity_dirty.json"), encoding="utf-8"))
        out = s05_sizing.sensitivity(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T08 scenario
# --------------------------------------------------------------------------- #
class T08(unittest.TestCase):
    def test_pestel_clean(self):
        from skills import s06_scenario
        data = json.load(open(os.path.join(EX, "scenario_pestel.json"), encoding="utf-8"))
        out = s06_scenario.pestel(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["categories_checked"], 6)
        self.assertEqual(out["total_factors"], 6)
        self.assertEqual(out["evidence_coverage"], 1.0)
        self.assertEqual(out["impact_summary"]["high"], 3)

    def test_pestel_dirty(self):
        from skills import s06_scenario
        data = json.load(open(os.path.join(EX, "scenario_pestel_dirty.json"), encoding="utf-8"))
        out = s06_scenario.pestel(data)
        self.assertFalse(out["ok"])
        self.assertLess(out["categories_checked"], 6)
        self.assertLess(out["evidence_coverage"], 1.0)

    def test_premortem_clean(self):
        from skills import s06_scenario
        data = json.load(open(os.path.join(EX, "scenario_premortem.json"), encoding="utf-8"))
        out = s06_scenario.premortem(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["scenario_count"], 3)
        self.assertEqual(out["highest_risk"]["scenario"], "巨头碾压")
        self.assertEqual(out["highest_risk"]["risk_score"], 9)
        self.assertEqual(out["highest_risk"]["risk_tier"], "critical")

    def test_premortem_dirty(self):
        from skills import s06_scenario
        data = json.load(open(os.path.join(EX, "scenario_premortem_dirty.json"), encoding="utf-8"))
        out = s06_scenario.premortem(data)
        self.assertFalse(out["ok"])


# --------------------------------------------------------------------------- #
# T09 auto
# --------------------------------------------------------------------------- #
class T09(unittest.TestCase):
    def test_plan_clean(self):
        from skills import s07_auto
        data = json.load(open(os.path.join(EX, "auto_plan.json"), encoding="utf-8"))
        out = s07_auto.plan(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["question_count"], 3)
        self.assertEqual(len(out["coverage_matrix"]), 3)

    def test_plan_dirty(self):
        from skills import s07_auto
        data = json.load(open(os.path.join(EX, "auto_plan_dirty.json"), encoding="utf-8"))
        out = s07_auto.plan(data)
        self.assertFalse(out["ok"])

    def test_track_clean(self):
        from skills import s07_auto
        data = json.load(open(os.path.join(EX, "auto_track.json"), encoding="utf-8"))
        out = s07_auto.track(data)
        self.assertTrue(out["ok"])
        self.assertEqual(out["run_count"], 4)
        self.assertEqual(out["completed_runs"], 3)
        self.assertEqual(out["completion_rate"], 0.75)
        self.assertEqual(out["coverage_gaps"], [])

    def test_track_dirty(self):
        from skills import s07_auto
        data = json.load(open(os.path.join(EX, "auto_track_dirty.json"), encoding="utf-8"))
        out = s07_auto.track(data)
        self.assertFalse(out["ok"])
        self.assertTrue(out["coverage_gaps"])


# --------------------------------------------------------------------------- #
# T10 对抗评审
# --------------------------------------------------------------------------- #
class T10(unittest.TestCase):
    def _packet(self, name):
        return json.load(open(os.path.join(EX, name), encoding="utf-8"))

    def test_review_clean(self):
        import review
        out = review.review_packet(self._packet("review_clean.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "PASS")

    def test_unsourced_gate(self):
        import review
        out = review.review_packet(self._packet("review_unsourced.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "react")
        self.assertEqual(out["failure_category"], "review:unsourced")

    def test_evidence_gate(self):
        import review
        out = review.review_packet(self._packet("review_no_evidence.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "react")
        self.assertEqual(out["failure_category"], "review:evidence")

    def test_decision_gate(self):
        import review
        out = review.review_packet(self._packet("review_decision.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "writer")
        self.assertEqual(out["failure_category"], "review:decision")

    def test_scope_boundary(self):
        import review
        out = review.review_packet(self._packet("review_scope.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "writer")
        self.assertEqual(out["failure_category"], "review:scope")

    def test_hedge_words(self):
        import review
        out = review.review_packet(self._packet("review_hedge.json"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["route"], "writer")
        self.assertEqual(out["failure_category"], "review:hedge")

    def test_msg_not_scanned(self):
        import review
        packet = {"skill": "research", "action": "ledger",
                  "result": {"ok": True, "verdict": "PASS",
                             "claims": [{"id": "C1", "source_ids": ["S1"]}],
                             "orphan_claims": [], "coverage_gaps": [],
                             "evidence_coverage": 1.0,
                             "summary": "台账核验完成",
                             "checks": [{"ok": False, "msg": "claim 缺少来源建议补充，可能被降级",
                                         "dim": "d", "sev": "HIGH"}],
                             "next": "x"}}
        out = review.review_packet(packet)
        self.assertTrue(out["ok"], "msg 中的禁词不应触发评审失败")


# --------------------------------------------------------------------------- #
# T11 契约登记表
# --------------------------------------------------------------------------- #
class T11(unittest.TestCase):
    def test_registry_complete(self):
        import contracts
        self.assertEqual(contracts.skill_names(),
                         ["research", "industry", "competitor", "business",
                          "sizing", "scenario", "auto"])
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
            ("research", "ledger", {}),
            ("sizing", "size", {"top_down": {}}),
            ("competitor", "battlecard", {"competitor": "厂商A"}),
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
        v = contracts.validate_output("sizing", "size", {"ok": True, "checks": []})
        self.assertFalse(v["ok"])
        v = contracts.validate_output("unknown", "x", {})
        self.assertFalse(v["ok"])


# --------------------------------------------------------------------------- #
# T12 验证器
# --------------------------------------------------------------------------- #
class T12(unittest.TestCase):
    def test_materials(self):
        import harness
        good = harness.validate_materials(os.path.join(EX, "materials_good.json"))
        self.assertTrue(good["ok"])
        self.assertEqual(good["grade"], "PASS")
        bad = harness.validate_materials(os.path.join(EX, "materials_bad.json"))
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["grade"], "BLOCKED")
        self.assertTrue(bad["missing_required"])

    def test_verdict(self):
        import harness
        good = harness.validate_verdict(os.path.join(EX, "verdict_good.json"))
        self.assertTrue(good["ok"])
        bad = harness.validate_verdict(os.path.join(EX, "verdict_bad.json"))
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
# T13 案例库
# --------------------------------------------------------------------------- #
class T13(unittest.TestCase):
    def test_list_and_validate(self):
        import cases
        rows = cases.list_cases()
        ids = {r["case_id"] for r in rows}
        self.assertEqual(ids, {"competitor-deep-dive", "market-entry", "market-sizing"})
        for r in rows:
            v = cases.validate_case(r["case_id"])
            self.assertTrue(v["ok"], f"{r['case_id']}: {v['errors']}")

    def test_market_entry_steps(self):
        import cases
        from skills import SKILL_BY_NAME
        import argparse
        case = cases.load_case("market-entry")
        self.assertEqual(len(case["steps"]), 4)
        for step in case["steps"]:
            args = argparse.Namespace(action=step["action"],
                                      input=os.path.normpath(os.path.join(
                                          case["case_dir"], step["input"])))
            out = SKILL_BY_NAME[step["skill"]].run(args)
            for k, expected in step["expect"].items():
                self.assertEqual(out.get(k), expected,
                                 f"{step['skill']}/{step['action']} expect[{k}]")

    def test_competitor_case_steps(self):
        import cases
        from skills import SKILL_BY_NAME
        import argparse
        case = cases.load_case("competitor-deep-dive")
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
# T14 CLI 协议
# --------------------------------------------------------------------------- #
class T14(unittest.TestCase):
    def test_dirty_fixtures_exit_1(self):
        for s, a, f in DIRTY:
            res, code = run_cli(s, a, os.path.join(EX, f))
            self.assertIsNotNone(res, f"{s}/{a} 无输出")
            self.assertFalse(res["ok"], f"{s}/{a} 脏数据应 ok=false")
            self.assertEqual(code, 1, f"{s}/{a} 脏数据应 exit 1")

    def test_manifest_cli(self):
        proc = subprocess.run([sys.executable, "agent.py", "manifest"], cwd=_HERE,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        self.assertEqual(proc.returncode, 0)
        mf = None
        for line in (proc.stdout or "").splitlines():
            if line.startswith("__AGENT_RESULT__ "):
                mf = json.loads(line[17:])
        self.assertIsNotNone(mf)
        self.assertEqual(mf["role"], "r05")

    def test_demo_cli(self):
        proc = subprocess.run([sys.executable, "agent.py", "demo"], cwd=_HERE,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
        self.assertIn("[demo]", proc.stdout)
        self.assertEqual(proc.returncode, 0)

    def test_contract_cli(self):
        rows, code = run_cli_json(["contract", "list"])
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 14)
        v, code = run_cli_json(["contract", "validate", "--skill", "sizing",
                                "--action", "size",
                                "--output", os.path.join(EX, "sizing_size.json")])
        self.assertEqual(code, 1, "原始输入 JSON 不是合法 result，应 exit 1")

    def test_review_cli(self):
        v, code = run_cli_json(["review", "--packet",
                                os.path.join(EX, "review_unsourced.json")])
        self.assertEqual(code, 1)
        self.assertEqual(v["route"], "react")
        v, code = run_cli_json(["review", "--packet",
                                os.path.join(EX, "review_clean.json")])
        self.assertEqual(code, 0)

    def test_case_cli(self):
        rows, code = run_cli_json(["case"])
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 3)
        v, code = run_cli_json(["case", "market-entry"])
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
# T15 verify_loop 闭环矩阵
# --------------------------------------------------------------------------- #
class T15(unittest.TestCase):
    def test_verify_loop_all_green(self):
        import verify_loop
        out = verify_loop.run_all()
        self.assertTrue(out["ok"], f"闭环矩阵有红：\n" +
                        json.dumps([r for r in out["matrix"] if not r.get("ok")],
                                   ensure_ascii=False, indent=2))
        self.assertEqual(out["total"], 28)
        self.assertEqual(out["failed"], 0)
        self.assertEqual(out["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
