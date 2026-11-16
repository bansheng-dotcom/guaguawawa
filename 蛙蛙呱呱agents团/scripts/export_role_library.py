# -*- coding: utf-8 -*-
"""把 20 个角色领域包导出成一份可读的 Markdown 书单 + 方法总表。

用法：
    python scripts/export_role_library.py --out <file.md>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import skill_bridge  # noqa: E402

ROLES = ROOT / "knowledge" / "roles"


def load() -> List[Dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8-sig"))
            for p in sorted(ROLES.glob("r*.json"))]


def build(roles: List[Dict[str, Any]]) -> str:
    L: List[str] = []
    L.append("# 20 角色领域书单与方法总表\n")
    L.append("> 每个角色：5 本书（中英各至少 1 本）、6 个方法（带公式）、6 个指标、"
             "4 类决策、3 个领先信号、4 个常见误判、6 个报告必备章节。")
    L.append("> 书是原料，方法才是可执行动作；每条方法都标了技能落点："
             "`角色.技能 动作`（exact/partial），没有对应技能的标「新增」。\n")
    L.append("## 总览\n")
    L.append("| 角色 | 能力域 | 书 | 方法 | 核心指标 |")
    L.append("|---|---|---:|---:|---|")
    for r in roles:
        L.append(f"| {r['role']} {r['name']} | {r['domain']} | {len(r['books'])} | "
                 f"{len(r['methods'])} | {'、'.join(r['kpis'][:4])} |")
    L.append("")
    for r in roles:
        L.append(f"\n---\n\n## {r['role']} {r['name']} · {r['domain']}\n")
        L.append("**书单**\n")
        L.append("| 书 | 作者（年） | 语言 | 核心概念 | 贡献的动作 |")
        L.append("|---|---|---|---|---|")
        for b in r["books"]:
            L.append(f"| {b['title']} | {b['author']}（{b['year']}） | "
                     f"{b['lang']} | {b['concept']} | {b['move']} |")
        L.append("\n**方法**（公式/算法 → 什么时候用）\n")
        for m in r["methods"]:
            sk = skill_bridge.info(r["role"], m["name"]) or {}
            where = (f" → `{sk.get('skill_role')}.{sk.get('skill')}"
                     f"{(' ' + sk['action']) if sk.get('action') else ''}`"
                     f"（{sk.get('fit')}）") if sk.get("fit") in ("exact", "partial") else " → 新增"
            L.append(f"- **{m['name']}**：`{m['formula']}` —— {m['when']}{where}")
        L.append("\n**指标**：" + "、".join(r["kpis"]))
        L.append("\n**决策**：" + "、".join(r["decisions"]))
        L.append("\n**领先信号**：" + "、".join(r["foresight"]))
        L.append("\n**常见误判**：")
        for f in r["failure_modes"]:
            L.append(f"- {f}")
        L.append("\n**报告必备章节**：" + "、".join(r["report_sections"]))
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    roles = load()
    text = build(roles)
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {p} ({len(roles)} roles, {len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
