# -*- coding: utf-8 -*-
"""批量接入 REP-001 报告引擎 + 修复 agents 包导入（可重复执行，幂等）。

做四件事，全部是**结构化文本替换**，执行后会打印逐文件 diff 摘要供人工复核：
  1. 在 `from __future__ import annotations` 之后插入仓库根 sys.path 引导块；
  2. `from core import ... report_bridge` → 改为 `from agents.shared import role_runtime`；
  3. `report_bridge.emit(` → `role_runtime.emit(`；
  4. 报告调用补 `input_path=<本次输入文件>`，让报告页脚带上 SHA256 可复算证据。

用法：
    python agents/scripts/upgrade/apply_report_engine.py --dry-run
    python agents/scripts/upgrade/apply_report_engine.py
"""
from __future__ import annotations

import os
import re
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}  # 用户指定 R06 跳过（它是原型基准）

BOOT = '''
# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)
'''

IMPORT_PATTERNS = [
    ("from core import protocol, registry, runner, workspace, report_bridge",
     "from core import protocol, registry, runner, workspace"),
    ("from core import protocol, workspace, report_bridge",
     "from core import protocol, workspace"),
    ("from core import protocol, report_bridge",
     "from core import protocol"),
    ("from core import report_bridge",
     "from agents.shared import role_runtime"),
]


def role_dirs():
    for name in sorted(os.listdir(AGENTS)):
        p = os.path.join(AGENTS, name)
        if (os.path.isdir(p) and len(name) > 3 and name[0] == "r"
                and name[1:3].isdigit() and name[3] == "-" and name not in SKIP):
            yield p


def patch_source(src: str, var: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    out = src

    if "_REPO_ROOT" not in out:
        marker = "from __future__ import annotations"
        if marker in out:
            out = out.replace(marker, marker + "\n" + BOOT, 1)
            notes.append("+bootstrap")

    replaced_import = False
    for old, new in IMPORT_PATTERNS:
        if old in out:
            out = out.replace(old, new, 1)
            if old != new:
                notes.append(f"import: {old} -> {new}")
            replaced_import = True
            break

    if re.search(r"^\s*from core import .*report_bridge", out, re.M):
        notes.append("!! 未匹配的 report_bridge import，请人工确认")

    if replaced_import and "from agents.shared import role_runtime" not in out:
        anchor = "from core import"
        idx = out.find(anchor)
        while idx != -1:
            eol = out.find("\n", idx)
            line = out[idx:eol]
            if "protocol" in line or "workspace" in line or "registry" in line:
                out = out[:eol] + "\nfrom agents.shared import role_runtime  # REP-001 报告引擎" + out[eol:]
                notes.append("+role_runtime import")
                break
            idx = out.find(anchor, eol)

    if "report_bridge.emit(" in out:
        out = out.replace("report_bridge.emit(", "role_runtime.emit(")
        notes.append("report_bridge.emit -> role_runtime.emit")

    if "role_runtime.emit(" in out and "input_path=" not in out:
        pattern = re.compile(r"out_dir=out_dir,(\s*)md_name=")
        if pattern.search(out):
            out = pattern.sub(lambda m: f"out_dir=out_dir, input_path={var},{m.group(1)}md_name=",
                              out, count=1)
            notes.append(f"+input_path={var}")
        else:
            notes.append("!! emit 调用形态未匹配，未补 input_path")

    return out, notes


def main() -> int:
    dry = "--dry-run" in sys.argv
    changed = 0
    for d in role_dirs():
        path = os.path.join(d, "agent.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        var = "input_path" if "input_path = _first_input_file" in src else "in_file"
        new, notes = patch_source(src, var)
        if new == src:
            continue
        changed += 1
        print(f"[{'DRY' if dry else 'APPLY'}] {os.path.basename(d)}: " + " | ".join(notes))
        if not dry:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
    print(f"--- {changed} 个角色文件{'将被' if dry else '已'}修改")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
