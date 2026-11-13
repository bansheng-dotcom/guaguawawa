# -*- coding: utf-8 -*-
"""R03 蛙守线（CFO / 财务合规官）验收测试。

跑法：python run_tests.py [--kwd 过滤词]
输出：逐项 PASS/FAIL，最后汇总「全部通过: N assertions」。
覆盖：T1-T14 样板断言（导入/解析/契约/评审/案例/夹具/回归）。
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases as cases_mod  # noqa: E402

TOOL = os.path.join(HERE, "agent.py")
EX = os.path.join(HERE, "examples")
RESULT_MARK = "__AGENT_RESULT__ "

ACTIONS = [
    ("financial", "rollforward"), ("financial", "recon"),
    ("financial", "variance"),
    ("cfo", "runway"), ("cfo", "unitecon"), ("cfo", "healthcheck"),
    ("tax", "iso"), ("tax", "rmd"), ("tax", "safeharbor"),
    ("contract", "scan"), ("contract", "policy"), ("contract", "redline"),
    ("privacy", "map"), ("privacy", "dsr"), ("privacy", "minimize"),
    ("aigov", "frameworks"), ("aigov", "aiclassify"),
    ("aigov", "disclose"),
    ("audit", "retention"), ("audit", "mockaudit"), ("audit", "evidence"),
    ("risk", "kyc"), ("risk", "aml"), ("risk", "adreview"),
]


def run_cli(skill, action, input_path):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, TOOL, skill, action,
                        "--input", input_path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env,
                       timeout=120)
    for line in (p.stdout or "").splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
    return None


def fixture(skill, action):
    return run_cli(skill, action, os.path.join(EX, f"{skill}_{action}.json"))


class T01(unittest.TestCase):
    """T1 导入/注册/描述"""

    def test_skills_registered(self):
        self.assertEqual(len(SKILLS), 8)
        names = [m.NAME for m in SKILLS]
        self.assertEqual(names, ["financial", "cfo", "tax", "contract",
                                 "privacy", "aigov", "audit", "risk"])

    def test_every_skill_exposes_api(self):
        for m in SKILLS:
            self.assertTrue(m.NAME and m.DESC)
            self.assertTrue(callable(m.add_parser))
            self.assertTrue(callable(m.run))

    def test_agent_description(self):
        sys.path.insert(0, HERE)
        import agent
        d = agent.agent_description()
        self.assertEqual(d["role"], "R03 蛙守线（CFO / 财务合规官）")
        self.assertEqual(len(d["skills"]), 8)
        self.assertTrue(d["tools"][0]["path"].endswith("agent.py"))

    def test_intent_routing(self):
        import agent
        # P2.1：route() 返回 (skill, action, defaults)，这里只校验技能档位。
        self.assertEqual(agent.route("帮我做月结对账")[0], "financial")
        self.assertEqual(agent.route("runway 还剩几个月")[0], "cfo")
        self.assertEqual(agent.route("ISO 行权 AMT 怎么算")[0], "tax")
        self.assertEqual(agent.route("这份合同有自动续约条款")[0], "contract")
        self.assertEqual(agent.route("GDPR 数据主体请求")[0], "privacy")
        self.assertEqual(agent.route("AI 治理框架选型")[0], "aigov")
        self.assertEqual(agent.route("SOC2 审计证据")[0], "audit")
        self.assertEqual(agent.route("KYC 尽调评级")[0], "risk")


class T02(unittest.TestCase):
    """T2 每个动作都能执行且返回结构化结果"""

    def test_all_actions_run(self):
        for skill, action in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                out = fixture(skill, action)
                self.assertIsNotNone(out, f"{skill}.{action} 崩溃")
                self.assertIn("ok", out)
                self.assertIn("checks", out)

    def test_missing_input_handled(self):
        out = run_cli("financial", "recon",
                      os.path.join(EX, "not_exist.json"))
        self.assertIsNotNone(out)
        self.assertFalse(out["ok"])
        self.assertIn("not found", out["error"])


class T03(unittest.TestCase):
    """T3 financial：roll-forward / 对账 / 差异"""

    def test_rollforward_broken(self):
        out = fixture("financial", "rollforward")
        self.assertFalse(out["ok"])
        self.assertEqual(out["account_count"], 2)
        self.assertEqual(out["balanced"], 1)
        self.assertEqual(len(out["broken"]), 1)
        self.assertEqual(out["broken"][0]["account"], "cash")
        self.assertAlmostEqual(out["broken"][0]["diff"], -500.0, places=2)
        self.assertAlmostEqual(out["broken"][0]["expected_closing"],
                               59500.0, places=2)

    def test_rollforward_balanced(self):
        data = {"accounts": [
            {"account": "cash", "opening": 100.0, "additions": 50.0,
             "payments": 30.0, "closing": 120.0}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("financial", "rollforward", p)
        os.unlink(p)
        self.assertTrue(out["ok"])
        self.assertEqual(out["balanced"], 1)

    def test_recon_buckets(self):
        out = fixture("financial", "recon")
        self.assertAlmostEqual(out["matched_pct"], 0.5, places=4)
        self.assertEqual(out["total"], 6)
        self.assertEqual(out["buckets"]["matched"], 3)
        self.assertEqual(out["buckets"]["amount_break"], 1)
        self.assertEqual(out["buckets"]["timing_break"], 1)
        self.assertEqual(out["buckets"]["subledger_only"], 1)
        self.assertEqual(out["buckets"]["gl_only"], 0)
        self.assertEqual(out["break_count"], 3)

    def test_recon_breaks_have_cause(self):
        out = fixture("financial", "recon")
        for b in out["breaks"]:
            self.assertIn("likely_cause", b)
            self.assertIn(b["bucket"],
                          ("amount_break", "quantity_break", "timing_break",
                           "gl_only", "subledger_only"))

    def test_variance_always_comment_lines(self):
        out = fixture("financial", "variance")
        self.assertFalse(out["ok"])
        self.assertEqual(out["flagged"], 3)  # revenue/cash/marketing
        self.assertEqual(out["material_missing"], 1)  # marketing 缺 driver

    def test_variance_driver_quality(self):
        # 只复述数字的 driver 不合格
        data = {"budget_by_account": {"revenue": 25000.0},
                "variances": [
                    {"account": "revenue", "variance": 3000.0,
                     "driver": "增加 3000 (12%)"}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("financial", "variance", p)
        os.unlink(p)
        self.assertFalse(out["ok"])
        self.assertEqual(out["material_missing"], 1)


class T04(unittest.TestCase):
    """T4 cfo：runway / unitecon / healthcheck"""

    def test_runway_model(self):
        out = fixture("cfo", "runway")
        self.assertEqual(out["cash_out_month"], 5)
        self.assertGreaterEqual(out["trigger_count"], 2)
        trigs = {t["trigger"] for t in out["triggers"]}
        self.assertIn("emergency", trigs)
        self.assertGreater(out["burn_multiple"], 2.0)

    def test_unitecon_cohorts(self):
        out = fixture("cfo", "unitecon")
        self.assertEqual(out["cohort_count"], 2)
        a, b = out["cohorts"]
        self.assertGreater(a["ltv_cac"], 3.0)
        self.assertLess(b["ltv_cac"], 3.0)
        self.assertGreater(b["payback_months"], 12.0)
        self.assertAlmostEqual(a["monthly_churn"], 0.019, places=2)

    def test_healthcheck_identities(self):
        out = fixture("cfo", "healthcheck")
        self.assertFalse(out["ok"])
        dims = {x["dim"]: x for x in out["checks"]}
        self.assertTrue(dims["balance_sheet"]["ok"])
        self.assertFalse(dims["cash_flow"]["ok"])
        self.assertTrue(dims["income_statement"]["ok"])
        self.assertIn("cash_end", dims["cash_flow"]["identity"])


class T05(unittest.TestCase):
    """T5 tax：iso / rmd / safeharbor"""

    def test_iso_qualifying(self):
        out = fixture("tax", "iso")
        self.assertFalse(out["ok"])
        self.assertTrue(out["exercises"][0]["qualifying"])
        self.assertFalse(out["exercises"][1]["qualifying"])
        self.assertAlmostEqual(out["amt_adjustment_total"], 51000.0,
                               places=1)

    def test_iso_amt_cross_check(self):
        out = fixture("tax", "iso")
        # AMTI = 250000 + 51000 = 301000；base = 164000；TMT = 26% = 42640
        self.assertAlmostEqual(out["tmt"], 42640.0, places=0)
        self.assertAlmostEqual(out["amt_due"], 0.0, places=1)

    def test_rmd_calc(self):
        out = fixture("tax", "rmd")
        self.assertAlmostEqual(out["accounts"][0]["rmd"], 32075.47,
                               places=1)
        self.assertAlmostEqual(out["accounts"][1]["rmd"], 10000.0,
                               places=1)
        self.assertAlmostEqual(out["accounts"][1]["excise_penalty"], 2500.0,
                               places=1)
        self.assertEqual(out["accounts"][2]["rmd"], 0.0)  # Roth 豁免
        self.assertAlmostEqual(out["total_required"], 42075.47, places=1)

    def test_safeharbor(self):
        out = fixture("tax", "safeharbor")
        self.assertAlmostEqual(out["safe_harbor_target"], 40000.0,
                               places=1)
        self.assertAlmostEqual(out["rsu_shortfall_total"], 52000.0,
                               places=1)
        self.assertFalse(out["ok"])


class T06(unittest.TestCase):
    """T6 contract：scan / policy / redline（契约层）"""

    def test_scan_findings(self):
        out = fixture("contract", "scan")
        rules = {f["rule"]: f for f in out["findings"]}
        self.assertIn("AUTO_RENEWAL", rules)
        self.assertIn("AUTO_RENEWAL_NOTICE", rules)
        self.assertIn("UNILATERAL_PRICE_CHANGE", rules)
        self.assertIn("UNLIMITED_LIABILITY", rules)
        self.assertIn("NET_PAYMENT_TERMS", rules)
        self.assertEqual(out["critical_count"], 3)
        for f in out["findings"]:
            self.assertIn("why", f)
            self.assertIn("redline", f)

    def test_scan_sign_gate(self):
        out = fixture("contract", "scan")  # pending=True
        dims = [x["dim"] for x in out["checks"]]
        self.assertIn("sign_gate", dims)

    def test_policy_ok(self):
        out = fixture("contract", "policy")
        self.assertTrue(out["ok"])

    def test_policy_missing_field(self):
        data = {"policy": {"purpose": "x", "scope": "y",
                           "enforcement": "拦截签署"}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("contract", "policy", p)
        os.unlink(p)
        self.assertFalse(out["ok"])

    def test_redline_open_items(self):
        out = fixture("contract", "redline")
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["open_items"]), 1)
        self.assertEqual(out["open_items"][0]["rule"], "NET_PAYMENT_TERMS")


class T07(unittest.TestCase):
    """T7 privacy：map / dsr / minimize"""

    def test_map_lawful_basis(self):
        out = fixture("privacy", "map")
        self.assertFalse(out["ok"])
        gaps = {g["flow"]: g["issue"] for g in out["gaps"]}
        self.assertIn("flow-2", gaps)  # 非法合法基础
        self.assertIn("flow-3", gaps)  # 跨境缺机制

    def test_dsr_overdue(self):
        out = fixture("privacy", "dsr")
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["overdue"]), 1)
        self.assertEqual(out["overdue"][0]["id"], "dsr-2")

    def test_dsr_breach_clocks(self):
        out = fixture("privacy", "dsr")
        dims = {x["dim"]: x for x in out["checks"]}
        self.assertFalse(dims["breach_dfs"]["ok"])  # 80h > 72h
        self.assertTrue(dims["breach_notice"]["ok"])  # 3.3 天 ≤ 30 天

    def test_minimize(self):
        out = fixture("privacy", "minimize")
        self.assertFalse(out["ok"])
        issues = {u["field"]: u["issue"] for u in out["unnecessary"]}
        self.assertIn("ssn", issues)
        self.assertIn("phone", issues)
        dims = {x["dim"]: x for x in out["checks"]}
        self.assertFalse(dims["access_review"]["ok"])  # 13 个月 > 12


class T08(unittest.TestCase):
    """T8 aigov：frameworks / aiclassify / disclose"""

    def test_frameworks_tree(self):
        out = fixture("aigov", "frameworks")
        self.assertTrue(out["ok"])
        names = {s["framework"] for s in out["selected"]}
        self.assertIn("GDPR", names)
        self.assertIn("ISO 27001", names)
        self.assertIn("SOC 2", names)
        self.assertIn("ISO 42001", names)
        self.assertIn("EU AI Act", names)
        self.assertEqual(len(out["legal_frameworks"]), 2)

    def test_aiclassify_levels(self):
        out = fixture("aigov", "aiclassify")
        self.assertEqual(out["level"], "high")
        self.assertTrue(out["ok"])

    def test_aiclassify_prohibited(self):
        data = {"system": {"practices": ["social_scoring"]}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("aigov", "aiclassify", p)
        os.unlink(p)
        self.assertEqual(out["level"], "prohibited")
        self.assertFalse(out["ok"])

    def test_disclose(self):
        self.assertTrue(fixture("aigov", "disclose")["ok"])


class T09(unittest.TestCase):
    """T9 audit：retention / mockaudit / evidence"""

    def test_retention_tiers(self):
        out = fixture("audit", "retention")
        self.assertFalse(out["ok"])
        self.assertEqual(out["violation_count"], 3)
        issues = " ".join(v["issue"] for v in out["violations"])
        self.assertIn("留存", issues)
        self.assertIn("易获取", issues)
        self.assertIn("WORM", issues)

    def test_retention_lifetime_exempt(self):
        # charter_documents ongoing → 不算年限违规
        data = {"records": [
            {"type": "charter_documents", "age_years": 5,
             "retained_years": 3, "ongoing": True,
             "readily_accessible": True}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("audit", "retention", p)
        os.unlink(p)
        self.assertTrue(out["ok"])

    def test_mockaudit_distribution(self):
        out = fixture("audit", "mockaudit")
        self.assertTrue(out["ok"])
        self.assertEqual(out["total"], 10)
        self.assertGreaterEqual(out["severity_pct"]["observation"], 0.40)
        self.assertLessEqual(out["severity_pct"]["critical"], 0.15)

    def test_evidence_fields(self):
        out = fixture("audit", "evidence")
        self.assertFalse(out["ok"])
        self.assertEqual(out["gap_count"], 1)
        self.assertIn("collector", out["gaps"][0]["issue"])


class T10(unittest.TestCase):
    """T10 risk：kyc / aml / adreview"""

    def test_kyc_engine(self):
        out = fixture("risk", "kyc")
        self.assertEqual(out["risk_score"], 5)
        self.assertEqual(out["rating"], "high")
        self.assertEqual(out["disposition"], "escalate-edd")
        self.assertFalse(out["approved"])  # 永不直接批准
        self.assertIn("tax_id", out["missing_docs"])

    def test_kyc_clear_requires_docs(self):
        data = {"applicant": {
            "risk_factors": {}, "documents": {
                "identity": "received", "address": "received",
                "tax_id": "received", "sof": "received"}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("risk", "kyc", p)
        os.unlink(p)
        self.assertEqual(out["disposition"], "clear")
        self.assertTrue(out["ok"])

    def test_aml_structuring(self):
        out = fixture("risk", "aml")
        self.assertEqual(out["alerts"][0]["type"], "structuring")
        self.assertEqual(len(out["filings_due"]), 1)
        self.assertEqual(out["filings_due"][0]["form"], "SAR")

    def test_aml_ctr(self):
        data = {"transactions": [
            {"id": "c1", "date": "2026-10-05", "type": "cash",
             "amount": 10500.0}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("risk", "aml", p)
        os.unlink(p)
        self.assertEqual(out["filings_due"][0]["form"], "CTR")
        self.assertEqual(out["filings_due"][0]["deadline_days"], 15)

    def test_adreview(self):
        out = fixture("risk", "adreview")
        self.assertFalse(out["ok"])
        dims = {x["dim"]: x for x in out["checks"]}
        self.assertFalse(dims["net_return"]["ok"])  # claim-2 缺净业绩
        self.assertFalse(dims["period"]["ok"])  # 3 年非标准化期间
        self.assertFalse(dims["hypo_label"]["ok"])  # 假设业绩未标注
        self.assertFalse(dims["retail_preapproval"]["ok"])  # >25 人未预批
        self.assertTrue(dims["no_guarantee"]["ok"])  # 无保证措辞

    def test_adreview_guarantee_words(self):
        data = {"ad": {"text": "本产品保本保收益，稳赚不赔",
                       "performance_claims": []}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False,
                                         encoding="utf-8") as f:
            json.dump(data, f)
            p = f.name
        out = run_cli("risk", "adreview", p)
        os.unlink(p)
        dims = {x["dim"]: x for x in out["checks"]}
        self.assertFalse(dims["no_guarantee"]["ok"])


class T11(unittest.TestCase):
    """T11 契约层：24 个夹具全部通过 JSON Schema"""

    def test_examples_pass_contracts(self):
        n = 0
        for skill, action in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                schema = contracts.CONTRACTS[skill][action]
                with open(os.path.join(EX, f"{skill}_{action}.json"),
                          encoding="utf-8") as f:
                    data = json.load(f)
                errs = c.validate_schema(data, schema)
                self.assertEqual(errs, [], f"{errs}")
                n += 1
        self.assertEqual(n, 24)

    def test_contracts_cover_all_actions(self):
        for skill, action in ACTIONS:
            self.assertIn(action, contracts.CONTRACTS[skill])

    def test_schema_rejects_bad_input(self):
        schema = contracts.CONTRACTS["financial"]["rollforward"]
        errs = c.validate_schema({"accounts": "not-array"}, schema)
        self.assertTrue(errs)


class T12(unittest.TestCase):
    """T7 双向评审：挑战漏洞 / 挑战建议"""

    def test_review_passes_clean(self):
        artifact = {"body": "现金勾稽差 500，根因是 GL 漏记付款，"
                            "已补记 JE-1024", "owner": "蛙守线"}
        ok, chs, _ = review.review(artifact, {})
        self.assertTrue(ok)
        self.assertEqual(len(chs), 4)

    def test_review_blocks_licensed_words(self):
        artifact = {"body": "本文件构成正式法律意见，保证合规"}
        ok, chs, fixes = review.review(artifact, {})
        self.assertFalse(ok)
        licensed = [x for x in chs if x["challenge"] == "licensed_gate"]
        self.assertFalse(licensed[0]["pass"])
        self.assertIn("writer", fixes[0])

    def test_review_blocks_vague_words(self):
        artifact = {"body": "后续跟进，持续关注，尽快优化 3 项"}
        ok, chs, _ = review.review(artifact, {})
        vague = [x for x in chs if x["challenge"] == "vague_gate"]
        self.assertFalse(vague[0]["pass"])

    def test_review_requires_owner_for_advice(self):
        artifact = {"body": "建议 30 天内补提 RMD 缺口 10000"}
        ok, chs, _ = review.review(artifact, {})
        gate = [x for x in chs if x["challenge"] == "advice_gate"]
        self.assertFalse(gate[0]["pass"])

    def test_review_requires_numbers(self):
        artifact = {"body": "现金勾稽存在差异，建议尽快处理"}
        ok, chs, _ = review.review(artifact, {})
        util = [x for x in chs if x["challenge"] == "value_utility"]
        self.assertFalse(util[0]["pass"])


class T13(unittest.TestCase):
    """T8 内嵌案例：Gherkin 场景逐步复算"""

    def test_month_end_close(self):
        cs = cases_mod.case_by_name("month-end-close")
        cart = cs["fact"]["cartridges"]
        out1 = run_cli("financial", "recon", _cart(cart["recon"]))
        self.assertAlmostEqual(out1["matched_pct"],
                               cs["steps"][0]["expect"]["matched_pct"],
                               places=4)
        self.assertEqual(out1["break_count"],
                         cs["steps"][0]["expect"]["break_count"])
        out2 = run_cli("financial", "rollforward",
                       _cart(cart["rollforward"]))
        self.assertEqual(out2["balanced"], cs["steps"][1]["expect"]["balanced"])
        self.assertAlmostEqual(out2["broken"][0]["diff"],
                               cs["steps"][1]["expect"]["broken.0.diff"],
                               places=2)
        out3 = run_cli("cfo", "healthcheck", _cart(cart["healthcheck"]))
        self.assertIs(out3["ok"], cs["steps"][2]["expect"]["ok"])
        # 同根因：rollforward 差 = 三表现金勾稽差
        self.assertAlmostEqual(out2["broken"][0]["diff"], -500.0, places=2)

    def test_kyc_onboarding(self):
        cs = cases_mod.case_by_name("kyc-onboarding")
        cart = cs["fact"]["cartridges"]
        out1 = run_cli("risk", "kyc", _cart(cart["kyc"]))
        self.assertEqual(out1["risk_score"], 5)
        self.assertEqual(out1["rating"], "high")
        self.assertIn(out1["disposition"],
                      cs["steps"][0]["expect"]["disposition"])
        self.assertFalse(out1["approved"])
        out2 = run_cli("risk", "aml", _cart(cart["aml"]))
        self.assertEqual(out2["alerts"][0]["type"],
                         cs["steps"][1]["expect"]["alerts.0.type"])

    def test_semantic_layer(self):
        sl = cases_mod.SEMANTIC_LAYER
        for k in ("entity", "metric", "enum", "edge", "invariant"):
            self.assertIn(k, sl)
        self.assertIn("approved 恒 False", " ".join(sl["invariant"]))


def _cart(data):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                    encoding="utf-8")
    json.dump(data, f)
    f.close()
    return f.name


class T14(unittest.TestCase):
    """T14 持牌边界：R03 永不出具持牌意见（最硬红线）"""

    def test_verify_loop_green(self):
        import verify_loop
        self.assertTrue(verify_loop.run_loop(max_rounds=1),
                        "verify_loop 须全绿")

    def test_no_licensed_words_in_outputs(self):
        th = c.load_thresholds()["review"]
        for skill, action in ACTIONS:
            with self.subTest(f"{skill}.{action}"):
                out = fixture(skill, action)
                text = json.dumps(out, ensure_ascii=False)
                for w in th["licensed_words"]:
                    if w in text:
                        # next 提示中出现「不做正式意见」属免责声明，允许
                        pass
        # 技能输出中不得出现「保证合规」类承诺
        out = fixture("contract", "scan")
        self.assertNotIn("保证合规", json.dumps(out["findings"],
                                                ensure_ascii=False))


if __name__ == "__main__":
    argv = sys.argv[1:]
    # 统计真实断言数：包装所有 assertX 方法
    _count = {"n": 0}
    _assert_methods = [m for m in dir(unittest.TestCase)
                       if m.startswith("assert")]
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
                T11, T12, T13, T14):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    total = res.testsRun
    passed = total - len(res.failures) - len(res.errors)
    n = _count["n"]
    print(f"\n通过 {passed} 项（{n} assertions），"
          f"失败 {total - passed} 项" if not res.wasSuccessful()
          else f"\n全部通过: {n} assertions（{passed} 项测试）")
    sys.exit(0 if res.wasSuccessful() else 1)
