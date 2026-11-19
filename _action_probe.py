# -*- coding: utf-8 -*-
import re, glob, os
base = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"
pat = re.compile(r'add_parser\(\s*"([^"]+)"')
key = re.compile(r'"([a-z0-9_]+)"\s*:')
hits = []
for f in glob.glob(os.path.join(base, "r*", "skills", "*.py")):
    s = open(f, encoding="utf-8", errors="replace").read()
    for a in pat.findall(s):
        if not re.fullmatch(r"[a-z0-9_]+", a):
            hits.append((os.path.relpath(f, base), a))
print("non-word add_parser actions:", hits)
# also ACTIONS dict keys with hyphen
hits2 = []
for f in glob.glob(os.path.join(base, "r*", "skills", "*.py")):
    s = open(f, encoding="utf-8", errors="replace").read()
    m = re.search(r"^ACTIONS\s*=\s*\{([\s\S]*?)\n\}", s, re.M)
    if m:
        for k in re.findall(r'"([^"]+)"\s*:', m.group(1)):
            if not re.fullmatch(r"[a-z0-9_]+", k):
                hits2.append((os.path.relpath(f, base), k))
print("non-word ACTIONS keys:", hits2)
