# -*- coding: utf-8 -*-
import json, glob, os, sys, collections
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, os.getcwd())
from core import skill_graph

rows = skill_graph.load()
r06 = sorted(r["skill"] for r in rows if r["role"] == "r06")
ev = {json.load(open(f, encoding="utf-8"))["skill"] for f in glob.glob("evals/analysis/*/*.json")}
print("r06 skills", len(r06), r06)
print("covered", sorted(ev))
print("NOT covered", [s for s in r06 if s not in ev])
print("covered not in r06", [s for s in ev if s not in r06])
# funnel case skill
for f in glob.glob("evals/analysis/funnel/*.json"):
    print(f, json.load(open(f, encoding="utf-8"))["skill"])
