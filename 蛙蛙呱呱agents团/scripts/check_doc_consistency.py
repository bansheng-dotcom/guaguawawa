# -*- coding: utf-8 -*-
"""文档一致性检查：报告的产线版本与步骤在多个入口文档里必须一致。

背景（2026-11-23）：`SKILL.md` 写着「报告产线 v5（面板优先）」，
`README.md` 写着「v13（拆卡线唯一）」——两处更新时间相同、版本与步骤却不同，
读者按哪份做都可能是错的。

检查三件事：
    D1 版本号：所有提到「报告产线 vN」的文档，N 必须相同
    D2 步骤齐：SKILL / README 必须都出现 probe / --issue / plan/supply.json / collect / run-line
    D3 无废弃词：不许再出现「面板优先」（v5 的旧模型）

用法：
    python scripts/check_doc_consistency.py          # 不过返回 1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ("SKILL.md", "README.md", "docs/_entry/REPORT-BRIDGE-GUIDE.md",
        "REPORT-STANDARD.md", "docs/REPORT-LINES.md", "使用指南.md")
REQUIRED_STEPS = ("report probe", "--issue", "plan/supply.json",
                  "report collect", "report run-line")
BANNED = ("面板优先",)

VER_RE = re.compile(r"报告产线 v(\d+)")


def _txt(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def main() -> int:
    problems = []

    # D1 版本号一致
    versions = {}
    for rel in DOCS:
        for m in VER_RE.finditer(_txt(rel)):
            versions.setdefault(m.group(1), []).append(rel)
    if len(versions) > 1:
        problems.append("D1 版本号不一致：%s" % {
            v: sorted(set(f)) for v, f in versions.items()})
    elif not versions:
        problems.append("D1 没有文档写「报告产线 vN」")

    # D2 入口文档步骤齐
    for rel in ("SKILL.md", "README.md"):
        s = _txt(rel)
        if not s:
            problems.append("D2 %s 不存在" % rel)
            continue
        miss = [k for k in REQUIRED_STEPS if k not in s]
        if miss:
            problems.append("D2 %s 缺步骤：%s" % (rel, miss))

    # D3 无废弃词
    for rel in DOCS:
        s = _txt(rel)
        for w in BANNED:
            if w in s:
                problems.append("D3 %s 仍含废弃词「%s」" % (rel, w))

    ver = sorted(versions)[-1] if versions else "?"
    if problems:
        print("FAIL 文档不一致（%d 项）" % len(problems))
        for p in problems:
            print("  -", p)
        return 1
    print("PASS 文档一致（报告产线 v%s，%d 份入口文档同版）" % (ver, len(DOCS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
