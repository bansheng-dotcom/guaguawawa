# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
p = r"D:\蛙蛙呱呱\酒水赛道调研_2026-11-19\out\_flowtest.html"
h = open(p, encoding="utf-8").read()
print("@page", h.count("@page"), 'class="page', h.count('class="page'),
      "flow-block", h.count("flow-block"), "svg", h.count("<svg"))

from core import report_quality
r = report_quality.audit(p)
print("quality ok", r["ok"], "score", r["score"], "sections", r["sections"])
for c in r["checks"]:
    if not c["ok"]:
        print(" fail", c["id"], c.get("value"), c.get("need"))

sys.path.insert(0, r"D:\蛙蛙呱呱\蛙蛙呱呱agents团\scripts")
try:
    from check_report_presentation import check_html
    from pathlib import Path
    pres = check_html(Path(p))
    print("presentation ok", pres.get("ok"), "violations", [v.get("id") for v in pres.get("violations") or []])
except Exception as e:
    print("presentation error", type(e).__name__, e)
