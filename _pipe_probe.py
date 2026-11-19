# -*- coding: utf-8 -*-
import json, glob, os, collections
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sigs = {}
for f in sorted(glob.glob("pipelines/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    sig = tuple((s.get("skill"), tuple(s.get("args") or [])) for s in d["steps"] if s.get("type") == "skill")
    sigs[f] = sig
    print(f, "steps", len(d["steps"]), "skills", len(sig))
seen = collections.defaultdict(list)
for f, s in sigs.items():
    seen[s].append(f)
for s, fs in seen.items():
    if len(fs) > 1:
        print("DUP", fs)
