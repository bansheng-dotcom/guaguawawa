# -*- coding: utf-8 -*-
"""校验「领域方法 → 现有技能」的接入率，防止另起一套。

判据：
1. 20 个角色、120 条方法全部有落点（exact / partial / new 之一）；
2. 映射到的技能与动作在 `knowledge/skills_inventory.json` 里真实存在；
3. 接入率（exact+partial）≥95%；
4. exact（技能已做同一件事）≥50 条；
5. new（必须新增）≤5 条，且每条写明理由；
6. 每个角色 6 条方法都有落点。

用法：python scripts/check_skill_integration.py [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import skill_bridge  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_skill_integration")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    c = skill_bridge.coverage()
    roles = skill_bridge.skill_map().get("roles", {})
    errs = []
    if c["total"] != 120:
        errs.append(f"方法总数 {c['total']} != 120")
    if c["missing"]:
        errs.extend(c["missing"][:10])
    if c["coverage_rate"] < 0.95:
        errs.append(f"接入率 {c['coverage_rate']:.0%} < 95%")
    if c["counts"].get("exact", 0) < 50:
        errs.append(f"exact {c['counts'].get('exact', 0)} < 50")
    if c["counts"].get("new", 0) > 5:
        errs.append(f"new {c['counts'].get('new', 0)} > 5")
    for role, items in roles.items():
        if len(items) < 6:
            errs.append(f"{role} 只映射了 {len(items)} 条方法")
    if a.json:
        print(json.dumps({"coverage": c, "errors": errs}, ensure_ascii=False, indent=2))
    else:
        print(f"方法 {c['total']} 条 | exact {c['counts'].get('exact', 0)} / "
              f"partial {c['counts'].get('partial', 0)} / new {c['counts'].get('new', 0)} "
              f"| 接入率 {c['coverage_rate']:.0%}")
        for role in sorted(roles):
            x = c["by_role"].get(role, {})
            print(f"  {role}  exact {x.get('exact', 0):>2}  "
                  f"partial {x.get('partial', 0):>2}  new {x.get('new', 0):>2}")
        if errs:
            print("\nFAIL")
            for e in errs:
                print("  -", e)
        else:
            print("\nPASS：全部方法都有落点，且技能/动作真实存在")
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
