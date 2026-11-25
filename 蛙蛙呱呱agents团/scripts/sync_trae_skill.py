#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把团队技能包镜像到 Trae 的技能目录（`<Trae skills>/wawaguagua-agents/`）。

为什么需要它：
    Trae（国内版）从 `~/.trae-cn/skills/<name>/SKILL.md` 发现「用户上传」技能，
    技能名取目录名，正文取 SKILL.md。团队包在 Trae 里的落点是
    `~/.trae-cn/skills/wawaguagua-agents/`，内容必须与源包 `蛙蛙呱呱agents团/` 一致。

    镜像必须**保持原目录形状**：SKILL.md 与角色卡里大量使用相对引用
    （`../../../shared/...`、`r06-wadeqing-analyst/skills/...`），压平成
    `<root>/<id>/SKILL.md` 会全部指错地方 —— 这正是 DSH 镜像
    （scripts/sync_dsh_skills.py）需要改写路径、而 Trae 镜像不需要改写的原因。

排除项（不是技能本体，进了镜像只会让 Trae 变慢）：
    workspace/         运行态产物（.gitignore 已排除）
    __pycache__/ .pytest_cache/ *.pyc    Python 缓存
    _attic/            删除留档
    projects/pet-beijing/   59 MB 试验输出（out_*/、.dsh-office-*、一次性探针）

用法：
    python scripts/sync_trae_skill.py             # 增量镜像（删掉目标里源已不存在的文件）
    python scripts/sync_trae_skill.py --check     # 只对比，不写盘；有漂移返回 1
    python scripts/sync_trae_skill.py --no-prune  # 只覆盖/新增，不删多余文件
    python scripts/sync_trae_skill.py --dest DIR  # 指定技能根（默认自动探测 Trae）

退出码：0 一致/成功 / 1 有漂移或错误 / 2 环境问题（找不到目标根）
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL_NAME = "wawaguagua-agents"

EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "workspace",
    "_attic",
    ".cache",
}
EXCLUDE_DIR_PATHS = {
    os.path.join("projects", "pet-beijing"),
    # 管线测试产物（.gitignore 已排除，每次跑测试都会重写）
    os.path.join("pipelines", "out"),
}
EXCLUDE_FILES = {
    # 规范化测试会重写这个夹具，内容随时间变化，不属于技能本体
    os.path.join("tests", "fixtures", "_norm_tmp.json"),
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def default_dest_root() -> str:
    """Trae 技能根：国内版 ~/.trae-cn/skills，国际版 ~/.trae/skills。"""
    home = os.path.expanduser("~")
    for name in (".trae-cn", ".trae"):
        root = os.path.join(home, name, "skills")
        if os.path.isdir(root):
            return root
    return os.path.join(home, ".trae-cn", "skills")


def excluded(rel: str) -> bool:
    parts = rel.split(os.sep)
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return True
    if parts and parts[-1] in EXCLUDE_DIRS:
        return True
    if rel in EXCLUDE_DIR_PATHS or any(rel.startswith(p + os.sep) for p in EXCLUDE_DIR_PATHS):
        return True
    if rel in EXCLUDE_FILES:
        return True
    return rel.lower().endswith(EXCLUDE_SUFFIXES)


def collect(root: str):
    """返回 {相对路径: 绝对路径}，已剔除排除项。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames) if d not in EXCLUDE_DIRS]
        for fn in sorted(filenames):
            abs_p = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_p, root)
            if excluded(rel):
                continue
            out[rel] = abs_p
    return out


def digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="镜像团队技能包到 Trae 技能目录")
    ap.add_argument("--check", action="store_true", help="只对比，不写盘")
    ap.add_argument("--no-prune", action="store_true", help="不删除目标中多出的文件")
    ap.add_argument("--dest", default=None, help="技能根目录（默认自动探测 Trae）")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    skills_root = os.path.abspath(args.dest or default_dest_root())
    dest = os.path.join(skills_root, SKILL_NAME)
    if not os.path.isdir(skills_root):
        print(f"[sync] 技能根不存在：{skills_root}", file=sys.stderr)
        print("       请先确认 Trae 已安装并打开过一次（会创建 skills/ 目录）", file=sys.stderr)
        return 2

    src_files = collect(ROOT)
    dst_files = collect(dest) if os.path.isdir(dest) else {}

    added, changed = [], []
    for rel, abs_p in src_files.items():
        target = os.path.join(dest, rel)
        if rel not in dst_files:
            added.append(rel)
        elif os.path.getsize(abs_p) != os.path.getsize(target) or digest(abs_p) != digest(target):
            changed.append(rel)

    prune = not args.check and not args.no_prune
    extras = [rel for rel in dst_files if rel not in src_files]
    stale = extras if prune else []

    if args.check:
        print(f"Trae 技能镜像校验：{dest}")
        print("=" * 70)
        print(f"源文件 {len(src_files)} 个｜目标 {len(dst_files)} 个")
        print(f"缺失 {len(added)} 个｜内容不同 {len(changed)} 个｜目标多出 {len(extras)} 个")
        for rel in (added[:20] + changed[:20] + extras[:10]):
            print(f"  [DRIFT] {rel}")
        if added or changed or extras:
            print("\n修复：python scripts/sync_trae_skill.py")
            return 1
        print("[OK] 与源完全一致")
        return 0

    errs = []
    for rel in added + changed:
        target = os.path.join(dest, rel)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, rel), target)
        except OSError as exc:
            errs.append((rel, str(exc)))
    for rel in stale:
        try:
            os.remove(os.path.join(dest, rel))
        except OSError as exc:
            errs.append((rel, str(exc)))
    # 清掉空的残留目录
    for dirpath, dirnames, filenames in os.walk(dest, topdown=False):
        if dirpath == dest or dirnames or filenames:
            continue
        try:
            os.rmdir(dirpath)
        except OSError:
            pass

    print(f"Trae 技能镜像已刷新：{dest}")
    print("=" * 70)
    print(f"源文件 {len(src_files)} 个｜写入 {len(added) + len(changed)} 个"
          f"（新增 {len(added)}｜更新 {len(changed)}）｜删除 {len(stale)} 个"
          f"｜失败 {len(errs)} 个")
    for rel, why in errs:
        print(f"  [ERR] {rel}: {why}")

    # 形状校验：必须有 SKILL.md，且 frontmatter name 与技能目录名一致
    skill_md = os.path.join(dest, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"\n[ERR] 缺少 {skill_md}", file=sys.stderr)
        return 1
    with io.open(skill_md, encoding="utf-8") as fh:
        head = fh.read(600)
    name_line = [ln for ln in head.splitlines() if ln.startswith("name:")]
    if not name_line or name_line[0].split(":", 1)[1].strip() != SKILL_NAME:
        print(f"\n[ERR] SKILL.md frontmatter name 必须是 {SKILL_NAME}：{name_line}", file=sys.stderr)
        return 1
    print(f"形状校验通过：SKILL.md 在根、name = {SKILL_NAME}")
    print("提示：Trae 下次启动（或技能面板刷新）后生效。")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
