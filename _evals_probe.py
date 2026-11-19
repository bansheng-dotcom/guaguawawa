# -*- coding: utf-8 -*-
import json, os, glob
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
for f in ["evals/consulting/baseline.json", "evals/results/eval_20261117.json",
          "evals/consulting/labels_draft.json"]:
    d = json.load(open(f, encoding="utf-8"))
    print("##", f, list(d))
    print(json.dumps(d.get("summary") or d.get("note"), ensure_ascii=False)[:500])
    rows = d.get("rows") or d.get("labels") or []
    print("rows", len(rows))
    for r in rows[:4]:
        print("  ", json.dumps(r, ensure_ascii=False)[:220])
print()
print("answers:", sorted(os.path.basename(p) for p in glob.glob("evals/answers/*")))
