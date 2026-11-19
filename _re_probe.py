# -*- coding: utf-8 -*-
import re, sys, json
p = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团\r04-watiaoci-reviewer\skills\s01_artifact.py"
src = open(p, encoding="utf-8", errors="replace").read()
print(repr(src[:60]))
NAME = re.compile(r'^NAME\s*=\s*"([^"]+)"', re.M)
print("NAME", NAME.search(src))
ACT = re.compile(r"^ACTIONS\s*=\s*\{([\s\S]*?)\n\}", re.M)
m = ACT.search(src)
print("ACT", bool(m))
if m:
    print(repr(m.group(1)[:120]))
    print("keys", re.findall(r'"([a-z0-9_]+)"\s*:', m.group(1)))
