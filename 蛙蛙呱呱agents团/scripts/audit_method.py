# -*- coding: utf-8 -*-
"""方法包审计：检查 rXX/references/method-pack.md 是否达到 6 段 + 可检查项。

100 分制，但量的是「方法」不是「结构」：
  决策问题 15 / 问题树 20 / 假设与证伪 20 / 证据分级 15 / 方法与陷阱 20 / 输出契约 10
用法：
  python scripts/audit_method.py r05        # 单角色
  python scripts/audit_method.py --all      # 全角色（缺包记 0 分）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECTIONS = [
    ("决策问题", 15, [r"决策问题|决策", r"决策者|谁.*拍板", r"成功标准|判断标准", r"非目标|不回答|不做"]),
    ("问题树", 20, [r"问题树|Issue Tree|MECE", r"分支|支路", r"\|\s*分支\s*\|", r"关键分支|critical|优先"]),
    ("假设与证伪", 20, [r"假设", r"证伪|杀死标准|推翻", r"竞争解释|替代解释", r"支持证据|反对证据"]),
    ("证据分级", 15, [r"A 级|A级|\|\s*A\s*\|", r"B 级|B级|\|\s*B\s*\|", r"C 级|C级|\|\s*C\s*\|", r"缺口|回溯|口径"]),
    ("方法与陷阱", 20, [r"基线|对照|匹配", r"分解|归因", r"敏感性|区间|情景", r"陷阱|误用|反模式"]),
    ("输出契约", 10, [r"claim|结论", r"evidence|来源", r"confidence|置信|区间", r"falsifier|证伪"]),
]


def score_file(p: Path) -> tuple[int, list[str]]:
    if not p.exists():
        return 0, [f"缺文件 {p}"]
    text = p.read_text(encoding="utf-8", errors="replace")
    total, notes = 0, []
    for name, weight, pats in SECTIONS:
        hit = sum(1 for pat in pats if re.search(pat, text, re.I))
        part = round(weight * hit / len(pats))
        total += part
        if hit < len(pats):
            notes.append(f"{name} {part}/{weight}（缺 {len(pats)-hit} 项）")
    return total, notes


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--all":
        rows = []
        for d in sorted(ROOT.glob("r[0-9][0-9]-*")):
            p = d / "references" / "method-pack.md"
            s, notes = score_file(p)
            rows.append((d.name, s, notes))
        rows.sort(key=lambda r: -r[1])
        print(f"{'角色':<28}{'得分':>5}  缺口")
        for name, s, notes in rows:
            print(f"{name:<28}{s:>5}  {'; '.join(notes) if notes else '满分'}")
        have = sum(1 for _, s, _ in rows if s > 0)
        print(f"\n有方法包 {have}/{len(rows)}；平均 {sum(s for _, s, _ in rows)/len(rows):.1f}")
        return

    role = args[0] if args else "r05"
    d = next((p for p in ROOT.glob(f"{role}-*") if p.is_dir()), None)
    if not d:
        raise SystemExit(f"找不到角色 {role}")
    s, notes = score_file(d / "references" / "method-pack.md")
    print(f"{d.name}: {s}/100")
    for n in notes:
        print("  -", n)
    if s < 80:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
