import json, sys, os
sys.path.insert(0, os.getcwd())
from engines.runtime_engine import DataEngRuntimeEngine
from engines.intent_compiler import DataEngIntentCompiler, DEPENDENCIES
from engines.reflexive_healer import DataEngReflexiveHealer

e = DataEngRuntimeEngine()
r = e.run_sql({"orders":[{"id":1,"amt":10},{"id":2,"amt":20},{"id":3,"amt":30}]},
              "SELECT SUM(amt) AS total, COUNT(*) AS n FROM orders WHERE amt > 10")
print("L01 run_sql:", r["engine"], r["columns"], r["rows"], r["sha256"][:16])
print("L01 fingerprint stable:", e.fingerprint([{"a":1},{"a":2}]) == e.fingerprint([{"a":2},{"a":1}]))

dirty = [{"id":1,"v":"x"},{"id":1,"v":""},{"id":2,"v":None},{"id":3,"v":"y"}]
p = e.profile_table(dirty)
g = e.gate_quality(dirty)
print("L01 profile:", p["row_count"], "dup", p["dup_ratio"], "null", p["null_ratio"])
print("L01 gate:", g["grade"], [d for d in g["checks"] if not d["ok"]])
g2 = e.gate_quality([{"id":1,"v":"x"},{"id":2,"v":"y"}])
print("L01 clean gate:", g2["grade"])

inc = e.incremental_conservation([{"id":1,"v":1},{"id":2,"v":2}], [{"id":2,"v":9},{"id":3,"v":3}])
print("L01 incremental:", inc["conserved"], inc["base_count"], inc["inserted_count"], inc["target_count"], inc["expected_count"])

c = DataEngIntentCompiler()
ents = c.extract_entities("把 `orders` 和 dwd_orders 最近 30 天增量做成看板，2 小时内要新鲜，空值率<=0.05")
print("L02 entities:", ents["tables"], ents["window_days"], ents["sla_hours"], ents["mode"], ents["destination"], ents["thresholds"])
dag = c.compile_intent("把 `orders` 和 dwd_orders 最近 30 天增量做成看板，2 小时内要新鲜")
print("L02 topo:", dag["topological_order"], "levels", dag["parallel_levels"])
print("L02 critical:", dag["critical_path"], dag["critical_path_h"], "total", dag["total_effort_h"], "mandays", dag["total_man_days"])
cyc = c.topological_order(["a","b","c"], [{"from":"a","to":"b"},{"from":"b","to":"c"},{"from":"c","to":"a"}])
print("L02 cycle detect:", cyc["acyclic"], cyc["cycle_nodes"])

h = DataEngReflexiveHealer()
for bad in ["密码=abc123 连 jdbc:postgresql://prod", "直接回填 orders 表", "给出 p 值 0.03 的增长建议", "直接退款 500 元"]:
    try:
        h.audit_redlines(bad); print("L03 NOT BLOCKED:", bad)
    except ValueError as ex:
        print("L03 blocked:", str(ex)[:50])
print("L03 clean:", h.audit_redlines("SELECT * FROM orders WHERE dt='2026-01-01'")["ok"])
healed = h.heal_artifact({"tbl":"orders","father_table":"src","conn_id":"c1"})
print("L03 healed:", healed["mapped"], healed["filled"], healed["missing"], healed["needs_revalidation"])

calls = {"n":0}
def flaky(p):
    calls["n"] += 1
    if calls["n"] < 3:
        raise KeyError("missing required field owner")
    return {"ok": True, "attempt": calls["n"]}
rr = h.run_with_reflection(flaky, {"tbl":"orders"})
print("L03 reflection retry:", rr["ok"], rr["attempts"], [x["category"] for x in rr["reflections"]])

def always_bad(p): raise KeyError("missing required")
rr2 = h.run_with_reflection(always_bad, {"tbl":"x"}, max_attempts=3)
print("L03 bounded retry:", rr2["ok"], rr2["attempts"], len(rr2["reflections"]))
