# -*- coding: utf-8 -*-
"""报告层隔离门禁：报告层只读证据，不读知识库、不读 expert_brief。

为什么必须隔离：brief 是「怎么想」，证据是「是什么」。一旦报告层能读 brief，
就会拿 brief 里的问题当结论、拿行业框架补事实，最后写出一份「听起来专业、
但每个数字都没有出处」的报告——这是本团最贵的一种失败。

检查范围：报告产线全部模块——`core/report_*.py` 与 `core/report*/**/*.py`。
禁止出现：
    shared.knowledge / knowledge_base / expert_brief / brief_ref / brief_version
    from core.project import ...
说明：`report_roles.py` 里的能力名 `knowledge` 是历史标签，不在这条红线内
（只查 import 与 brief 字段，不做裸词扫描）。

用法：
    python scripts/check_report_isolation.py [--json]
退出码：0=隔离成立，1=报告层越界。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
CORE = TEAM / "core"

#: 报告层路径：平铺模块 + 已成型/将来成型的子包都要覆盖，
#: 否则文件一挪进 core/report/ 或 core/cards/ 就会“扫不到 = 永远 PASS”。
REPORT_GLOBS = ("report_*.py", "report/**/*.py",
                "report_kernel/**/*.py", "report_theme/**/*.py",
                "cards/report_dispatch.py")

PATTERNS = [
    (re.compile(r"\bshared\.knowledge\b"), "import shared.knowledge"),
    (re.compile(r"\bknowledge_base\b"), "knowledge_base"),
    (re.compile(r"\bexpert_brief\b"), "expert_brief"),
    (re.compile(r"\bbrief_ref\b"), "brief_ref"),
    (re.compile(r"\bbrief_version\b"), "brief_version"),
    (re.compile(r"from\s+core\.project\s+import|from\s+core\s+import\s+project\b"),
     "import core.project"),
]


def report_paths() -> list[Path]:
    out: set[Path] = set()
    for pat in REPORT_GLOBS:
        out.update(p for p in CORE.glob(pat) if p.is_file())
    return sorted(out)


def scan(paths: list[Path] | None = None) -> list[str]:
    bad: list[str] = []
    for p in (report_paths() if paths is None else paths):
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            bad.append(f"{p.name}: 读取失败 {exc}")
            continue
        for i, line in enumerate(lines, 1):
            code = line.split("#", 1)[0]
            for pat, label in PATTERNS:
                if pat.search(code):
                    bad.append(f"{p.name}:{i} 报告层出现 {label}：{line.strip()[:70]}")
    return bad


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    problems = scan()
    if "--json" in argv:
        print(json.dumps({"ok": not problems, "problems": problems},
                         ensure_ascii=False, indent=2))
    elif problems:
        print("报告层隔离门禁 FAIL：")
        for p in problems:
            print(f"  - {p}")
    else:
        print("报告层隔离门禁 PASS：core/report* 不读知识库、不读 brief")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
