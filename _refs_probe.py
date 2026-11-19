# -*- coding: utf-8 -*-
import os, glob, json, re
BASE = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"
os.chdir(BASE)

py_live = [p for p in glob.glob("**/*.py", recursive=True)
           if not p.startswith("workspace") and "__pycache__" not in p
           and "_archive" not in p and ".pytest_cache" not in p]
texts = {p: open(p, encoding="utf-8", errors="replace").read() for p in py_live}

def refs(name):
    hits = []
    for p, t in texts.items():
        if name in t:
            hits.append(p)
    return hits

groups = ["configs", "datasets", "knowledge", "pipelines", "projects", "evals",
          "fixtures", "examples"]
rows = []
for g in groups:
    for f in sorted(glob.glob(f"{g}/**/*", recursive=True)):
        if not os.path.isfile(f):
            continue
        b = os.path.basename(f)
        # a file is "referenced" if its basename appears in live py, OR its parent dir is globbed
        rh = refs(b)
        rows.append((f, b, len(rh), rh[:2]))
print("total files", len(rows))
zero = [r for r in rows if r[2] == 0]
print("zero-basename-ref files", len(zero))
import collections
c = collections.Counter(r[0].split("/")[0] for r in zero)
print(c)
for r in zero:
    print("  DEAD?", r[0], r[1])
