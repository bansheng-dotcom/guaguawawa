# -*- coding: utf-8 -*-
import glob, os
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
for f in sorted(glob.glob("knowledge/frameworks/*.md")) + sorted(glob.glob("knowledge/playbooks/*.md")):
    t = open(f, encoding="utf-8").read()
    print(f, "chars", len(t), "lines", t.count("\n"))
