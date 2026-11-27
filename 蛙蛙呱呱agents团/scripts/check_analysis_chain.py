# -*- coding: utf-8 -*-
"""scripts/check_analysis_chain.py —— R06 分析链门禁：六段工件齐全、哈希/门禁/跨段一致。

两种用法：
    python scripts/check_analysis_chain.py --dir <输出目录>   # 复核一次真实运行
    python scripts/check_analysis_chain.py --selftest        # 用三份预埋真因数据集端到端自测

判据（任一不满足即 exit 1）：
  1. chain_manifest.json 存在且 ok=true；
  2. 六个阶段文件齐全、sha256 与 manifest 一致；
  3. 每段 gate.ok=true；
  4. 跨段一致：假设↔计划、解释根变化↔发现、统计指标↔计划、驱动↔分段；
  5. 自测时：三份数据的预埋真因必须出现在头号驱动里。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "r06-wadeqing-analyst"
for p in (str(ROOT), str(ROLE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from analysis_chain import common, runner  # noqa: E402
from analysis_chain import deliver as deliver_mod, report_runner  # noqa: E402

CASES = [
    {"name": "retail", "data": ROLE / "cases" / "analysis-retail" / "data.csv",
     "question": "9月利润为什么下滑", "start": "2026-06-01", "end": "2026-09-28",
     "split": "2026-07-31", "dims": ["channel", "category"], "metric": "profit",
     "domain": "profit", "date": "date", "qty": "qty", "expect": "抖音"},
    {"name": "saas", "data": ROLE / "cases" / "analysis-saas" / "data.csv",
     "question": "客户流失风险为什么上升", "start": "2025-01", "end": "2026-12",
     "split": "2025-12", "dims": ["onboarding", "plan"], "metric": "churn_flag",
     "domain": "churn", "date": "month", "qty": None, "expect": "pending"},
    {"name": "selfmedia", "data": ROLE / "cases" / "analysis-selfmedia" / "data.csv",
     "question": "播放量为什么增长", "start": "2026-07-01", "end": "2026-09-28",
     "split": "2026-08-15", "dims": ["platform", "account"], "metric": "views",
     "domain": "growth", "date": "date", "qty": "posts", "expect": "抖音"},
]


def check_dir(path: str) -> dict:
    checks = []
    manifest_path = os.path.join(path, "chain_manifest.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "checks": [common.ck(False, f"缺少 {manifest_path}",
                                                  "existence", "CRITICAL")],
                "errors": [f"缺少 {manifest_path}"]}
    manifest = common.read_json(manifest_path)
    checks.append(common.ck(bool(manifest.get("ok")), "manifest ok=true", "gate",
                            "CRITICAL" if not manifest.get("ok") else "OK"))
    stages = manifest.get("stages") or []
    names = [s.get("stage") for s in stages]
    checks.append(common.ck(names == list(common.STAGE_ORDER),
                            f"阶段顺序 {names}", "structure",
                            "CRITICAL" if names != list(common.STAGE_ORDER) else "OK"))
    for item in stages:
        p = os.path.join(path, item.get("file", ""))
        exists = os.path.exists(p)
        checks.append(common.ck(exists, f"{item.get('stage')} 文件存在", "existence",
                                "CRITICAL" if not exists else "OK"))
        if not exists:
            continue
        sha = common.sha256_file(p)
        checks.append(common.ck(sha == item.get("sha256"), f"{item.get('stage')} 哈希一致",
                                "integrity", "CRITICAL" if sha != item.get("sha256") else "OK"))
        art = common.read_json(p)
        g = art.get("gate") or {}
        checks.append(common.ck(bool(g.get("ok")), f"{item.get('stage')} 门禁通过",
                                "gate", "CRITICAL" if not g.get("ok") else "OK"))

    arts = {}
    for item in stages:
        p = os.path.join(path, item.get("file", ""))
        if os.path.exists(p):
            arts[item.get("stage")] = common.read_json(p)
    f, pl = arts.get("frame"), arts.get("plan")
    if f and pl:
        fids = sorted(h["id"] for h in f.get("hypotheses", []))
        pids = sorted(r.get("hypothesis_id") for r in pl.get("rounds", []))
        checks.append(common.ck(fids == pids, "假设↔计划一一对应", "consistency",
                                "CRITICAL" if fids != pids else "OK"))
    fd, ex = arts.get("explore"), arts.get("explain")
    if fd and ex:
        overall = next((x for x in fd.get("findings", []) if x.get("type") == "overall"), {})
        delta = (ex.get("root") or {}).get("delta")
        tol = max(0.5, abs(overall.get("delta", 0)) * 0.005)
        checks.append(common.ck(isinstance(delta, (int, float)) and
                                abs(delta - overall.get("delta", 0)) <= tol,
                                "解释根变化↔发现", "consistency",
                                "CRITICAL" if not (isinstance(delta, (int, float)) and
                                                   abs(delta - overall.get("delta", 0)) <= tol) else "OK"))
        dim = ex.get("dimension")
        seg_pairs = {((x.get("segment_definition") or {}).get("column"), x.get("segment"))
                     for x in fd.get("findings", []) if x.get("type") == "segment"}
        for d in ex.get("drivers", [])[:5]:
            ok_d = (dim, d.get("segment")) in seg_pairs
            checks.append(common.ck(ok_d, f"驱动可追到分段 {d.get('driver')}",
                                    "traceability", "CRITICAL" if not ok_d else "OK"))
    st = arts.get("test")
    if st and pl:
        checks.append(common.ck(st.get("metric") == pl.get("metric"),
                                "统计指标↔计划", "consistency",
                                "CRITICAL" if st.get("metric") != pl.get("metric") else "OK"))
        if fd:
            overall = next((x for x in fd.get("findings", []) if x.get("type") == "overall"), {})
            ev = overall.get("evidence") or {}
            h = st.get("headline") or {}
            same = ev.get("rows_before") == h.get("n_before") and ev.get("rows_after") == h.get("n_after")
            checks.append(common.ck(same, "统计样本量↔发现样本量", "traceability",
                                    "CRITICAL" if not same else "OK"))
    g = common.gate(checks, "analysis_chain")
    return {"ok": g["ok"], "grade": g["grade"], "checks": g["checks"],
            "errors": g["errors"], "warnings": g.get("warnings", [])}


def selftest() -> dict:
    results, checks = [], []
    for case in CASES:
        out = tempfile.mkdtemp(prefix=f"chain_gate_{case['name']}_")
        t0 = time.time()
        manifest = runner.run(case["question"], str(case["data"]), out,
                              case["start"], case["end"], case["split"],
                              dimensions=case["dims"], metric=case["metric"],
                              domain=case["domain"], date=case["date"],
                              qty=case["qty"])
        elapsed = round(time.time() - t0, 2)
        ex = common.read_json(os.path.join(out, "explanation.json")) if os.path.exists(
            os.path.join(out, "explanation.json")) else {}
        top = ex.get("top_driver", "")
        ok = bool(manifest.get("ok")) and case["expect"] in top
        checks.append(common.ck(bool(manifest.get("ok")),
                                f"{case['name']} 六段门禁全过", "selftest",
                                "CRITICAL" if not manifest.get("ok") else "OK"))
        checks.append(common.ck(case["expect"] in top,
                                f"{case['name']} 预埋真因命中（top={top}）", "selftest",
                                "CRITICAL" if case["expect"] not in top else "OK"))
        rep = report_runner.run_report(out, os.path.join(out, "report"))
        html_path = os.path.join(out, "report", "report.html")
        pack_path = os.path.join(out, "analysis_material_pack.json")
        trace = {"ok": False, "rate": 0.0, "untraced": ["未产出"]}
        if os.path.exists(html_path) and os.path.exists(pack_path):
            trace = deliver_mod.audit_trace(
                open(html_path, encoding="utf-8").read(),
                common.read_json(pack_path))
        charts = common.read_json(os.path.join(out, "chart_spec_pack.json")) \
            if os.path.exists(os.path.join(out, "chart_spec_pack.json")) else {"charts": []}
        chart_ok = bool(charts.get("charts")) and all(
            (c.get("series_completeness") or {}).get("ratio") == 1
            and "required_series" in (c.get("fail_if_missing") or [])
            and (c.get("annotation_plan") or {}).get("avoid_overlap") is True
            for c in charts.get("charts", []))
        checks.append(common.ck(bool(rep.get("ok")),
                                f"{case['name']} T8b 报告链门禁", "report",
                                "CRITICAL" if not rep.get("ok") else "OK"))
        checks.append(common.ck(trace["ok"], f"{case['name']} 结论可追率={trace['rate']:.0%}",
                                "report", "CRITICAL" if not trace["ok"] else "OK"))
        checks.append(common.ck(chart_ok, f"{case['name']} 图表必绘/标注门禁", "report",
                                "CRITICAL" if not chart_ok else "OK"))
        results.append({"case": case["name"], "ok": ok and bool(rep.get("ok")),
                        "top_driver": top, "elapsed_sec": elapsed,
                        "trace_rate": round(trace["rate"], 3), "out_dir": out})
    g = common.gate(checks, "analysis_chain_selftest")
    return {"ok": g["ok"], "grade": g["grade"], "cases": results,
            "checks": g["checks"], "errors": g["errors"],
            "warnings": g.get("warnings", [])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_analysis_chain")
    ap.add_argument("--dir", default=None, help="复核一次 run 的输出目录")
    ap.add_argument("--selftest", action="store_true", help="跑三份预埋真因数据集")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.dir and not a.selftest:
        a.selftest = True
    out = selftest() if a.selftest else check_dir(a.dir)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for r in out.get("cases", []):
            print(f"[{'OK' if r['ok'] else 'FAIL'}] {r['case']:<10} "
                  f"{r['top_driver']:<24} {r['elapsed_sec']}s")
        for e in out.get("errors", []):
            print(f"  - {e}")
        print(f"[{'PASS' if out['ok'] else 'FAIL'}] analysis_chain "
              f"grade={out.get('grade')}")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
