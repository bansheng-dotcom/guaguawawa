# -*- coding: utf-8 -*-
import json, glob, os, sys, collections
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, os.getcwd())

kinds = collections.Counter()
per_skill = collections.Counter()
fields = collections.Counter()
total = 0
for f in sorted(glob.glob("evals/analysis/*/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    per_skill[d.get("skill")] += 1
    for k, v in (d.get("expect") or {}).items():
        total += 1
        fields[k.split(".")[0]] += 1
        if isinstance(v, dict):
            kinds[",".join(v)] += 1
        else:
            kinds["scalar:" + type(v).__name__] += 1
print("cases", len(glob.glob("evals/analysis/*/*.json")), "skills", len(per_skill))
print("expectations", total)
print("expect kinds", kinds.most_common())
print("per skill", per_skill.most_common())

# consult eval in-memory
import importlib.util
spec = importlib.util.spec_from_file_location("rce", "scripts/run_consult_eval.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
tasks = m.load_tasks()
rows = []
for t in tasks:
    txt = m.load_answer(t["id"])
    if not txt.strip():
        rows.append({"id": t["id"], "status": "missing"})
        continue
    rows.append({"id": t["id"], "status": "scored", "scores": m.score_answer(txt)})
scored = [r for r in rows if r["status"] == "scored"]
print("consult tasks", len(tasks), "scored", len(scored), "missing", len(tasks) - len(scored))
print("mean", sum(r["scores"]["total"] for r in scored) / len(scored))
print("totals", [(r["id"], r["scores"]["total"]) for r in scored])
