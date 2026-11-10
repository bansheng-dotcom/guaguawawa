import sys, os
sys.path.insert(0, os.getcwd())
from engines.reflexive_healer import DataEngReflexiveHealer
h = DataEngReflexiveHealer()
calls = {"n":0}
def flaky(p):
    calls["n"] += 1
    if calls["n"] < 3: raise KeyError("missing required field owner")
    return {"ok": True, "attempt": calls["n"]}
rr = h.run_with_reflection(flaky, {"tbl":"orders"})
print("retry ok:", rr["ok"], "attempts:", rr["attempts"], "refl n:", len(rr["reflections"]))
print("cats:", [x.get("category") for x in rr["reflections"] if x.get("category")])
def always_bad(p): raise KeyError("missing required")
rr2 = h.run_with_reflection(always_bad, {"tbl":"x"}, max_attempts=3)
print("bounded:", rr2["ok"], rr2["blocked"], rr2["attempts"], "err:", rr2["error"][:40])
def redline(p): raise ValueError("[REDLINE BLOCKED] R18-RL-01 凭据入工件")
rr3 = h.run_with_reflection(redline, {"tbl":"x"})
print("redline short-circuit:", rr3["ok"], rr3["blocked"], rr3["attempts"])
