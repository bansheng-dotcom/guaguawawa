# -*- coding: utf-8 -*-
"""项目边界门禁：专家团里不许出现项目资产。

判定原则（和 §7.4 一致）：团内不能出现「能指向真实委托」的项目文件组合。
本脚本只查**结构性证据**，不做关键词扫描（关键词扫描误报高、易被绕过）：

    FAIL  TEAM/projects/           项目目录
    FAIL  TEAM/{briefs,cards,claims,artifacts,report}/  项目过程目录
    FAIL  TEAM/**/project.yaml     项目元数据
    FAIL  TEAM/**/claims_*.json    合并后的 claims（含项目数据）
    FAIL  TEAM/report/report.html  成品报告

`baselines/ examples/ evals/ tests/ fixtures/ samples/ docs/` 是夹具/文档，
允许出现 claims.json / report.html；但它们必须在这些目录内。

用法：
    python scripts/check_project_boundary.py [--json]
退出码：0=通过，1=有越界。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

#: 夹具与文档目录：允许放样例 claims/report（测试需要）
FIXTURE_ROOTS = {"baselines", "examples", "evals", "tests", "fixtures",
                 "samples", "docs", "agent-packs"}
#: 团内不允许出现的项目过程目录（根级）
FORBIDDEN_DIRS = ("projects", "briefs", "cards", "claims", "artifacts", "report")


def _rel(p: Path) -> str:
    return p.relative_to(TEAM).as_posix()


def _under_fixture(p: Path) -> bool:
    try:
        first = p.relative_to(TEAM).parts[0]
    except ValueError:
        return False
    return first in FIXTURE_ROOTS


def scan() -> list[str]:
    bad: list[str] = []
    for name in FORBIDDEN_DIRS:
        d = TEAM / name
        if d.is_dir() and any(d.iterdir()):
            bad.append(f"团内出现项目目录：{name}/（应迁到 <PROJECT_ROOT>）")

    for pattern in ("**/project.yaml", "**/claims_*.json"):
        for p in TEAM.glob(pattern):
            if _under_fixture(p):
                continue
            bad.append(f"团内出现项目文件：{_rel(p)}")

    for p in TEAM.glob("**/report/report.html"):
        if _under_fixture(p):
            continue
        bad.append(f"团内出现成品报告：{_rel(p)}")

    return bad


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    problems = scan()
    if "--json" in argv:
        print(json.dumps({"ok": not problems, "problems": problems},
                         ensure_ascii=False, indent=2))
    else:
        if problems:
            print("项目边界门禁 FAIL：")
            for p in problems:
                print(f"  - {p}")
        else:
            print("项目边界门禁 PASS：团内无项目资产")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
