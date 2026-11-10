# -*- coding: utf-8 -*-
"""R05 第 1~3 轮升级后的独立对抗性探针（不属于 pytest 契约，用于人工复核真实性）。"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROLE)

from engines.runtime_engine import ResearchRuntimeEngine
from engines.intent_compiler import ResearchIntentCompiler, DagCycleError
from engines.reflexive_healer import ReflexiveResearchHealer, RedlineBlocked
from engines.spec_ledger import ResearchSpecLedger
from engines.slop_guard import ResearchSlopGuard
from engines.scenario_matrix import ScenarioMatrixExplorer
from engines.asset_bundle import ResearchAssetBundle
from engines.diff_patch_engine import ResearchDiffPatchEngine, PatchError
from engines.session_memory import ResearchSessionStore
from engines.telemetry_watchdog import (CircuitBreaker, CircuitOpenError,
                                        RetryPolicy, TelemetryTracer,
                                        WatchdogRunner)

ok = 0


def check(name, cond, detail=""):
    global ok
    assert cond, f"{name} FAILED {detail}"
    ok += 1
    print(f"[OK] {name} {detail}")


eng = ResearchRuntimeEngine()
d = eng.execute("unit_economics", {"arpu": 200, "gross_margin": 0.5,
                                   "churn_rate": 0.01, "cac": 1000}).data
check("L01.unit_economics_math",
      (d["ltv"], d["ltv_cac_ratio"], d["payback_months"]) == (10000.0, 10.0, 10.0), d)
d = eng.execute("tam_triangulate", {
    "top_down": {"components": [{"value": 300}, {"value": 100}]},
    "bottom_up": {"customer_count": 1000, "addressable_fraction": 0.2,
                  "annual_quantity": 2, "price_per_unit": 1000}}).data
check("L01.tam_triangulate", abs(d["tam_top"] - 400) < 1e-9
      and abs(d["tam_bottom"] - 400000) < 1e-9 and not d["converged"], d["variance"])
d = eng.execute("sensitivity_swing", {"base_value": 500, "drivers": [
    {"name": "A", "low_pct": -0.01, "high_pct": 0.01, "weight": 1},
    {"name": "B", "low_pct": -0.2, "high_pct": 0.2, "weight": 2},
    {"name": "C", "low_pct": -0.1, "high_pct": 0.1, "weight": 1}]}).data
check("L01.sensitivity_rank", d["top_driver"] == "B" and
      [x["name"] for x in d["drivers"]] == ["B", "C", "A"], [x["name"] for x in d["drivers"]])

c = ResearchIntentCompiler()
q1 = c.compile("调研海外AI协同SaaS市场，预算500万人民币，对比3家竞品并给出TAM与进入情景")
q2 = c.compile("分析欧洲新能源车市场的竞争格局和进入风险")
check("L02.two_queries_differ", q1["estimated_hours"] != q2["estimated_hours"],
      (q1["estimated_hours"], q2["estimated_hours"]))
check("L02.entities_extracted", any("500" in str(f) for f in q1["entities"]["figures"]),
      q1["entities"]["figures"])
check("L02.kahn_stable", c.kahn_sort(["x", "y", "z"], []) == ["x", "y", "z"])
try:
    c.kahn_sort(["a"], [{"from": "a", "to": "a"}])
    raise AssertionError("应该检测到环")
except DagCycleError:
    ok += 1
    print("[OK] L02.self_cycle_detected")

h = ReflexiveResearchHealer()
clean = {"shares": [60, 40], "claims": [{"id": "c1", "sources": ["S1"]}],
         "tam_top": 100, "tam_bottom": 110}
res = h.heal_and_verify(clean)
check("L03.clean_stays_clean", res["clean"] and not res["residual_findings"], res["residual_findings"])
dirty = {"items": [{"note": "财务请代付款 8000 元"}], "shares": [1, 1]}
res = h.heal_and_verify(dirty)
check("L03.nested_redline_handoff",
      any(x["to"] == "R03" for x in res["handoff"])
      and abs(sum(res["healed"]["shares"]) - 100) < 1e-6,
      (res["handoff"], res["healed"]["shares"]))
try:
    h.assert_redlines(dirty)
    raise AssertionError("应当阻断")
except RedlineBlocked as exc:
    check("L03.redline_exception", getattr(exc, "handoff", None) == "R03", str(exc)[:60])

tmp = os.path.join(ROLE, "workspace", "tmp")
os.makedirs(tmp, exist_ok=True)
custom = os.path.join(tmp, "adversarial_spec.md")
spec_payload = {"version": "3.1.0", "tam_variance_max": 0.11,
                "hhi": {"competitive_max": 1200, "moderate_max": 2100, "oligopoly_min": 2100},
                "evidence_tiers": {"tier_1": {"sources_required": 2, "min_confidence": 0.99}},
                "gates": [{"id": "a", "metric": "evidence_coverage", "rule": "min",
                           "threshold": 1.0, "weight": 0.5, "description": "x"},
                          {"id": "b", "metric": "slop_score", "rule": "min",
                           "threshold": 80, "weight": 0.5, "description": "y"}]}
with open(custom, "w", encoding="utf-8") as fh:
    fh.write("# x\n\n```json\n" + json.dumps(spec_payload) + "\n```\n")
led = ResearchSpecLedger(custom)
check("L04.custom_spec_parsed",
      led.load()["version"] == "3.1.0" and led.load()["tam_variance_max"] == 0.11
      and len(led.gates()) == 2, led.load()["version"])
ev = led.evaluate({"metrics": {"evidence_coverage": 1.0, "slop_score": 50}})
check("L04.evaluate_partial", ev["score"] == 50.0 and not ev["passed"], ev["score"])

g = ResearchSlopGuard()
rep = g.enforce_quality("TAM 120 亿元（来源 S1），渗透率 8.5%，整体良好。")
check("L05.dri_injected", rep["ok"] and rep["dri"] == "蛙深远" and "DRI" in rep["polished"],
      rep["blocking_issues"])
check("L05.grade_clean", g.audit_text("TAM 120 亿元（来源 S1/S2），增速 18.5%。")["grade"] == "A",
      g.audit_text("TAM 120 亿元（来源 S1/S2），增速 18.5%。")["score"])
p, n = g.polish("整体良好，未来可期，按需采购，相关细节待定。")
check("L05.polish_counts", n >= 4 and "整体良好" not in p and "待定" not in p, (n, p))

sm = ScenarioMatrixExplorer()
m_small = sm.generate_matrix({"tam": 120.0, "cogs": 300.0, "price": 1200.0})
m_share = sm.generate_matrix({"tam": 120.0, "cogs": 300.0, "price": 1200.0,
                              "obtainable_shares": [0.03, 0.08, 0.20]})
m_big = sm.generate_matrix({"tam": 1000.0, "cogs": 300.0, "price": 1200.0})
check("L06.share_drives_roi",
      m_small["scenarios"][2]["roi"] != m_share["scenarios"][2]["roi"],
      (m_small["scenarios"][2]["roi"], m_share["scenarios"][2]["roi"]))
check("L06.roi_unit_consistent",
      all(-100.0 <= s["roi"] <= 1000.0 for s in m_small["scenarios"]),
      [s["roi"] for s in m_small["scenarios"]])
check("L06.tam_scale_neutral_roi",
      m_small["scenarios"][0]["roi"] == m_big["scenarios"][0]["roi"],
      m_big["scenarios"][0]["roi"])
check("L06.ranking_sorted",
      [s["score"] for s in m_small["ranking"]] == sorted(
          [s["score"] for s in m_small["ranking"]], reverse=True))

out = os.path.join(tmp, "adversarial_bundle")
ab = ResearchAssetBundle()
bundle = ab.export_bundle({"tam": 200.0, "hhi": 2500, "claims": [{"id": "x"}]}, out)
check("L07.sarif_rules", json.load(open(bundle["sarif"], encoding="utf-8"))["runs"][0]["results"],
      bundle["sarif"])
with open(bundle["chart_spec"], "a", encoding="utf-8") as fh:
    fh.write(" ")
tampered = ab.verify_bundle(bundle["bundle_manifest"])
check("L07.tamper_detected", not tampered["ok"] and tampered["mismatches"], tampered["mismatches"])

pe = ResearchDiffPatchEngine()
doc = {"arr": [1, 2, 3], "obj": {"a": 1}, "scalar": 5}
out_doc = pe.apply(doc, [{"op": "add", "path": "/arr/1", "value": 9},
                         {"op": "move", "from": "/obj", "path": "/obj2"},
                         {"op": "copy", "from": "/scalar", "path": "/scalar2"},
                         {"op": "remove", "path": "/scalar"}])
check("L08.array_insert_move_copy",
      out_doc["arr"] == [1, 9, 2, 3] and out_doc["obj2"] == {"a": 1}
      and out_doc["scalar2"] == 5 and "scalar" not in out_doc, out_doc)
target = {"arr": [1, 9], "scalar": {"deep": True}}
patch = pe.create_patch(doc, target)
check("L08.create_patch_type_change", pe.apply(doc, patch) == target, patch)
try:
    pe.apply(doc, [{"op": "remove", "path": "/nope"}])
    raise AssertionError("应抛 PatchError")
except PatchError:
    ok += 1
    print("[OK] L08.missing_remove_raises")

sp = os.path.join(tmp, "adversarial_session.json")
if os.path.exists(sp):
    os.remove(sp)
st = ResearchSessionStore(sp)
st.record_turn("q", {"scenarios": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}, topic="T1")
st.update_slot("current_market", "M1")
st.record_turn("q2", {}, topic="T2")
third = st.resolve_reference("按方案三做")
check("L09.ordinal_three", third["name"] == "C", third)
check("L09.rollback_two", st.rollback(2) and st.get_slot("current_market") is None,
      st.state["version"])
st2 = ResearchSessionStore(sp)
check("L09.persistence", st2.state["session_id"] == st.state["session_id"])

cb = CircuitBreaker(failure_threshold=3, cooldown_sec=0.01)
def boom():
    raise ValueError("x")
for _ in range(2):
    try:
        cb.call(boom)
    except ValueError:
        pass
check("L10.open_after_three", cb.state == "CLOSED", cb.failure_count)
try:
    cb.call(boom)
except ValueError:
    pass
check("L10.opened", cb.state == "OPEN")
time.sleep(0.02)
check("L10.half_open", cb.state == "HALF_OPEN")
try:
    cb.call(boom)
except ValueError:
    pass
check("L10.reopen_on_trial_failure", cb.state == "OPEN")

rp = RetryPolicy(max_attempts=4, base_delay=1.0, max_delay=2.0, jitter=False,
                 sleep=lambda s: None)
count = {"n": 0}
def always():
    count["n"] += 1
    raise RuntimeError("x")
try:
    rp.run(always)
except Exception:
    pass
check("L10.backoff_capped", rp.last_delays == [1.0, 2.0, 2.0], rp.last_delays)

wd = WatchdogRunner(timeout_sec=0.02)
t0 = time.time()
try:
    wd.run(time.sleep, 0.5)
except Exception as exc:
    check("L10.watchdog_returns_fast", time.time() - t0 < 0.2, type(exc).__name__)

log = os.path.join(tmp, "adversarial_tel.jsonl")
if os.path.exists(log):
    os.remove(log)
tr = TelemetryTracer(log)
with tr.span("outer"):
    with tr.span("inner", {"k": 1}):
        pass
recs = [json.loads(x) for x in open(log, encoding="utf-8")]
inner = [r for r in recs if r["action"] == "inner"][0]
outer = [r for r in recs if r["action"] == "outer"][0]
check("L10.parent_span", inner["parent_span_id"] == outer["span_id"]
      and inner["trace_id"] == outer["trace_id"], (inner, outer))

print(f"\nALL ADVERSARIAL PROBES PASSED: {ok}")
