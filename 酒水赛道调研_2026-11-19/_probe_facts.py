# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团\workspace\seasoning_v3_2026-11-19")
spec = importlib.util.spec_from_file_location("sf", ROOT / "facts.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print("META keys:", list(m.META))
print("KPI:", m.KPI[:2])
print("SUMMARY:", m.SUMMARY[:1])
s = m.SECTIONS[0]
print("SECTION keys:", list(s))
for k, v in s.items():
    if isinstance(v, (str, int)):
        print(" ", k, "=", str(v)[:120])
print("n sections:", len(m.SECTIONS), "sources:", len(m.SOURCES))
print("SOURCES row:", m.SOURCES[0])
print("ACTIONS row:", m.ACTIONS[0])
print("FILES:", m.FILES[:2])
