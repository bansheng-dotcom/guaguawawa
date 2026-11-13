# -*- coding: utf-8 -*-
"""为 20 角色接入统一元命令（report / test / logs）——幂等补丁脚本。

用法：
    python agents/scripts/upgrade/install_meta_commands.py --dry-run
    python agents/scripts/upgrade/install_meta_commands.py
"""
from __future__ import annotations

import os
import re
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}

HOOK_TPL = """
    _meta = role_runtime.handle_meta_command({expr}, ROLE)
    if _meta is not None:
        return _meta
"""


def role_dirs():
    for name in sorted(os.listdir(AGENTS)):
        p = os.path.join(AGENTS, name)
        if (os.path.isdir(p) and len(name) > 3 and name[0] == "r"
                and name[1:3].isdigit() and name[3] == "-" and name not in SKIP):
            yield p


def ensure_import(src: str) -> tuple[str, bool]:
    if "from agents.shared import role_runtime" in src:
        return src, False
    anchor = "\nimport argparse"
    if anchor in src:
        return src.replace(anchor, "\nfrom agents.shared import role_runtime  # 统一元命令/报告", 1), True
    return src, False


def insert_hook(src: str) -> tuple[str, str]:
    if "handle_meta_command" in src:
        return src, "已有"
    m = re.search(r"^def main\(([^)]*)\)[^:]*:\s*$", src, re.M)
    if not m:
        return src, "!! 未找到 main()"
    sig = m.group(1)
    start = m.end()
    tail = src[start:]
    lines = tail.split("\n")
    # 情况 A：函数体内已有 argv 归一化
    for i, line in enumerate(lines[:6]):
        if re.match(r"\s+argv = list\(sys\.argv", line) or re.match(r"\s+argv = sys\.argv", line):
            insert_at = start + len("\n".join(lines[: i + 1])) + 1
            return (src[:insert_at] + HOOK_TPL.format(expr="argv") + src[insert_at:],
                    "hook@argv")
    expr = ("list(sys.argv[1:] if argv is None else argv)" if "argv" in sig
            else "sys.argv[1:]")
    return src[:start] + HOOK_TPL.format(expr=expr) + src[start:], f"hook@{expr}"


def main() -> int:
    dry = "--dry-run" in sys.argv
    for d in role_dirs():
        path = os.path.join(d, "agent.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        new, added = ensure_import(src)
        new, note = insert_hook(new)
        if new == src:
            continue
        print(f"[{'DRY' if dry else 'APPLY'}] {os.path.basename(d)}: "
              f"import={'+1' if added else '='} | {note}")
        if not dry:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
