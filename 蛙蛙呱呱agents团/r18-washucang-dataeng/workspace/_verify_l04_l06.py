# -*- coding: utf-8 -*-
"""R18 step2 标杆对齐 · L04/L05/L06 实跑验收探针（一次性，不入产品路径）。"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engines.spec_ledger import DataEngSpecLedger, parse_target          # L04
from engines.slop_guard import DataEngSlopGuard, SLOP_TERMS              # L05
from engines.scenario_matrix import DataEngScenarioMatrix, WEIGHTS, SCENARIOS  # L06

out = {}

# ---------------- L04 ----------------
ledger = DataEngSpecLedger()
spec = ledger.load_spec()
print("[L04] load_spec ok=%s version=%s metrics=%d gates=%d redlines=%d dri=%s"
      % (spec["ok"], spec["version"], spec["metrics_count"], spec["gates_count"],
         spec["redlines_count"], spec["dri"]))
print("[L04] gate ids=%s" % [g["id"] for g in spec["gates"]])
print("[L04] metric codes=%s" % list(spec["metrics"].keys()))
print("[L04] thresholds=%s" % spec["thresholds"])
print("[L04] parse_target('≥ 99.5%%')=%s" % parse_target("≥ 99.5%"))
print("[L04] parse_target('≤ 15 min')=%s" % parse_target("≤ 15 min"))

good_obs = {"PSR": 0.996, "FSR": 0.992, "DQR": 0.985, "LCR": 1.0, "BCR": 1.0,
            "MTTD": 9.0, "DMR": 0.04, "ORT": 0}
ev_good = ledger.evaluate(good_obs)
print("[L04] evaluate(good) grade=%s passed=%d/%d ok=%s"
      % (ev_good["grade"], ev_good["passed"], ev_good["total"], ev_good["ok"]))
bad_obs = dict(good_obs, PSR=0.970, ORT=3)
ev_bad = ledger.evaluate(bad_obs)
print("[L04] evaluate(bad PSR=0.97,ORT=3) grade=%s passed=%d/%d failing=%s"
      % (ev_bad["grade"], ev_bad["passed"], ev_bad["total"],
         [k for k, v in ev_bad["metrics"].items() if not v["ok"]]))
ev_missing = ledger.evaluate({"PSR": 0.999})
print("[L04] evaluate(missing) grade=%s fail_closed=%s" % (
    ev_missing["grade"], all(not r["ok"] for r in ev_missing["metrics"].values())))

gates_all = {g["name"]: True for g in spec["gates"]}
btn = ledger.evaluate_gates(gates_all)
print("[L04] evaluate_gates(all pass) grade=%s %d/%d" % (btn["grade"], btn["passed"], btn["total"]))
gates_bad = dict(gates_all, **{"质量门禁": False})
btr = ledger.evaluate_gates(gates_bad)
print("[L04] evaluate_gates(G4 fail) grade=%s blocked_by=%s ok=%s"
      % (btr["grade"], btr["blocked_by"], btr["ok"]))
gates_empty = ledger.evaluate_gates({})
print("[L04] evaluate_gates(empty) grade=%s blocked_by=%d (fail-closed)" % (
    gates_empty["grade"], len(gates_empty["blocked_by"])))

exp_dir = os.path.join(tempfile.gettempdir(), "r18_l04_export")
ex = ledger.export(exp_dir)
print("[L04] export ok=%s files=%s gates=%d metrics=%d"
      % (ex["ok"], [os.path.basename(ex["json"]), os.path.basename(ex["sql"]),
                    os.path.basename(ex["dbt_schema"])], ex["gates_count"], ex["metrics_count"]))
for k in ("json", "sql", "dbt_schema"):
    print("[L04] export %s exists=%s size=%d" % (k, os.path.exists(ex[k]), os.path.getsize(ex[k])))
with open(ex["json"], encoding="utf-8") as f:
    back = json.load(f)
print("[L04] export json roundtrip metrics=%d gates=%d" % (len(back["metrics"]), len(back["gates"])))
out["L04"] = {"version": spec["version"], "metrics": spec["metrics_count"],
             "gates": spec["gates_count"], "redlines": spec["redlines_count"],
             "eval_good": ev_good["grade"], "eval_bad": ev_bad["grade"],
             "gates_blocked_by": btr["blocked_by"], "export_ok": ex["ok"]}

# ---------------- L05 ----------------
guard = DataEngSlopGuard()
print("[L05] SLOP_TERMS=%d terms dims=%s" % (
    len(SLOP_TERMS), sorted({t["dim"] for t in SLOP_TERMS})))
sample = ("本季度数据管道整体良好，核心链路基本正常，质量指标大幅提升。\n"
          "补充说明：相关细节待定，视情况而定，按需采购，持续关注。\n"
          "团队高度重视合规，暂无异常，剩余事项待定。")
a = guard.audit(sample)
print("[L05] audit has_slop=%s hits=%d score=%d grade=%s terms=%s"
      % (a["has_slop"], len(a["hits"]), a["actionability_score"], a["grade"], a["terms_found"]))
print("[L05] audit line/index sample=%s" % [(h["term"], h["line"], h["index"], h["severity"])
                                            for h in a["hits"][:4]])
c = guard.clean(sample)
after = guard.audit(c["cleaned"])
print("[L05] clean ok=%s before_score=%d after_score=%d residue=%d grade=%s"
      % (c["ok"], c["before"]["actionability_score"], c["after"]["actionability_score"],
         len(after["hits"]), c["grade"]))
print("[L05] clean replaced=%d terms=%s" % (len(c["replaced"]), [r["term"] for r in c["replaced"]]))
print("[L05] zero-residue assert = %s" % (not after["has_slop"] and not after["terms_found"]))
print("[L05] cleaned text preview: %s" % c["cleaned"].replace("\n", " / ")[:220])
# 幂等：清洗后再次清洗应无替换
c2 = guard.clean(c["cleaned"])
print("[L05] clean idempotent: second_replaced=%d score=%d"
      % (len(c2["replaced"]), c2["after"]["actionability_score"]))
# 清洗注入 facts 覆盖 DRI
c3 = guard.clean("整体良好。", facts={"dri": "蛙数仓-R18-夜班"})
print("[L05] clean(facts override) contains custom dri=%s" % ("蛙数仓-R18-夜班" in c3["cleaned"]))
print("[L05] score(vague no-number) = %d ; score(quantified) = %d" % (
    guard.actionability_score("整体良好"),
    guard.actionability_score("PSR=99.6%，DRI 蛙数仓 R18，T+1 10:00 闭环")))
out["L05"] = {"terms": len(SLOP_TERMS), "hits": len(a["hits"]),
              "score_before": c["before"]["actionability_score"],
              "score_after": c["after"]["actionability_score"],
              "residue_after_clean": len(after["hits"]), "ok": c["ok"]}

# ---------------- L06 ----------------
m = DataEngScenarioMatrix()
print("[L06] WEIGHTS=%s sum=%.2f" % (WEIGHTS, sum(WEIGHTS.values())))
print("[L06] SCENARIOS=%s" % [s["id"] for s in SCENARIOS])
base = m.generate()
print("[L06] generate() ranking=%s recommended=%s count=%d"
      % ([(r["id"], r["total_score"]) for r in base["scenarios"]],
         base["recommended_id"], base["scenario_count"]))
rk = m.rank()
print("[L06] rank()=%s" % [(r["rank"], r["id"], r["total_score"]) for r in rk])
strict = m.generate({"strict_consistency": True, "sla_hours": 24})
print("[L06] generate(strict_consistency) recommended=%s ranking=%s"
      % (strict["recommended_id"], [(r["id"], r["total_score"]) for r in strict["scenarios"]]))
fast = m.generate({"sla_hours": 1, "budget_days": 1})
print("[L06] generate(sla<=2h,budget<=1d) recommended=%s ranking=%s"
      % (fast["recommended_id"], [(r["id"], r["total_score"]) for r in fast["scenarios"]]))
md = m.render_markdown(base)
print("[L06] render_markdown lines=%d" % len(md.splitlines()))
print("[L06] md head:\n%s" % "\n".join(md.splitlines()[:6]))
print("[L06] md table rows=%d" % sum(1 for l in md.splitlines() if l.startswith("| ") and l[2].isdigit()))
note = base["note"]
no_decide = ("不替人类拍板" in note) and ("最终选型由人类" in note)
print("[L06] note=%s" % note)
print("[L06] no-decide constraint on note = %s" % no_decide)
print("[L06] no-decide in md = %s" % ("不替人类拍板" in md))
print("[L06] determinism: same-input identical = %s"
      % (m.generate()["scenarios"] == m.generate()["scenarios"]))
out["L06"] = {"weights_sum": round(sum(WEIGHTS.values()), 4),
              "scenarios": len(SCENARIOS), "recommended": base["recommended_id"],
              "strict_recommended": strict["recommended_id"],
              "fast_recommended": fast["recommended_id"],
              "no_decide": no_decide}

print("\n__SUMMARY__ " + json.dumps(out, ensure_ascii=False))
