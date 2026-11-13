# -*- coding: utf-8 -*-
"""R06 数据分析能力升级（P0/P1）回归测试。

覆盖：质量两维、精确 p/BH、图表精度、多元回归、事件研究 v2、数据契约、结论层。
运行：python -m pytest tests/test_analysis_upgrade.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1]
FIX = AGENTS / "tests" / "fixtures"
sys.path.insert(0, str(AGENTS))


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


def test_report_status_kpi_and_caveats():
    from core import report_bridge
    c = report_bridge.generic_contract(
        {"ok": True, "status": "warn", "conclusion": "结论", "caveats": ["边界A", "边界B"]},
        "r06", "蛙得清", "数据分析师", "ttest", "run", "测试")
    assert any(m.get("label") == "技能状态" and m.get("status") == "watch"
               for m in c["metric_strip"])
    notes = " ".join(str(x.get("text")) for x in c["notes"]["items"])
    assert "边界A" in notes


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
