#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R06 每个技能产出的「验证闭环」。

背景：run_tests.py 的 smoke 只验证「技能能跑、退出码 0」，但没有对每个技能的实际
产出做「契约校验(T6) + 对抗评审(T7)」的闭环验证。本脚本补齐这一步：

    对 15 个技能 × 36 个动作，逐一：
        1. 真实运行（subprocess 调 agent.py，端到端）
        2. 契约校验 contracts.validate_output(skill, action, output)
        3. 对抗评审 review.review_packet({skill, action, result, data_ref})
        4. 汇总成闭环矩阵 → 输出 {skill, action, contract_ok, review_verdict, ...}

闭环通过标准：契约通过 且 评审 PASS。退出码 = 0 当且仅当全部动作闭环通过。

用法：
    python verify_loop.py            # 全量闭环
    python verify_loop.py --json     # 只输出闭环矩阵 JSON（供编排器消费）
"""
from __future__ import annotations

import argparse
import json
import os

import subprocess
import sys
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(HERE)
for p in (HERE, _AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import contracts  # noqa: E402
import review  # noqa: E402
from skills import _common as c  # noqa: E402

WS = os.path.join(role_workspace(HERE))


def run(argv):
    r = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *argv],
                       cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout, r.stderr


def extract(stdout):
    marker = "__AGENT_RESULT__"
    i = stdout.find(marker)
    if i == -1:
        return None
    s = stdout[i + len(marker):].strip()
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find("{"), s.rfind("}")
        return json.loads(s[a:b + 1]) if a != -1 and b != -1 else None


def _write_clean(path):
    """干净订单 CSV（无缺失/无哨兵），供统计类动作产出可复算结果。"""
    chans = ["抖音", "微信", "小红书", "知乎"]
    statuses = ["浏览", "加购", "支付", "下单"]
    lines = ["order_id,date,channel,status,user_id,amount"]
    for i in range(1, 21):
        amt = round(50 + i * 3.7, 2)
        lines.append(f"{i},2024-01-{i:02d},{chans[i % 4]},{statuses[i % 4]},u{i},{amt}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _write_saas(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("customer_id,month,mrr,status\n"
                "c1,2024-01,100,active\nc2,2024-01,200,active\nc3,2024-01,300,active\n"
                "c1,2024-02,100,active\nc2,2024-02,250,active\n"
                "c3,2024-02,0,canceled\nc4,2024-02,150,active\n")
    return path


def _write_text(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("id,text\n"
                "1,用户留存下降需要分析原因\n"
                "2,渠道投放的转化率在波动\n"
                "3,价格调整对客单价有影响\n"
                "4,新功能上线后激活率提升\n")
    return path


def _write_selfmedia(path):
    raw = {
        "platforms": {
            "douyin": {"fans": 12000, "new_fans": 340, "revenue": 5200.5,
                       "posts": 12, "last_update": "2026-11-01"},
            "xiaohongshu": {"fans": 8000, "new_fans": 210, "revenue": 3100.0,
                            "posts": 8, "last_update": "2026-10-28"},
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False)
    return path


def prepare():
    os.makedirs(WS, exist_ok=True)
    csv = _write_clean(os.path.join(WS, "_loop_clean.csv"))
    model = os.path.join(HERE, "examples", "semantic_model.json")
    saas_csv = _write_saas(os.path.join(WS, "_loop_saas.csv"))
    text_csv = _write_text(os.path.join(WS, "_loop_text.csv"))
    selfmedia_raw = _write_selfmedia(os.path.join(WS, "_loop_selfmedia_raw.json"))
    spec = os.path.join(WS, "_loop_chart_spec.json")
    with open(spec, "w", encoding="utf-8") as f:
        json.dump({"chart_type": "bar", "title": "各渠道营收",
                   "x_field": "label", "y_field": "value",
                   "data": [{"label": "抖音", "value": 120.0},
                            {"label": "微信", "value": 80.0}]}, f, ensure_ascii=False)
    metrics_json = os.path.join(WS, "_loop_metrics.json")
    with open(metrics_json, "w", encoding="utf-8") as f:
        json.dump({"describe": {"amount": {"count": 20, "mean": 88.85}}}, f, ensure_ascii=False)
    return {"csv": csv, "model": model, "saas_csv": saas_csv, "text_csv": text_csv,
            "selfmedia_raw": selfmedia_raw, "spec": spec, "metrics_json": metrics_json}


# 每个动作：(skill, action, argv_tail, data_ref)
#   argv_tail 不含 python/agent.py；统计模块是单层命令，action == skill。
def build_plan(d):
    csv, model = d["csv"], d["model"]
    saas_csv, text_csv = d["saas_csv"], d["text_csv"]
    raw, spec, mjson = d["selfmedia_raw"], d["spec"], d["metrics_json"]

    norm = os.path.join(WS, "_loop_normalized.json")
    dash = os.path.join(WS, "_loop_dashboard.json")
    cleaned = os.path.join(WS, "_loop_cleaned.csv")

    return [
        # --- semantics (5) ---
        ("semantics", "validate", ["semantics", "validate", "--input", model], None),
        ("semantics", "tree", ["semantics", "tree", "--input", model], None),
        ("semantics", "link", ["semantics", "link", "--input", model, "--data", csv], csv),
        ("semantics", "compute", ["semantics", "compute", "--input", model, "--data", csv], csv),
        ("semantics", "reconcile", ["semantics", "reconcile", "--a", "100", "--b", "102",
                                    "--domain", "product", "--label", "metric"], None),
        # --- quality (2) ---
        ("quality", "audit", ["quality", "audit", "--input", csv, "--pk", "order_id",
                              "--date", "date"], csv),
        ("quality", "clean", ["quality", "clean", "--input", csv, "--output", cleaned,
                              "--pk", "order_id"], csv),
        # --- explore (9) ---
        ("explore", "trend", ["explore", "trend", "--input", csv, "--date", "date",
                              "--value", "amount"], csv),
        ("explore", "groupby", ["explore", "groupby", "--input", csv, "--group", "channel",
                                "--value", "amount"], csv),
        ("explore", "funnel", ["explore", "funnel", "--input", csv, "--stage", "status"], csv),
        ("explore", "cohort", ["explore", "cohort", "--input", csv, "--user", "user_id",
                               "--period", "date"], csv),
        ("explore", "rfm", ["explore", "rfm", "--input", csv, "--user", "user_id",
                            "--date", "date", "--value", "amount"], csv),
        ("explore", "saas", ["explore", "saas", "--mrr", "3000", "--active_users", "100",
                             "--churn_rate", "0.05"], None),
        ("explore", "time_series", ["explore", "time_series", "--input", csv, "--date", "date",
                                    "--value", "amount", "--window", "3"], csv),
        ("explore", "segment", ["explore", "segment", "--input", csv, "--features", "amount",
                                "--k", "3", "--user", "user_id"], csv),
        ("explore", "metrics", ["explore", "metrics", "--input", saas_csv, "--model", "saas"],
         saas_csv),
        # --- rootcause (2) ---
        ("rootcause", "decompose", ["rootcause", "decompose", "--input", csv, "--dim", "channel",
                                    "--value", "amount", "--period", "date",
                                    "--before", "2024-01-01", "--after", "2024-12-31"], csv),
        ("rootcause", "drilldown", ["rootcause", "drilldown", "--input", csv, "--dim", "channel",
                                    "--value", "amount"], csv),
        # --- 统计 7 模块（单层命令，action == skill）---
        ("describe", "describe", ["describe", "--input", csv, "--col", "amount"], csv),
        ("correlate", "correlate", ["correlate", "--input", csv, "--col-a", "amount",
                                    "--col-b", "amount"], csv),
        ("ttest", "ttest", ["ttest", "--input", csv, "--value", "amount", "--group", "channel",
                            "--group-a", "抖音", "--group-b", "微信"], csv),
        ("chi2", "chi2", ["chi2", "--input", csv, "--row", "channel", "--col", "status"], csv),
        ("anova", "anova", ["anova", "--input", csv, "--value", "amount", "--group", "channel"],
         csv),
        ("regression", "regression", ["regression", "--input", csv, "--x", "amount",
                                      "--y", "amount"], csv),
        ("abtest", "abtest", ["abtest", "--input", csv, "--group", "channel",
                              "--control", "抖音", "--treatment", "微信", "--metric", "amount"],
         csv),
        # --- scinlp (3) ---
        ("scinlp", "describe", ["scinlp", "describe", "--input", csv, "--col", "amount"], csv),
        ("scinlp", "textstats", ["scinlp", "textstats", "--input", text_csv, "--text", "text"],
         text_csv),
        ("scinlp", "backend", ["scinlp", "backend"], None),
        # --- domain (2) ---
        ("domain", "list", ["domain", "list"], None),
        ("domain", "run", ["domain", "run", "--data", csv, "--pipeline", "preprocess"], csv),
        # --- viz (3) ---
        ("viz", "spec", ["viz", "spec", "--input", spec], None),
        ("viz", "report", ["viz", "report", "--metrics", mjson, "--title", "闭环报告",
                           "--output", os.path.join(WS, "_loop_report.md")], mjson),
        ("viz", "guide", ["viz", "guide", "--chart", "bar"], None),
        # --- selfmedia (3，链式) ---
        ("selfmedia", "normalize", ["selfmedia", "normalize", "--input", raw, "--output", norm],
         raw),
        ("selfmedia", "dashboard", ["selfmedia", "dashboard", "--input", norm,
                                    "--today", "2026-11-04", "--output", dash], norm),
        ("selfmedia", "report", ["selfmedia", "report", "--input", dash, "--output",
                                 os.path.join(WS, "_loop_daily.md")], dash),
    ]


# 元信息/指南类动作：产出是选型提示词/清单，非数据分析结果，豁免 value_utility
# 注：viz.report 产出 report_path（无量化结论），selfmedia.normalize 产出
# normalized_path（仅归一化），同属基础设施动作，一并豁免。
_META_ACTIONS = {("viz", "guide"), ("domain", "list"), ("scinlp", "backend"),
                 ("viz", "report"), ("selfmedia", "normalize")}


def run_closed_loop(plan):
    rows = []
    for skill, action, argv, data_ref in plan:
        rc, out, err = run(argv)
        result = extract(out)
        if result is None:
            rows.append({"skill": skill, "action": action, "ran": False,
                         "exit_code": rc, "error": "no __AGENT_RESULT__",
                         "contract_ok": False, "review_verdict": "N/A"})
            continue
        cok = contracts.validate_output(skill, action, result)["ok"]
        rev = review.review_packet({"skill": skill, "action": action,
                                    "result": result, "data_ref": data_ref},
                                   check_value_utility=(skill, action) not in _META_ACTIONS)
        rows.append({"skill": skill, "action": action, "ran": True,
                     "exit_code": rc, "contract_ok": cok,
                     "review_verdict": rev["verdict"],
                     "failure_category": rev.get("failure_category"),
                     "issue_count": len(rev.get("issues", []))})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = prepare()
    plan = build_plan(d)
    rows = run_closed_loop(plan)

    passed = [r for r in rows if r.get("contract_ok") and r.get("review_verdict") == "PASS"]
    failed = [r for r in rows if r not in passed]

    summary = {
        "total": len(rows),
        "passed": len(passed),
        "failed": len(failed),
        "rows": rows,
        "failed_detail": failed,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if not failed else 1

    print("== R06 每个技能产出的验证闭环 ==")
    for r in rows:
        mark = "PASS" if (r.get("contract_ok") and r.get("review_verdict") == "PASS") else "FAIL"
        cat = r.get("failure_category") or ""
        err = r.get("error") or ""
        print(f"  [{mark}] {r['skill']}/{r['action']}"
              f"  contract={'OK' if r.get('contract_ok') else 'X'}"
              f"  review={r.get('review_verdict')}"
              f"  issues={r.get('issue_count', 0)}"
              + (f"  cat={cat}" if cat else "")
              + (f"  ERR={err}" if err else ""))

    print("\n================ 闭环汇总 ================")
    print(f"  PASS {len(passed)} / {len(rows)}")
    if failed:
        print("  未闭环的动作：")
        for r in failed:
            print(f"    - {r['skill']}/{r['action']}"
                  f"  contract={'OK' if r.get('contract_ok') else 'FAIL'}"
                  f"  review={r.get('review_verdict')}"
                  f"  cat={r.get('failure_category') or r.get('error')}")
        return 1
    print("  ALL CLOSED-LOOP GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
