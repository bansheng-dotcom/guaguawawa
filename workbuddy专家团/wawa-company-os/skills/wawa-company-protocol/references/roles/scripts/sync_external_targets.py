# -*- coding: utf-8 -*-
"""把「蛙蛙呱呱agents团」同步到外部安装位（WorkBuddy 插件 / Trae 技能目录）。

规则：
  * 只同步代码与文档；跳过运行期目录 workspace/ .cache/ projects/ __pycache__/ .git
  * 合并覆盖，不删除目标侧独有文件（插件自己的 skills/、bin/workspace/ 保留）
  * WorkBuddy 额外同步 agents/*.md（来自 agent-packs/agents）

用法：
  python scripts/sync_external_targets.py            # 全部同步
  python scripts/sync_external_targets.py --check    # 只比对，不写
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

SKIP_DIRS = {"workspace", ".cache", "__pycache__", ".pytest_cache", ".git",
             "projects", "node_modules", ".mypy_cache", "real_check"}
SKIP_FILES = {".DS_Store"}

WORKBUDDY = Path(r"C:\Users\18238\.workbuddy\plugins\marketplaces\my-experts\plugins\wawa-guagua-agents")
TRAE = Path(r"C:\Users\18238\.trae-cn\skills\wawa-guagua-agents")


def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if p.name in SKIP_FILES or p.suffix == ".pyc":
            continue
        yield rel


def sync_tree(src: Path, dst: Path, check: bool) -> tuple[int, int]:
    """返回 (新增/更新数, 跳过数)。"""
    dst.mkdir(parents=True, exist_ok=True)
    changed = same = 0
    for rel in iter_files(src):
        s, d = src / rel, dst / rel
        if d.exists() and filecmp.cmp(s, d, shallow=False):
            same += 1
            continue
        changed += 1
        if not check:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
    return changed, same


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    # 注意：不覆盖 WorkBuddy 的 agents/*.md —— 那是宿主侧生成物（138 行，含 hosts 专有字段），
    # 用仓库的 76 行版本覆盖会丢字段。它的代码入口是 bin/runtime。
    jobs = [
        ("WorkBuddy runtime", TEAM, WORKBUDDY / "bin" / "runtime"),
        ("Trae 技能目录", TEAM, TRAE),
    ]
    total_changed = 0
    for label, src, dst in jobs:
        if not dst.parent.exists():
            print(f"[skip] {label}: 目标不存在 {dst}")
            continue
        if not src.exists():
            print(f"[skip] {label}: 源不存在 {src}")
            continue
        changed, same = sync_tree(src, dst, args.check)
        total_changed += changed
        flag = "需同步" if args.check else "已同步"
        print(f"[{label}] {flag}：变更 {changed} 个，已一致 {same} 个 → {dst}")

    print(f"\n合计变更 {total_changed} 个文件" + ("（--check 未写入）" if args.check else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
