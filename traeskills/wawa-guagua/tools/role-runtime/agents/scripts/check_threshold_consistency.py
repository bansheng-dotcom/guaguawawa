#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨卡阈值一致性检查：防止同一概念在不同 SKILL.md 里被定义成不同数值。

为什么需要它：
    技能库长到几十张后，「地板线 15%」「一致率 80%」「抽样 3 项」这类共享数值
    会被多张卡各自写一遍。改一处、其余不跟 —— 模型读到两张卡会拿到两个答案。
    本脚本以 `shared-standards` §4 为唯一出处，扫描所有 SKILL.md 找冲突。

判定方式（只认阈值上下文，不认随手出现的数字）：
    每个概念用带捕获组的正则，只匹配「概念词 + 紧跟的数字」，
    如 `一致率 ≥80%` 会抓 80，而 `EX-10 | 双评就发布` 不会抓 10。
    抓到值与权威值不一致即记为冲突。

用法：
    python scripts/check_threshold_consistency.py            # 人读报告
    python scripts/check_threshold_consistency.py --json
    python scripts/check_threshold_consistency.py --verbose  # 显示命中数

退出码：0 无不一致 / 1 有不一致 / 2 环境问题
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = os.path.join(ROOT, "r04-watiaoci-reviewer", "references",
                    "capabilities", "shared-standards")

# (概念, 带 (?P<v>...) 的正则, 权威值, 说明)
# 只收录「跨 ≥2 张卡」的概念；领域内独有数值不在此列。
CANON = [
    ("毛利率地板",
     r"(?:毛利率?[^。\n]{0,14}?|续约价低于|折后毛利[^。\n]{0,10}?)\s*地板[^。\n]{0,14}?(?P<v>\d{1,3})\s*%"
     r"|地板[^。\n]{0,10}?(?P<v2>\d{1,3})\s*%[^。\n]{0,8}毛利",
     "15", "毛利率地板 15%（含平台费与退货损耗后）"),

    ("双评一致率",
     r"一致率[^。\n]{0,14}?[≥⩾>]=?\s*(?P<v>\d{1,3})\s*%",
     "80", "双评一致率门槛 80%"),

    ("kappa 门槛",
     r"kappa[^。\n]{0,14}?[≥⩾>]=?\s*(?P<v>\d(?:\.\d)?)",
     "0.6", "≥3 人时 kappa ≥0.6"),

    ("评审抽样数",
     r"抽\s*(?P<v>\d{1,2})\s*项",
     "3", "评审反查抽 3 项"),

    ("双评最少样本",
     r"[≥⩾>]=?\s*(?P<v>\d{1,3})\s*个样本",
     "10", "双评至少 10 个样本"),

    ("图表欺骗操作数",
     r"(?:欺骗性操作|红线)[^。\n]{0,10}?[≥⩾>]?=?[^\d\n]{0,6}(?P<v>\d{1,2})\s*个",
     "0", "底线类指标归零"),
]


def packs() -> list:
    out = []
    for name in sorted(os.listdir(ROOT)):
        role = os.path.join(ROOT, name)
        caps = os.path.join(role, "references", "capabilities")
        if not os.path.isdir(caps):
            continue
        for cid in sorted(os.listdir(caps)):
            skill = os.path.join(caps, cid, "SKILL.md")
            if os.path.isfile(skill):
                out.append((cid, skill))
    return out


def line_of(text: str, pos: int) -> tuple:
    ln = text.count("\n", 0, pos) + 1
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return ln, text[start:end].strip()[:110]


def find_conflicts(text: str) -> list:
    """在给定文本里找冲突，返回 [(concept, canonical, found, line)]。"""
    out = []
    for concept, pattern, canon, _note in CANON:
        for m in re.finditer(pattern, text):
            val = m.groupdict().get("v") or m.groupdict().get("v2")
            if not val:
                continue
            norm = val.rstrip("0").rstrip(".") if "." in val else (val.lstrip("0") or "0")
            if val == canon or norm == canon:
                continue
            ln, _s = line_of(text, m.start())
            out.append((concept, canon, val, ln))
    return out


