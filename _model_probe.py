# -*- coding: utf-8 -*-
import json, os, sys
os.chdir(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, os.getcwd())
from core import report_model

m = report_model.build()
i = m["integrity"]
print("bad dims:", i["dimensions_with_unknown_method"])
print("orphan methods:", i["methods_used_by_no_dimension"])
print("chart types not in config:", i["chart_types_not_in_config"])
print("role sections without rule:", i["role_sections_without_chart_rule"])
specs = json.load(open("configs/role_report_specs.json", encoding="utf-8"))
cfg = json.load(open("configs/chart_type_by_question.json", encoding="utf-8"))
secs = {s for v in specs.values() for s in v["sections"]}
print("sections total", len(secs), "in cfg", sorted(secs & set(cfg)), "missing", sorted(secs - set(cfg)))
print("cfg keys not used as any section", sorted(set(cfg) - secs))
