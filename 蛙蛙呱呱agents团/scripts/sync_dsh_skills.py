#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把团队技能包镜像到 DSH 技能发现目录，让它们**真的**出现在模型可见的技能索引里。

为什么需要它（这是本节最关键的机制）：
    DSH 的 `dsh-skill-filesystem` 只从四个根发现技能：
        <projectRoot>/.dsh/skills        ← 本脚本写入这里
        <projectRoot>/.agents/skills
        <DSH_HOME>/skills
        <~/.agents>/skills
    并且目录式 bundle 的形状固定为 `<root>/<name>/SKILL.md`（恰好两段）。

    本团队的 45 个 SKILL.md 都在 `<role>/references/capabilities/<id>/` 下，
    **一个都不在这四个根里**。所以在补上镜像之前，它们对模型是不可见的：
    不是文件不存在，而是发现机制扫不到。

镜像时做的一件事：
    把正文里的 `../../../` 相对引用改写成绝对路径。原因：镜像目录深度只有
    `<root>/<id>/`，原来按包深度（4 层）写的相对路径在镜像里会指错地方。

用法：
    python scripts/sync_dsh_skills.py            # 生成/刷新镜像
    python scripts/sync_dsh_skills.py --check    # 只校验是否与源同步
    python scripts/sync_dsh_skills.py --list     # 列出会镜像哪些包
    python scripts/sync_dsh_skills.py --dest DIR # 指定目标根（默认 <projectRoot>/.dsh/skills）

退出码：0 成功/一致 / 1 有漂移或错误 / 2 环境问题
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKER = "<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->"


def find_project_root(start: str) -> str:
    """向上找含 .git 的目录作为 projectRoot（与 dsh-skill-filesystem 的 findProjectRoot 对齐）。

    这一步很关键：DSH 从 `<projectRoot>/.dsh/skills` 发现技能。
    本仓库的 projectRoot 是团队根的**上一级**（`D:\蛙蛙呱呱`，那里有 .git），
    若把镜像写在团队根下，形态再对也扫不到。
    """
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(start)


def packs() -> list:
    """返回 [(cap_id, 源 SKILL.md 绝对路径, 所属角色目录)]。"""
    out = []
    for name in sorted(os.listdir(ROOT)):
        role_dir = os.path.join(ROOT, name)
        caps = os.path.join(role_dir, "references", "capabilities")
        if not os.path.isdir(caps):
            continue
        for cid in sorted(os.listdir(caps)):
            skill = os.path.join(caps, cid, "SKILL.md")
            if os.path.isfile(skill):
                out.append((cid, skill, role_dir))
    return out


def render(skill_path: str, role_dir: str) -> str:
    with io.open(skill_path, encoding="utf-8") as fh:
        text = fh.read()
    # 相对引用 → 绝对路径（Windows 反斜杠转正斜杠，避免 Markdown 里出现转义问题）
    role_posix = role_dir.replace(os.sep, "/")
    text = text.replace("../../../", role_posix + "/")
    # 在 frontmatter 之后插入生成标记，不污染 frontmatter 解析
    m = re.match(r"^---\n.*?\n---\n", text, flags=re.S)
    if m:
        text = text[:m.end()] + "\n" + MARKER + "\n" + text[m.end():]
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="镜像团队技能包到 DSH 技能发现目录")
    ap.add_argument("--check", action="store_true", help="只校验是否与源一致")
    ap.add_argument("--list", action="store_true", help="只列出会被镜像的包")
    ap.add_argument("--dest", default=None, help="目标根目录（默认 <projectRoot>/.dsh/skills）")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    items = packs()
    if not items:
        print("[sync] 没找到任何 SKILL.md", file=sys.stderr)
        return 2

    if args.list:
        print(f"共 {len(items)} 个技能包会镜像到 DSH 发现目录")
        for cid, skill, _role in items:
            print(f"  {cid:<34} ← {os.path.relpath(skill, ROOT)}")
        return 0

    dest = args.dest or os.path.join(find_project_root(ROOT), ".dsh", "skills")
    dest = os.path.abspath(dest)

    drift, written, errs = [], 0, []
    for cid, skill, role_dir in items:
        target_dir = os.path.join(dest, cid)
        target = os.path.join(target_dir, "SKILL.md")
        body = render(skill, role_dir)
        if args.check:
            if not os.path.isfile(target):
                drift.append((cid, "缺失"))
                continue
            with io.open(target, encoding="utf-8") as fh:
                if fh.read() != body:
                    drift.append((cid, "与源不一致"))
            continue
        try:
            os.makedirs(target_dir, exist_ok=True)
            with io.open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            written += 1
        except OSError as exc:
            errs.append((cid, str(exc)))

    if args.check:
        print(f"DSH 技能镜像校验：{dest}")
        print("=" * 70)
        print(f"源包 {len(items)} 个｜漂移 {len(drift)} 个")
        for cid, why in drift:
            print(f"  [DRIFT] {cid}: {why}")
        if drift:
            print("\n修复：python scripts/sync_dsh_skills.py")
            return 1
        print("[OK] 镜像与源完全一致")
        return 0

    print(f"DSH 技能镜像已刷新：{dest}")
    print("=" * 70)
    print(f"写入 {written} 个｜失败 {len(errs)} 个")
    for cid, why in errs:
        print(f"  [ERR] {cid}: {why}")
    # 校验形状：必须是 <root>/<id>/SKILL.md 两段，且 frontmatter name 与目录名一致
    bad = []
    for cid, _s, _r in items:
        p = os.path.join(dest, cid, "SKILL.md")
        if not os.path.isfile(p):
            bad.append((cid, "未生成"))
            continue
        with io.open(p, encoding="utf-8") as fh:
            head = fh.read(400)
        m = re.search(r"^name:\s*(\S+)", head, flags=re.M)
        if not m or m.group(1) != cid:
            bad.append((cid, f"frontmatter name 不匹配: {m.group(1) if m else '缺失'}"))
    if bad:
        print(f"\n形状校验失败 {len(bad)} 个：")
        for cid, why in bad:
            print(f"  - {cid}: {why}")
        return 1
    print(f"形状校验通过：{len(items)} 个包均为 <root>/<id>/SKILL.md，且 name 与目录一致")
    print(f"\nprojectRoot = {find_project_root(ROOT)}")
    print("提示：DSH 会在下次启动/刷新时发现它们；镜像目录已加入 .gitignore。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
