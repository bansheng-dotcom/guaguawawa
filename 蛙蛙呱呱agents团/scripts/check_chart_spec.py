# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
from core.chart_spec import errors


def charts(mod):
    out = []
    if mod.get("chart"):
        out.append(mod["chart"])
    out.extend(mod.get("charts") or [])
    return out


def check(path):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = []
    for m in p.get("modules") or []:
        for c in charts(m):
            e = errors(c)
            if e:
                bad.append((m.get("id"), c.get("title", ""), e))
    return bad


for arg in sys.argv[1:]:
    bad = check(arg)
    print(arg, "PASS" if not bad else f"FAIL {bad}")
