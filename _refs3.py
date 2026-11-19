# -*- coding: utf-8 -*-
import os, glob, collections
BASE = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"
os.chdir(BASE)
py = [p for p in glob.glob("**/*.py", recursive=True)
      if not p.startswith("workspace") and "__pycache__" not in p
      and "_archive" not in p]
texts = {p: open(p, encoding="utf-8", errors="replace").read() for p in py}

def refs(name):
    return [p for p, t in texts.items() if name in t]

groups = ["configs", "datasets", "knowledge", "pipelines", "projects",
          "evals", "fixtures", "examples"]
zero = collections.Counter()
one = collections.Counter()
rows = []
for g in groups:
    for f in sorted(glob.glob(f"{g}/**/*", recursive=True)):
        if not os.path.isfile(f):
            continue
        b = os.path.basename(f)
        h = refs(b)
        rows.append((f, b, len(h), h))
        if len(h) == 0:
            zero[g] += 1
        else:
            one[g] += 1
print("files", len(rows))
print("zero", dict(zero), "nonzero", dict(one))
for f, b, n, h in rows:
    if n:
        print(f"{n}\t{f}\t{h[:2]}")
