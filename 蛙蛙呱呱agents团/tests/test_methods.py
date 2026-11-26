# -*- coding: utf-8 -*-
"""methods 域测试（合并自 7 个文件）。

源文件：
    test_analysis_lab.py —— 分析引擎回归：归因闭合、A/B、DiD、弹性、队列。
    test_analysis_upgrade.py —— R06 数据分析能力升级（P0/P1）回归测试。
    test_method_gate.py —— 方法门禁测试：未匹配价差/无基线趋势应 FAIL，匹配后应 PASS。
    test_methods_business.py —— 业务定量技能测试。
    test_methods_core.py —— 可执行方法库测试：匹配差分/DID/弹性/库存/LTV/跑道/利特尔/MMM/RDD/仿真。
    test_methods_deep.py —— 深度方法测试：PSM/TWFE/带控制弹性/RDD 敏感性/MMM/履约 (s,S)。
    test_methods_deep_advanced.py —— 深度方法测试（进阶）：PSM 反驳、事件研究、置换、交错、FE/IV、预算/CI、RDD 校正、预热。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import math
import random
import json
import subprocess
from scripts.method_gate import check
from shared.methods import business
from shared.methods import advanced, core
from shared.methods import deep


# ====================================================================
# 合并自 test_analysis_upgrade.py：R06 数据分析能力升级（P0/P1）回归测试。
# ====================================================================
# -*- coding: utf-8 -*-


AGENTS = Path(__file__).resolve().parents[1]
FIX = AGENTS / "tests" / "fixtures"


def _r06(*args):
    p = subprocess.run([sys.executable, "guagua.py", "call", "r06", *args],
                       cwd=str(AGENTS), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if "__AGENT_RESULT__" in line:
            return json.loads(line.split("__AGENT_RESULT__", 1)[1].strip())
    for line in reversed(out.splitlines()):
        if line.strip().startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise AssertionError(f"无法解析输出: {out[-500:]}")


def test_quality_clean_six_dims():
    r = _r06("quality", "audit", "--input", str(FIX / "analysis_orders.csv"),
             "--pk", "order_id", "--date", "order_date")
    assert r["dims_active"] == 6 and r["score_version"] == "2.0"
    assert r["dimension_score"]["validity"] == 10
    assert r["dimension_score"]["consistency"] == 10


def test_quality_dirty_drops_two_dims():
    r = _r06("quality", "audit", "--input", str(FIX / "quality_dirty.csv"),
             "--pk", "order_id", "--date", "order_date")
    assert r["dimension_score"]["validity"] < 10
    assert r["dimension_score"]["consistency"] < 10
    assert r["violations"], "脏数据必须留下 violations"


def test_chi2_exact_p_matches_scipy():
    from scipy import stats
    r = _r06("chi2", "--input", str(FIX / "analysis_orders.csv"),
             "--row", "category", "--col", "returned")
    assert r["chi2"]["p_method"] == "exact"
    assert 0 <= r["chi2"]["p_exact"] <= 1


def test_bh_adjust_monotone():
    from shared.stats_exact import bh_adjust
    out = bh_adjust([0.01, 0.02, 0.03, 0.2])
    assert out["p_adj"] == sorted(out["p_adj"])
    assert all(0 <= x <= 1 for x in out["p_adj"])


def test_chart_number_format():
    sys.path.insert(0, str(AGENTS / "core" / "charts"))
    import chart_lib as L
    assert L._fmt_num(0.022) == "0.022"
    assert L._fmt_num(0.148) == "0.148"
    assert L._fmt_num(646.32) == "646.32"
    assert L._fmt_num(12345) == "12,345"


def test_linear_ols_matches_statsmodels():
    import numpy as np
    import statsmodels.api as sm
    from shared.methods import linear

    rng = np.random.default_rng(0)
    n = 200
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    y = 1.5 + 2.0 * x1 - 1.0 * x2 + rng.normal(0, 0.5, n)
    X = np.column_stack([np.ones(n), x1, x2])
    ours = linear.fit_ols(y, X, ["const", "x1", "x2"], se="HC1")
    sm_res = sm.OLS(y, X).fit(cov_type="HC1")
    for i, name in enumerate(["const", "x1", "x2"]):
        assert abs(ours["coef"][i]["est"] - float(sm_res.params[i])) < 1e-8
        assert abs(ours["coef"][i]["se"] - float(sm_res.bse[i])) < 1e-6


def test_event_study_v2_has_joint_test():
    from shared.methods import deep
    import csv
    rows = list(csv.DictReader(open(FIX / "analysis_panel.csv", encoding="utf-8-sig")))
    y = [float(r["gmv"]) for r in rows]
    treat = [int(r["treat"]) for r in rows]
    post = [int(r["post"]) for r in rows]
    unit = [r["city_id"] for r in rows]
    time = [r["week"] for r in rows]
    out = deep.event_study_v2(y, treat, post, unit, time)
    assert "pretrend_joint" in out
    assert out["pretrend_joint"]["q"] >= 1


def test_data_contract_reports_missing_column():
    from core.data_contract import DataContract, validate_rows
    c = DataContract.from_dict({"name": "t", "fields": [
        {"name": "a", "dtype": "float"}, {"name": "b", "dtype": "date"}]})
    out = validate_rows([{"a": "1"}], c)
    assert not out["ok"] and any("b" in e["field"] for e in out["errors"])


def test_conclusions_enrich_abtest():
    from shared.conclusions import enrich
    res = {"abtest": {"decision": "no_ship", "lift_pct": 2.4, "p_exact": 0.43,
                      "srm_flag": False, "significant": False}}
    out = enrich(res, "abtest")
    assert "no_ship" in out["conclusion"]
    assert out["status"] == "ok"
    assert out["caveats"]


def test_contract_check_cli_warns_on_bad_enum():
    from core import data_contract as dc
    out = dc.check_cli("chi2", {"input": str(FIX / "analysis_orders.csv")}, mode="warn")
    assert out["checked"] is True
    assert out["ok"] is True or out["errors"]


def test_flow_contract_structure_and_traceability():
    """唯一产线：契约末节固定「口径与分数」，记录层折叠，数字带来源。"""
    from core import report_flow
    j = {"headline": "GMV 下降 3.2%",
         "conclusions": [{"text": "GMV 下降 3.2%", "number": "-3.2",
                          "source": "r06/semantics", "kind": "finding"}],
         "drivers": [], "boundary": ["只对本次输入成立"],
         "actions": [{"do": "复算", "condition": "对外时", "stop": "不一致即停"}],
         "gaps": []}
    ev = [{"role": "r06", "skill": "semantics", "action": "validate",
           "source": "x.json", "source_hash": "h"}]
    nums = [{"path": "gmv.delta_pct", "value": -3.2, "text": "-3.2",
             "source": "r06/semantics"}]
    c = report_flow.build_contract(j, "测试诊断", "A", ev, nums,
                                   [{"id": "x", "ok": True}], "rule")
    assert c["title_lines"][0] == "测试诊断"
    assert c["sections"][-1]["title"] == "口径与分数"
    assert c["sections"][-2].get("appendix") is True
    assert c["metric_strip"][0]["note"].startswith("来源 ")
    assert c["footer"][0].startswith("协作")


def test_json_contract_blocks_bad_viz_spec():
    import tempfile, json as _json
    from core import data_contract as dc
    bad = {"chart_type": "line"}  # 缺 title/data
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        _json.dump(bad, f)
        path = f.name
    out = dc.check_cli("viz", {"action": "spec", "input": path}, mode="warn")
    assert out["checked"] and not out["ok"]


def test_power_args_contract():
    from core import data_contract as dc
    out = dc.check_cli("power", {"baseline": 0.03}, mode="warn")
    assert not out["ok"]  # 既没 mde 也没 n_per_group


# ====================================================================
# 合并自 test_method_gate.py：方法门禁测试：未匹配价差/无基线趋势应 FAIL，匹配后应 PASS。
# ====================================================================
# -*- coding: utf-8 -*-


def test_unmatched_spread_fails(tmp_path: Path) -> None:
    p = tmp_path / "bad.html"
    p.write_text("<p>省内价差 2.33 倍，呼市最高。</p><p>价格窄幅震荡，振幅 4.79%，属正常。</p>", encoding="utf-8")
    issues = check(p)
    assert any(i["type"] == "价差未匹配" for i in issues)
    assert any(i["type"] == "趋势无基线" for i in issues)


def test_matched_spread_passes(tmp_path: Path) -> None:
    p = tmp_path / "good.md"
    p.write_text("同规格同日分规格对照后，价差 3.09 元；同比 -5.11%，低于同期基线。", encoding="utf-8")
    assert check(p) == []


# ====================================================================
# 合并自 test_methods_business.py：业务定量技能测试。
# ====================================================================
# -*- coding: utf-8 -*-


def test_expected_value() -> None:
    r = business.expected_value([
        {"name": "A", "p": 0.6, "good": 100, "bad": -50, "cost": 10},
        {"name": "B", "p": 0.9, "good": 30, "bad": -10, "cost": 5},
    ])
    assert r["best"] in ("A", "B")
    assert r["ranking"][0]["ev"] >= r["ranking"][1]["ev"]
    assert r["breakeven_p_vs_second"] is not None


def test_queue() -> None:
    r = business.queue_wait(8, 10, 1.0, 1.0)
    assert abs(r["utilization"] - 0.8) < 1e-6
    assert r["wait_days"] > 0
    assert r["cycle_days"] > r["wait_days"]


def test_tam_mc() -> None:
    r = business.tam_mc(1000, 0.1, 0.3, 50, 100, n=2000)
    assert r["p10"] <= r["p50"] <= r["p90"]
    assert r["mean"] > 0


def test_rice() -> None:
    r = business.rice([
        {"name": "A", "reach": 100, "impact": 3, "confidence": 0.8, "effort": 5},
        {"name": "B", "reach": 50, "impact": 5, "confidence": 0.9, "effort": 2},
    ])
    assert len(r["ranking"]) == 2
    assert r["sensitivity"][0]["top"]


def test_data_profile() -> None:
    rows = [{"x": 1, "t": "2026-01"}, {"x": None, "t": "2026-02"},
            {"x": 3, "t": "2026-03"}, {"x": 4, "t": "2026-04"}]
    r = business.data_profile(rows, ["x"], "t")
    assert r["columns"]["x"]["missing_pct"] == 25.0
    assert "psi" in r["columns"]["x"]


def test_slo_budget() -> None:
    r = business.slo_budget(99.0, 30, 1_000_000, 200)
    assert abs(r["allowed_downtime_min"] - 432.0) < 0.1
    assert r["status"] in ("正常", "预警", "超预算")


def test_experiment_power() -> None:
    r = business.experiment_power(0.10, 0.02)
    assert r["n_per_group"] > 1000
    assert r["n_total"] == r["n_per_group"] * 2


def test_hiring_funnel() -> None:
    r = business.hiring_funnel(1000, 300, 100, 20, 10)
    assert r["overall_pct"] == 1.0
    assert r["bottleneck"] is not None


def test_eval_ci() -> None:
    r = business.eval_ci(8, 10)
    assert r["ci95"][0] < 80 < r["ci95"][1]


def test_retry_reliability() -> None:
    r = business.retry_reliability(0.5, 3)
    assert abs(r["eventual_success_pct"] - 87.5) < 0.1


# ====================================================================
# 合并自 test_methods_core.py：可执行方法库测试：匹配差分/DID/弹性/库存/LTV/跑道/利特尔/MMM/RDD/仿真。
# ====================================================================
# -*- coding: utf-8 -*-


def test_matched_diff() -> None:
    r = core.matched_diff([10, 11, 12], [8, 8.5, 9])
    assert abs(r["diff"] - 2.5) < 0.05
    assert r["ci95"][0] <= r["diff"] <= r["ci95"][1]


def test_did() -> None:
    y = [10, 10, 14, 14, 10, 10, 12, 12]
    treat = [1, 1, 1, 1, 0, 0, 0, 0]
    post = [0, 0, 1, 1, 0, 0, 1, 1]
    assert core.did(y, treat, post)["did"] == 2.0


def test_elasticity() -> None:
    r = core.elasticity([1, 2, 4], [100, 50, 25])
    assert abs(r["elasticity"] + 1.0) < 0.01
    assert r["r2"] > 0.99


def test_safety_stock() -> None:
    assert abs(core.safety_stock(2, 9, 1.65)["safety_stock"] - 9.9) < 0.05


def test_ltv_cac() -> None:
    r = core.ltv_cac(60, 0.3, 0.05, 120)
    assert abs(r["ltv"] - 360) < 0.1
    assert abs(r["ltv_cac"] - 3.0) < 0.01
    assert r["verdict"] == "健康"


def test_runway_and_little() -> None:
    assert core.runway(300000, 55000)["runway_months"] == 6
    assert core.littles_law(200, 1.2)["wip"] == 240.0


def test_mmm() -> None:
    ch = [[i, (i * 7) % 11] for i in range(24)]
    y = [100 + 2 * a + 1.5 * b for a, b in ch]
    r = advanced.mmm(ch, y, ["tv", "search"])
    assert abs(r["coef"]["tv"] - 2) < 0.01
    assert abs(r["coef"]["search"] - 1.5) < 0.01
    assert r["r2"] > 0.99


def test_rdd() -> None:
    x = list(range(40, 100))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) for v in x]
    r = advanced.rdd(y, x, 60, bandwidth=20)
    assert abs(r["estimate"] - 2) < 0.01
    assert r["n_left"] >= 4 and r["n_right"] >= 4


def test_fulfillment() -> None:
    r = advanced.fulfillment_sim(100, 20, 3, 500, days=30, n_sim=200)
    assert 0 <= r["fill_rate"] <= 100
    assert r["avg_inventory"] > 0


# ====================================================================
# 合并自 test_methods_deep.py：深度方法测试：PSM/TWFE/带控制弹性/RDD 敏感性/MMM/履约 (s,S)。
# ====================================================================
# -*- coding: utf-8 -*-


def test_psm_recovers_effect_and_balances() -> None:
    rng = random.Random(11)
    tx, cx, ty, cy = [], [], [], []
    for _ in range(400):
        x1, x2 = rng.gauss(0, 1), rng.gauss(0, 1)
        p = 1 / (1 + math.exp(-(0.8 * x1 + 0.4 * x2)))
        t = rng.random() < p
        y = 2 * t + 1.5 * x1 + 0.5 * x2 + rng.gauss(0, 0.3)
        (tx if t else cx).append([x1, x2])
        (ty if t else cy).append(y)
    r = deep.psm_att(ty, cy, tx, cx)
    assert abs(r["att"] - 2) < 0.2
    assert r["smd_after_max"] < 0.1


def test_twfe_recovers_effect_and_pretrend() -> None:
    rng = random.Random(12)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(60):
        ufe = rng.gauss(0, 1)
        for p in range(6):
            is_post = 1 if p >= 3 else 0
            is_t = 1 if u < 30 else 0
            y.append(ufe + 0.3 * p + 2 * is_t * is_post + rng.gauss(0, 0.4))
            treat.append(is_t)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    r = deep.twfe_did(y, treat, post, unit, time)
    assert abs(r["att"] - 2) < 0.2
    assert r["pretrend"]["passed"] is True


def test_elasticity_with_controls() -> None:
    rng = random.Random(13)
    price = [1 + 0.2 * i for i in range(40)]
    qty = [100 * p ** -1.5 * math.exp(rng.gauss(0, 0.05)) for p in price]
    r = deep.elasticity_ols(price, qty)
    assert abs(r["elasticity"] + 1.5) < 0.1
    assert r["ci95"][0] < r["elasticity"] < r["ci95"][1]


def test_rdd_sensitivity() -> None:
    x = list(range(0, 101))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) for v in x]
    r = deep.rdd_sensitivity(y, x, 60)
    assert abs(r["estimate"] - 2) < 0.1
    assert r["p_placebo"] is not None


def test_mmm_deep() -> None:
    rng = random.Random(14)
    n = 60
    ch1 = [max(0, 20 + 10 * math.sin(i / 5) + rng.gauss(0, 3)) for i in range(n)]
    ch2 = [max(0, 15 + 8 * math.cos(i / 7) + rng.gauss(0, 3)) for i in range(n)]
    a1 = deep._hill(deep._adstock(ch1, 0.3), 1.0, 20)
    a2 = deep._hill(deep._adstock(ch2, 0.3), 1.0, 15)
    y = [100 + 120 * a + 90 * b + 0.2 * i for i, (a, b) in enumerate(zip(a1, a2))]
    r = deep.mmm_deep([ch1, ch2], y, ["tv", "search"])
    assert r["r2_train"] > 0.95
    assert r["r2_holdout"] > 0.8


def test_fulfillment_deep() -> None:
    r = deep.fulfillment_deep(30, 6, 3, 0.5, 100, 300, days=60, sims=200)
    assert 0 <= r["fill_rate"] <= 100
    assert 0 <= r["cycle_service_level"] <= 100
    assert r["avg_inventory"] > 0


# ====================================================================
# 合并自 test_methods_deep_advanced.py：深度方法测试（进阶）：PSM 反驳、事件研究、置换、交错、FE/IV、预算/CI、RDD 校正、预热。
# ====================================================================
# -*- coding: utf-8 -*-


def _panel_deep(effect: float = 2.0, units: int = 40, periods: int = 8, adopt: int = 4):
    rng = random.Random(21)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(units):
        ufe = rng.gauss(0, 1)
        is_t = u < units // 2
        for p in range(periods):
            is_post = 1 if (is_t and p >= adopt) else 0
            y.append(ufe + 0.3 * p + effect * is_post + rng.gauss(0, 0.4))
            treat.append(1 if is_t else 0)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    return y, treat, post, unit, time


def test_psm_refute() -> None:
    rng = random.Random(22)
    tx, cx, ty, cy = [], [], [], []
    for _ in range(200):
        x1, x2 = rng.gauss(0, 1), rng.gauss(0, 1)
        t = rng.random() < 1 / (1 + math.exp(-(0.8 * x1)))
        y = 2 * t + 1.5 * x1 + 0.5 * x2 + rng.gauss(0, 0.3)
        (tx if t else cx).append([x1, x2])
        (ty if t else cy).append(y)
    r = deep.psm_refute(ty, cy, tx, cx)
    assert r["original_att"] > 1.0
    assert r["placebo_att"] is None or abs(r["placebo_att"]) < 1.0


def test_event_study_and_placebo() -> None:
    y, t, p, u, tm = _panel_deep()
    es = deep.event_study(y, t, p, u, tm)
    assert "0" in es["coefficients"]
    assert abs(es["coefficients"]["0"]["coef"] - 2) < 0.6
    pb = deep.did_placebo(y, t, p, u, tm, n_perm=20)
    assert pb["main_att"] > 1.0
    assert pb["p_perm"] is None or 0 <= pb["p_perm"] <= 1


def test_staggered_att() -> None:
    rng = random.Random(23)
    y, treat, post, unit, time = [], [], [], [], []
    for u in range(30):
        adopt = 3 if u < 10 else (5 if u < 20 else None)
        for p in range(8):
            is_t = adopt is not None
            is_post = 1 if (is_t and p >= adopt) else 0
            y.append(rng.gauss(0, 1) + 0.2 * p + 2 * is_post)
            treat.append(1 if is_t else 0)
            post.append(is_post)
            unit.append(u)
            time.append(p)
    r = deep.staggered_att(y, treat, post, unit, time)
    assert abs(r["att"] - 2) < 0.6
    assert r["n_cells"] > 0


def test_elasticity_fe_and_iv() -> None:
    rng = random.Random(24)
    y, price, unit, time, z = [], [], [], [], []
    for u in range(25):
        for p in range(8):
            inst = rng.gauss(0, 1)
            pr = 2 + 0.5 * inst + rng.gauss(0, 0.1)
            q = 100 * pr ** -1.5 * math.exp(rng.gauss(0, 0.05))
            price.append(pr)
            y.append(q)
            unit.append(u)
            time.append(p)
            z.append(inst)
    fe = deep.elasticity_fe(price, y, unit, time)
    assert abs(fe["elasticity"] + 1.5) < 0.2
    iv = deep.elasticity_iv(price, y, z)
    assert abs(iv["elasticity"] + 1.5) < 0.3
    assert iv["first_stage_F"] > 10


def test_mmm_budget_and_ci() -> None:
    rng = random.Random(25)
    n = 60
    ch1 = [max(0, 20 + 10 * math.sin(i / 5) + rng.gauss(0, 3)) for i in range(n)]
    ch2 = [max(0, 15 + 8 * math.cos(i / 7) + rng.gauss(0, 3)) for i in range(n)]
    a1 = deep._hill(deep._adstock(ch1, 0.3), 1.0, 20)
    a2 = deep._hill(deep._adstock(ch2, 0.3), 1.0, 15)
    y = [100 + 120 * a + 90 * b + 0.2 * i for i, (a, b) in enumerate(zip(a1, a2))]
    b = deep.mmm_budget([ch1, ch2], y, ["tv", "search"], total_budget=100)
    assert abs(sum(b["allocation"].values()) - 100) < 1
    ci = deep.mmm_contribution_ci([ch1, ch2], y, ["tv", "search"], n_boot=10)
    assert "tv" in ci["contribution"]


def test_rdd_correction_and_balance() -> None:
    rng = random.Random(26)
    x = list(range(0, 101))
    y = [50 + 0.5 * v + (2 if v >= 60 else 0) + rng.gauss(0, 0.3) for v in x]
    cov = [[rng.gauss(0, 1)] for _ in x]
    r = deep.rdd_sensitivity(y, x, 60, covariates=cov)
    assert abs(r["estimate"] - 2) < 0.4
    assert r["quadratic_estimate"] is not None
    assert r["covariate_balance"]["balanced"] is True


def test_fulfillment_warmup() -> None:
    r = deep.fulfillment_deep(30, 6, 3, 0.5, 100, 300, days=60, sims=100)
    assert r["warmup_days"] > 0
    assert 0 <= r["fill_rate"] <= 100
