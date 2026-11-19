# -*- coding: utf-8 -*-
import glob, os
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
py = [p for p in glob.glob("**/*.py", recursive=True)
      if not p.startswith("workspace") and "__pycache__" not in p
      and "_archive" not in p]
for name in ["abtest_regression.json", "3c.md", "crm.json", "M-STR-001.json", "r06.yaml"]:
    hits = [p for p in py if name in open(p, encoding="utf-8", errors="replace").read()]
    print(name, "->", len(hits), hits[:3])
print("py files", len(py))
