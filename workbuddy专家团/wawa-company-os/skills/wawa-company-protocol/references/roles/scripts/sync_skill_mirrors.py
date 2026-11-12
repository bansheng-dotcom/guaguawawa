# -*- coding: utf-8 -*-
"""把「技能运行所需」同步到本地 Trae / WorkBuddy 镜像包。

同步范围：
  * 每个角色：skills/ + agent.py + contracts.py + harness.py + run_tests.py + SKILL.md
  * 运行时目录：core / configs / shared / scripts / styles / templates / knowledge / report_specs / agents
  * 测试：tests/test_methods_*.py
  * 文档：深度 SOP / 技能审计 / 改动地图
不复制 workspace、cases、avatars、报告产物。
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

TARGETS = [
    ("Trae 本地镜像", Path(r"D:\蛙蛙呱呱\traeskills\wawa-guagua\tools\role-runtime\agents")),
    ("WorkBuddy 本地镜像", Path(r"D:\蛙蛙呱呱\workbuddy专家团\wawa-company-os\skills\wawa-company-protocol\references\roles")),
]

RUNTIME_DIRS = ["core", "configs", "shared", "scripts", "styles", "templates",
                "knowledge", "report_specs", "agents"]
DOCS = ["docs/方法代码深度升级SOP.md", "docs/技能深度审计_2026-11-12.md",
        "docs/深度地图核对.md", "docs/升级改动地图.md"]
TESTS = ["tests/test_methods_core.py", "tests/test_methods_deep.py",
         "tests/test_methods_deep_advanced.py", "tests/test_methods_business.py",
         "tests/test_method_gate.py"]


def role_files() -> list[Path]:
    out = []
    for role in sorted(TEAM.glob("r[0-9][0-9]-*")):
        if not role.is_dir():
            continue
        out.extend(p for p in (role / "skills").rglob("*.py") if p.is_file())
        for name in ("agent.py", "contracts.py", "harness.py", "run_tests.py", "SKILL.md"):
            p = role / name
            if p.is_file():
                out.append(p)
    return out


def all_files() -> list[Path]:
    files = role_files()
    for rel in RUNTIME_DIRS:
        p = TEAM / rel
        if p.exists():
            files.extend(q for q in p.rglob("*") if q.is_file()
                         and "__pycache__" not in q.parts and q.suffix != ".pyc")
    for rel in DOCS + TESTS:
        p = TEAM / rel
        if p.is_file():
            files.append(p)
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    files = all_files()
    print(f"待同步技能运行时文件：{len(files)} 个")
    total = 0
    for label, dst_root in TARGETS:
        if not dst_root.exists():
            print(f"[skip] {label}: 不存在 {dst_root}")
            continue
        changed = same = 0
        for src in files:
            rel = src.relative_to(TEAM)
            dst = dst_root / rel
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                same += 1
                continue
            changed += 1
            if not args.check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        total += changed
        print(f"[{label}] {'需同步' if args.check else '已同步'}：变更 {changed}，一致 {same} → {dst_root}")
    print(f"\n合计变更 {total} 个文件" + ("（--check 未写入）" if args.check else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
