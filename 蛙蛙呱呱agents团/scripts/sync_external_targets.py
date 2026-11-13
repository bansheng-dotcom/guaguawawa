# -*- coding: utf-8 -*-
"""把「蛙蛙呱呱agents团」同步到外部安装位（WorkBuddy 插件 / Trae 技能目录）。

规则：
  * 只同步代码与文档；跳过运行期目录 workspace/ .cache/ projects/ __pycache__/ .git
  * 默认合并覆盖，不删除目标侧独有文件
  * `--prune`：目标侧严格镜像仓库（删除目标独有文件），仅对白名单内的镜像目标生效
  * WorkBuddy 额外同步 agents/*.md（来自 agent-packs/agents）

用法：
  python scripts/sync_external_targets.py              # 合并同步
  python scripts/sync_external_targets.py --check      # 只比对，不写
  python scripts/sync_external_targets.py --prune      # 镜像同步（会删目标侧多余文件）
  python scripts/sync_external_targets.py --prune --check   # 先看会删什么
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

SKIP_DIRS = {"workspace", ".cache", "__pycache__", ".pytest_cache", ".git",
             "projects", "node_modules", ".mypy_cache", "real_check"}
SKIP_FILES = {".DS_Store"}
# 镜像同步时，目标侧这些运行期目录一并清掉
RUNTIME_DIRS = ("workspace", "projects", ".cache", "__pycache__", ".pytest_cache",
                "node_modules", ".mypy_cache", "real_check")

WORKBUDDY = Path(r"C:\Users\18238\.workbuddy\plugins\marketplaces\my-experts\plugins\wawa-guagua-agents")
TRAE = Path(r"C:\Users\18238\.trae-cn\skills\wawa-guagua-agents")
# 历史遗留的第二个 Trae 安装位（无连字符，曾被 report_bridge 直接引用）；两处必须同源
TRAE_LEGACY = Path(r"C:\Users\18238\.trae-cn\skills\wawaguagua-agents")

# 允许 --prune 的镜像目标（防止误删宿主专有目录）
MIRROR_ALLOWED = {TRAE.resolve(), TRAE_LEGACY.resolve()}


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


def prune_tree(src: Path, dst: Path, check: bool) -> list[Path]:
    """删除目标侧独有文件（严格镜像），并清掉运行期目录。

    返回被删/将被删的相对路径（文件 + 运行期目录）。
    """
    src_rel = set(iter_files(src))
    extra = sorted((rel for rel in iter_files(dst) if rel not in src_rel))
    runtime = [d for d in RUNTIME_DIRS if (dst / d).exists()]
    if not check:
        for rel in extra:
            (dst / rel).unlink(missing_ok=True)
        # 清掉因此变空的目录（自底向上）
        for d in sorted((p for p in dst.rglob("*") if p.is_dir()),
                        key=lambda p: -len(p.parts)):
            try:
                d.rmdir()
            except OSError:
                pass
        for name in runtime:
            shutil.rmtree(dst / name, ignore_errors=True)
        # 任意层级的运行期目录（如 r10/workspace、agents/workspace）一并清掉
        for d in sorted((p for p in dst.rglob("*") if p.is_dir() and p.name in RUNTIME_DIRS),
                        key=lambda p: -len(p.parts)):
            shutil.rmtree(d, ignore_errors=True)
        # 嵌套 __pycache__ 与散落的 .pyc
        for d in list(dst.rglob("__pycache__")):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
        for f in dst.rglob("*.pyc"):
            f.unlink(missing_ok=True)
    return extra + [Path(d + "/") for d in runtime]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--prune", action="store_true",
                    help="镜像同步：删除目标侧独有文件（仅 Trae 技能目录）")
    args = ap.parse_args(argv)

    # 注意：不覆盖 WorkBuddy 的 agents/*.md —— 那是宿主侧生成物（138 行，含 hosts 专有字段），
    # 用仓库的 76 行版本覆盖会丢字段。它的代码入口是 bin/runtime。
    jobs = [
        ("WorkBuddy runtime", TEAM, WORKBUDDY / "bin" / "runtime", False),
        ("Trae 技能目录", TEAM, TRAE, True),
        ("Trae 技能目录（旧名）", TEAM, TRAE_LEGACY, True),
    ]
    total_changed = total_pruned = 0
    for label, src, dst, mirrorable in jobs:
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

        if args.prune and mirrorable and dst.resolve() in MIRROR_ALLOWED:
            extra = prune_tree(src, dst, args.check)
            total_pruned += len(extra)
            verb = "将删除" if args.check else "已删除"
            print(f"    {verb}目标独有 {len(extra)} 个", end="")
            if extra:
                print("：", "、".join(str(e) for e in extra[:5]),
                      "…" if len(extra) > 5 else "")
            else:
                print()

    tail = "（--check 未写入）" if args.check else ""
    print(f"\n合计变更 {total_changed} 个文件，镜像删除 {total_pruned} 个{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
