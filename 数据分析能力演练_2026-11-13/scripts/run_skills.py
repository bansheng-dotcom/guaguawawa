# -*- coding: utf-8 -*-
"""跑一遍 R06 蛙得清的全部分析技能，把结构化结果落到 results/。"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
AGENTS = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
DATA = HERE / "data"
RES = HERE / "results"
RES.mkdir(exist_ok=True)

PY = sys.executable


def p(name: str) -> str:
    return str(DATA / name)


def r(name: str) -> str:
    return str(RES / name)


P1 = [
    ("quality_audit", ["quality", "audit", "--input", p("orders.csv"), "--pk", "order_id", "--date", "order_date"]),
    ("quality_clean", ["quality", "clean", "--input", p("orders.csv"), "--output", r("orders_clean.csv"), "--pk", "order_id"]),
    ("semantics_validate", ["semantics", "validate", "--input", p("semantic_model.json")]),
    ("semantics_compute", ["semantics", "compute", "--input", p("semantic_model.json"), "--data", p("orders.csv")]),
    ("semantics_reconcile_pass", ["semantics", "reconcile", "--a", "1904317.5", "--b", "1904317.5",
                                  "--domain", "marketing", "--label", "GMV 对账"]),
    ("semantics_reconcile_fail", ["semantics", "reconcile", "--a", "4653", "--b", "11042.45",
                                  "--domain", "marketing", "--label", "化妆品市场规模口径"]),
    ("scinlp_describe_revenue", ["scinlp", "describe", "--input", p("orders.csv"), "--col", "revenue"]),
    ("scinlp_backend", ["scinlp", "backend"]),
    ("viz_spec", ["viz", "spec", "--input", p("chart_spec.json")]),
    ("domain_list", ["domain", "list"]),
    ("viz_guide", ["viz", "guide"]),
    ("viz_report", ["viz", "report", "--metrics", r("metrics_for_viz.json"), "--title", "个护线上增长拆解", "--output", r("viz_report.md")]),
]

P2 = [
    ("describe_unit_price", ["describe", "--input", p("orders.csv"), "--col", "unit_price"]),
    ("describe_revenue", ["describe", "--input", p("orders.csv"), "--col", "revenue"]),
    ("correlate_discount_revenue", ["correlate", "--input", p("orders.csv"), "--col-a", "discount", "--col-b", "revenue"]),
    ("regression_price_qty", ["regression", "--input", p("orders.csv"), "--x", "unit_price", "--y", "qty"]),
    ("elasticity_weekly", ["elasticity", "--input", p("price_qty_weekly.csv"), "--price", "avg_price", "--qty", "units"]),
    ("rootcause_decompose", ["rootcause", "decompose", "--input", p("panel_did.csv"), "--dim", "city",
                             "--value", "gmv", "--period", "post", "--before", "0", "--after", "1"]),
    ("rootcause_drilldown", ["rootcause", "drilldown", "--input", p("orders.csv"), "--dim", "category", "--value", "revenue"]),
    ("scinlp_textstats", ["scinlp", "textstats", "--input", p("sku_titles.csv"), "--text", "title", "--top", "15"]),
]

P3 = [
    ("describe_band_sales", ["describe", "--input", p("price_bands.csv"), "--col", "sales_share_pct"]),
    ("describe_band_volume", ["describe", "--input", p("price_bands.csv"), "--col", "volume_share_pct"]),
    ("chi2_category_returned", ["chi2", "--input", p("orders.csv"), "--row", "category", "--col", "returned"]),
    ("anova_revenue_category", ["anova", "--input", p("orders.csv"), "--value", "revenue", "--group", "category"]),
    ("rdd_paid_value", ["rdd", "--input", p("rdd_carts.csv"), "--y", "paid_value", "--running", "cart_value",
                        "--cutoff", "99", "--sensitivity", "--covariates", "is_new,douyin,city_tier"]),
    ("describe_rdd_paid", ["describe", "--input", p("rdd_carts.csv"), "--col", "paid_value"]),
]

P4 = [
    ("power_n", ["power", "--baseline", "0.032", "--mde", "0.0025", "--alpha", "0.05", "--power", "0.8"]),
    ("power_mde", ["power", "--baseline", "0.032", "--n-per-group", "100000", "--alpha", "0.05", "--power", "0.8"]),
    ("abtest_convert", ["abtest", "--input", p("ab_clean.csv"), "--group", "group", "--control", "A", "--treatment", "B", "--metric", "convert"]),
    ("abtest_click", ["abtest", "--input", p("ab_clean.csv"), "--group", "group", "--control", "A", "--treatment", "B", "--metric", "click"]),
    ("abtest_srm", ["abtest", "--input", p("ab_srm.csv"), "--group", "group", "--control", "A", "--treatment", "B", "--metric", "convert"]),
    ("ttest_revenue", ["ttest", "--input", p("ab_clean.csv"), "--value", "revenue", "--group", "group", "--group-a", "A", "--group-b", "B"]),
    ("chi2_device_convert", ["chi2", "--input", p("ab_clean.csv"), "--row", "device", "--col", "convert"]),
]

P5 = [
    ("did_twfe", ["did", "--input", p("panel_did.csv"), "--y", "gmv", "--treat", "treat", "--post", "post",
                  "--unit", "city_id", "--time", "week", "--event-study", "--placebo"]),
    ("did_staggered", ["did", "--input", p("panel_staggered.csv"), "--y", "gmv", "--treat", "treat", "--post", "post",
                       "--unit", "city_id", "--time", "week", "--staggered"]),
    ("matched_psm", ["matched", "--treat", p("cities_treat.csv"), "--control", p("cities_control.csv"),
                     "--col", "gmv_growth", "--covariates", "population,income_index,douyin_penetration,ecommerce_index",
                     "--refute"]),
    ("causal_backdoor", ["causal", "--input", p("cities_all.csv"), "--outcome", "gmv_growth", "--treatment", "treat",
                         "--confounders", "population,income_index,douyin_penetration,ecommerce_index", "--trials", "200"]),
]

P6 = [
    ("funnel", ["explore", "funnel", "--input", p("funnel.csv"), "--stage", "stage",
                "--order", "曝光,点击,加购,下单,支付"]),
    ("cohort", ["explore", "cohort", "--input", p("orders.csv"), "--user", "customer_id", "--period", "order_month"]),
    ("rfm", ["explore", "rfm", "--input", p("orders.csv"), "--user", "customer_id", "--date", "order_date", "--value", "revenue"]),
    ("segment", ["explore", "segment", "--input", p("customer_features.csv"),
                 "--features", "orders,revenue,recency_days,aov", "--k", "4", "--user", "customer_id", "--seed", "42"]),
    ("metrics_ecommerce", ["explore", "metrics", "--input", p("orders.csv"), "--model", "ecommerce",
                           "--value", "revenue", "--customer", "customer_id", "--month", "order_month",
                           "--cac_spend", "80000"]),
    ("time_series", ["explore", "time_series", "--input", p("orders.csv"), "--date", "order_date",
                     "--value", "revenue", "--window", "7"]),
    ("ttest_new", ["ttest", "--input", p("orders.csv"), "--value", "revenue", "--group", "is_new", "--group-a", "1", "--group-b", "0"]),
    ("chi2_channel_returned", ["chi2", "--input", p("orders.csv"), "--row", "channel", "--col", "returned"]),
    ("explore_saas", ["explore", "saas", "--mrr", "500000", "--active_users", "1200", "--churn_rate", "0.04"]),
    ("selfmedia_normalize", ["selfmedia", "normalize", "--input", p("selfmedia_raw.json"), "--output", r("selfmedia_norm.json")]),
    ("selfmedia_dashboard", ["selfmedia", "dashboard", "--input", r("selfmedia_norm.json"), "--today", "2026-11-12",
                             "--output", r("selfmedia_dash.json")]),
    ("selfmedia_report", ["selfmedia", "report", "--input", r("selfmedia_dash.json"), "--output", r("selfmedia_daily.md")]),
]

ALL = {"P1": P1, "P2": P2, "P3": P3, "P4": P4, "P5": P5, "P6": P6}


def parse(out: str) -> dict:
    for line in out.splitlines():
        if "__AGENT_RESULT__" in line:
            try:
                return json.loads(line.split("__AGENT_RESULT__", 1)[1].strip())
            except json.JSONDecodeError:
                pass
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def main() -> int:
    log = []
    for group, cmds in ALL.items():
        for name, args in cmds:
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "guagua.py", "call", "r06", *args], cwd=str(AGENTS),
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
            ms = int((time.perf_counter() - t0) * 1000)
            out = (proc.stdout or "") + (proc.stderr or "")
            data = parse(out)
            (RES / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            ok = proc.returncode == 0 and bool(data) and not data.get("error")
            log.append({"group": group, "name": name, "cmd": " ".join(args), "exit": proc.returncode,
                        "ms": ms, "ok": ok, "keys": sorted(data.keys())[:8]})
            print(f"[{'OK' if ok else '!!'}] {group} {name} {ms}ms keys={sorted(data.keys())[:6]}")
    (RES / "_run_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [x for x in log if not x["ok"]]
    print(f"\n{len(log)} 个技能调用，{len(log)-len(bad)} 成功，{len(bad)} 失败")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