def self_test() -> int:
    """验证检查器既能放过一致值，也能抓到不一致值。"""
    good = (
        "| **地板** | 不可低于 | 毛利地板 15% |\n"
        "双评一致率 ≥80% 才可上线。\n"
        "抽 3 项反查。\n"
        "双评（≥10 个样本）。\n"
        "kappa ≥0.6 视为可判。\n"
        "EX-10 双评一致率 ≥80% 才算可判定。\n"   # 含编号 10，不应误报
    )
    bad = (
        "毛利地板 12% 即可。\n"                   # 毛利地板冲突（12≠15）
        "双评一致率 ≥65% 就上线。\n"              # 一致率冲突（65≠80）
        "抽 1 项反查即可。\n"                     # 抽样冲突（1≠3）
        "双评只需 ≥5 个样本。\n"                  # 样本冲突（5≠10）
    )
    cases = [
        ("一致值不应报警", good, 0),
        ("冲突值必须报警", bad, 4),
    ]
    print("阈值一致性检查器 · 自检")
    print("=" * 60)
    failures = 0
    for name, text, expect in cases:
        got = find_conflicts(text)
        ok = len(got) >= expect if expect else len(got) == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}：命中 {len(got)} 处（期望 {'≥' + str(expect) if expect else '0'}）")
        for c, canon, val, ln in got:
            print(f"         · {c}: {val}（权威 {canon}）L{ln}")
        if not ok:
            failures += 1
    print("=" * 60)
    if failures:
        print(f"[selftest] FAIL {failures}/{len(cases)}：检查器本身失效，CI 的绿灯不可信")
        return 1
    print(f"[selftest] PASS {len(cases)}/{len(cases)}：既不会误报编号，也能抓到真冲突")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="跨卡阈值一致性检查")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="自检：验证检查器真的能抓到冲突（防假绿）")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if args.self_test:
        return self_test()

    items = packs()
    if not items:
        print("[consistency] 找不到任何 SKILL.md", file=sys.stderr)
        return 2

    problems, hits_total = [], 0
    for cid, path in items:
        if os.path.abspath(path).startswith(os.path.abspath(BASE)):
            continue  # 基准卡本身是权威，不查
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        for concept, pattern, canon, note in CANON:
            for m in re.finditer(pattern, text):
                val = m.groupdict().get("v") or m.groupdict().get("v2")
                if not val:
                    continue
                hits_total += 1
                norm = val.rstrip("0").rstrip(".") if "." in val else val.lstrip("0") or "0"
                if val == canon or norm == canon:
                    continue
                ln, snippet = line_of(text, m.start())
                problems.append({"card": cid, "concept": concept, "line": ln,
                                 "canonical": canon, "found": val,
                                 "snippet": snippet, "note": note})
                if args.verbose:
                    print(f"  [文中] {cid} L{ln} {concept} = {val}（权威 {canon}）")

    if args.json:
        print(json.dumps({"packs": len(items), "matches": hits_total,
                          "problems": problems}, ensure_ascii=False, indent=2))
        return 1 if problems else 0

    print("跨卡阈值一致性检查（唯一出处：shared-standards §4）")
    print("=" * 74)
    print(f"扫描 SKILL.md {len(items)} 份｜阈值上下文命中 {hits_total} 处｜冲突 {len(problems)} 处")
    if problems:
        print()
        for p in problems:
            print(f"  [冲突] {p['card']}  第 {p['line']} 行  →  {p['concept']}")
            print(f"         权威值 {p['canonical']}｜文中 {p['found']}｜依据：{p['note']}")
            print(f"         > {p['snippet']}")
        print()
        print("修复：先改 shared-standards §4（若该变），再逐张改卡；")
        print("      或把该卡改为「见 shared-standards §4」，不复制数字。")
        return 1
    print("\n[OK] 无冲突：所有卡与 shared-standards 一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
