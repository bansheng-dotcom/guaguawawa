# -*- coding: utf-8 -*-
"""把团队代码镜像到 WorkBuddy / CodeBuddy 插件目录。

结构（WorkBuddy 插件）：
    wawa-guagua-agents/
      .codebuddy-plugin/plugin.json
      agents/                      ← agent-packs/agents/*.md
      avatars/                     ← agent-packs/avatars/*
      skills/wawa-guagua-core/
        SKILL.md                   ← 版本号自动 +0.0.1
        references/                ← 根目录的 *.md（ORG/PROTOCOL/...）
        source/                    ← 整个代码仓库（与本目录同构）
        workspace/
      README.md

用法：
    python scripts/sync_workbuddy.py --check     # 只对比，不写盘
    python scripts/sync_workbuddy.py             # 写入
    python scripts/sync_workbuddy.py --dest DIR  # 指定插件目录
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DEST = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "plugins", "marketplaces",
    "my-experts", "plugins", "wawa-guagua-agents")
SKILL = "wawa-guagua-core"
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache",
                "node_modules", ".venv", "venv", "projects", "workspace",
                ".idea", ".vscode", "dist", "build", ".DS_Store"}
EXCLUDE_EXT = {".pyc", ".pyo", ".log", ".tmp", ".pdf", ".png", ".jpg",
               ".jpeg", ".zip", ".tar", ".gz", ".db", ".sqlite"}
REF_FILES = ("AGENTS.md", "ORG.md", "PROTOCOL.md", "README.md",
             "REPORT-BRIDGE-GUIDE.md", "REPORT-STANDARD.md", "SKILL.md",
             "TEAM.md", "使用指南.md")


def excluded(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return True
    ext = os.path.splitext(rel)[1].lower()
    return ext in EXCLUDE_EXT


def collect(root: str) -> dict:
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


def bump_version(dest: str) -> str:
    """SKILL.md 的 metadata.version 自增 patch 位。"""
    p = os.path.join(dest, "skills", SKILL, "SKILL.md")
    if not os.path.isfile(p):
        return ""
    s = open(p, encoding="utf-8").read()
    m = re.search(r'version:\s*"(\d+)\.(\d+)\.(\d+)"', s)
    if not m:
        return ""
    new = "%s.%s.%d" % (m.group(1), m.group(2), int(m.group(3)) + 1)
    s = s[:m.start(3)] + str(int(m.group(3)) + 1) + s[m.end(3):]
    open(p, "w", encoding="utf-8").write(s)
    return new


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="镜像团队代码到 WorkBuddy 插件目录")
    ap.add_argument("--check", action="store_true", help="只对比，不写盘")
    ap.add_argument("--dest", default=None, help="插件目录（默认自动探测 WorkBuddy）")
    ap.add_argument("--no-bump", action="store_true", help="不自增版本号")
    args = ap.parse_args(argv)

    dest = os.path.abspath(args.dest or DEFAULT_DEST)
    if not os.path.isdir(dest):
        print("目标不存在：%s" % dest)
        return 2

    # ① source/ ← 整个仓库
    src_files = collect(ROOT)
    dst_root = os.path.join(dest, "skills", SKILL, "source")
    written = skipped = 0
    drifts = []
    for rel, abs_p in src_files.items():
        target = os.path.join(dst_root, rel)
        same = (os.path.isfile(target)
                and digest(target) == digest(abs_p))
        if same:
            skipped += 1
            continue
        drifts.append(rel)
        if args.check:
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(abs_p, target)
        written += 1

    # ② references/ ← 根文档
    ref_dir = os.path.join(dest, "skills", SKILL, "references")
    for fn in REF_FILES:
        src = os.path.join(ROOT, fn)
        if not os.path.isfile(src):
            continue
        tgt = os.path.join(ref_dir, fn)
        if os.path.isfile(tgt) and digest(tgt) == digest(src):
            continue
        drifts.append("references/" + fn)
        if not args.check:
            os.makedirs(ref_dir, exist_ok=True)
            shutil.copy2(src, tgt)

    # ③ agents/ + avatars/ ← agent-packs
    for sub, pat in (("agents", ".md"), ("avatars", "")):
        s = os.path.join(ROOT, "agent-packs", sub)
        if not os.path.isdir(s):
            continue
        d = os.path.join(dest, sub)
        for fn in sorted(os.listdir(s)):
            if pat and not fn.endswith(pat):
                continue
            src = os.path.join(s, fn)
            if not os.path.isfile(src):
                continue
            tgt = os.path.join(d, fn)
            if os.path.isfile(tgt) and digest(tgt) == digest(src):
                continue
            drifts.append(sub + "/" + fn)
            if not args.check:
                os.makedirs(d, exist_ok=True)
                shutil.copy2(src, tgt)

    if args.check:
        print("源文件 %d 个｜与目标不同 %d 个" % (len(src_files), len(drifts)))
        for d in drifts[:12]:
            print("  [DRIFT]", d)
        return 1 if drifts else 0

    ver = "" if args.no_bump else bump_version(dest)
    print("WorkBuddy 插件已刷新：%s" % dest)
    print("源文件 %d 个｜写入 %d 个｜未变 %d 个｜差异项 %d 个"
          % (len(src_files), written, skipped, len(drifts)))
    if ver:
        print("SKILL.md 版本 → %s" % ver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
