# -*- coding: utf-8 -*-
"""把「技能运行所需」同步到本地 Trae / WorkBuddy 镜像包。

映射：
  Trae：角色与运行时都放在 role-runtime/agents/
  WorkBuddy：角色放 references/roles/，运行时（core/shared/scripts/...）放 references/
             —— 因为 role agent 的 _ROOT 是 references，core 必须在其下
不复制 workspace、cases、avatars、报告产物。
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent

TARGETS = [
    {"label": "Trae 本地镜像",
     "root": Path(r"D:\蛙蛙呱呱\traeskills\wawa-guagua\tools\role-runtime\agents"),
     "role_prefix": ""},
    {"label": "WorkBuddy 本地镜像",
     "root": Path(r"D:\蛙蛙呱呱\workbuddy专家团\wawa-company-os\skills\wawa-company-protocol\references"),
     "role_prefix": "roles"},
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


def dest_for(target: dict, rel: Path) -> Path:
    if rel.parts and rel.parts[0].startswith("r") and rel.parts[0][1:3].isdigit():
        return target["root"] / target["role_prefix"] / rel
    return target["root"] / rel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    files = all_files()
    print(f"待同步技能运行时文件：{len(files)} 个")
    total = 0
    for t in TARGETS:
        root = t["root"]
        if not root.exists():
            print(f"[skip] {t['label']}: 不存在 {root}")
            continue
        changed = same = 0
        for src in files:
            rel = src.relative_to(TEAM)
            dst = dest_for(t, rel)
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                same += 1
                continue
            changed += 1
            if not args.check:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        total += changed
        print(f"[{t['label']}] {'需同步' if args.check else '已同步'}：变更 {changed}，一致 {same} → {root}")
    print(f"\n合计变更 {total} 个文件" + ("（--check 未写入）" if args.check else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
