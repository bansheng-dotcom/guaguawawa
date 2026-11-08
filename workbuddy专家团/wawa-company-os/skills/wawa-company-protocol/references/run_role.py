#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蛙蛙呱呱 · 零配置角色启动器（R09 收口内置，不改任何源 agent.py）。

用法（cwd 必须是 references/）：
    cd PKG/skills/wawa-company-protocol/references
    python3 run_role.py r04-watiaoci-reviewer manifest
    python3 run_role.py r06-wadeqing-analyst --help

作用：
  1. 把 references/ 与 references/agents/ 插入 sys.path，等价于手工设置
     PYTHONPATH=<references>;<references/agents>，因此无需配置环境变量；
     并把目标角色目录追加到 sys.path 末尾，兼容源脚本里依赖
     「cwd 为角色目录」的写法（如 r02 的 `from skills import SKILLS`）；
  2. 用 runpy.run_path(target, run_name="__main__") 执行目标角色的 agent.py。
     runpy 会把 __file__ 设为 target 的真实绝对路径，所以 agent.py 里的
     _REPO_ROOT = dirname(dirname(dirname(__file__))) 仍正确推得 references/，
     `from agents.shared...` / `from core import ...` 均可解析。

本文件只做路径引导与转发，不含任何业务逻辑，不修改任何源 agent.py。
"""
from __future__ import annotations

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 与实测成功的 PYTHONPATH 顺序一致：references 在前、references/agents 在后。
# 循环 insert(0) 后 HERE 位于 sys.path[0]。
for _p in (os.path.join(HERE, "agents"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python3 run_role.py <rXX-角色目录名> <子命令> [参数...]", file=sys.stderr)
        print("例:   python3 run_role.py r04-watiaoci-reviewer manifest", file=sys.stderr)
        return 2

    role, rest = sys.argv[1], sys.argv[2:]
    target = os.path.join(HERE, "roles", role, "agent.py")
    if not os.path.isfile(target):
        roles_dir = os.path.join(HERE, "roles")
        avail = sorted(
            d for d in os.listdir(roles_dir)
            if os.path.isfile(os.path.join(roles_dir, d, "agent.py"))
        ) if os.path.isdir(roles_dir) else []
        print("找不到角色入口: %s" % target, file=sys.stderr)
        print("可用角色(%d): %s" % (len(avail), ", ".join(avail)), file=sys.stderr)
        return 2

    # 兼容源脚本里依赖「cwd 为角色目录」的写法：追加角色目录到 sys.path 末尾，
    # 不抢占 references / references/agents 中 core、agents 包的解析优先级。
    role_dir = os.path.dirname(target)
    if role_dir not in sys.path:
        sys.path.append(role_dir)

    sys.argv = [target] + rest
    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
