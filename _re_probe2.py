# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
from pathlib import Path
from core import skill_graph as sg

f = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团\r04-watiaoci-reviewer\skills\s01_artifact.py")
print(sg._parse_skill(f))
src = f.read_text(encoding="utf-8", errors="replace")
print("ACTIONS search:", bool(sg._ACTIONS.search(src)))
if sg._ACTIONS.search(src):
    print(repr(sg._ACTIONS.search(src).group(1)[:80]))
    print(sg._ACTION_KEY.findall(sg._ACTIONS.search(src).group(1)))
