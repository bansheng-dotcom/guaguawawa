#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/check_dead_code.py —— 「每个文件都要能说清谁在用」的可执行版本。

为什么要有它：
    仓库 5 万行、200+ 文件。删不删一个文件，靠人记得「好像没人用」是不可靠的；
    靠一次大扫除也不可靠——下次加文件又会积累。
    所以把判据做成门禁：**每个 .py 必须有引用者，否则 CI 失败**。

三类引用者（任一即可）：
    1. import   —— 被别的 .py 用 `import` / `from ... import` 引用
    2. 运行     —— 被脚本、CI、文档以命令行调用（`scripts/xxx.py` 或以模块运行）
    3. 入口     —— `guagua.py` / 角色 `agent.py` / `tests/` 这类天然入口

例外要显式登记（ALLOW）：说明「为什么它是入口但没人 import」，
否则就是悄悄留死代码。

用法：
    python scripts/check_dead_code.py            # 人读报告
    python scripts/check_dead_code.py --json     # 机器读
    python scripts/check_dead_code.py --check    # 门禁：有死文件就 exit 1
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("core", "shared", "scripts", "z", "agents", "pipelines")
SKIP_PARTS = {"__pycache__", "_attic", ".git", "node_modules", "workspace",
              "projects"}
TEXT_EXT = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg",
            ".ini", ".sh", ".ps1"}

# 天然入口：不需要被 import，但必须有调用方（CI / 文档 / guagua.py 子命令）
ALLOW: Dict[str, str] = {
    "guagua.py": "总入口",
    "chat.py": "交互入口",
    "core/__main__.py": "python -m core 入口",
    "core/report_cli.py": "report 子命令分发",
    "scripts/sync_trae_skill.py": "Trae 技能镜像同步入口（手动执行）",
    "scripts/sync_workbuddy.py": "WorkBuddy/CodeBuddy 插件镜像同步入口（手动执行）",
}


def _iter_py():
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            yield p


def _iter_text():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_EXT:
            continue
        if any(s in p.parts for s in SKIP_PARTS):
            continue
        if p.stat().st_size > 3_000_000:
            continue
        yield p


def _mod_of(p: Path) -> str:
    rel = p.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imports(path: Path) -> Set[str]:
    """该文件 import 了哪些本仓模块（返回模块路径集合）。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return set()
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
                for a in node.names:
                    out.add(f"{node.module}.{a.name}")
            elif node.level and node.names:      # from . import x
                for a in node.names:
                    out.add(a.name)
    return out


def census() -> Dict[str, Dict[str, object]]:
    py_files = sorted(_iter_py())
    mods = {str(p.relative_to(ROOT)).replace("\\", "/"): _mod_of(p)
            for p in py_files}

    # 1) import 引用
    imported: Dict[str, Set[str]] = {rel: set() for rel in mods}
    for p in py_files:
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        for m in _imports(p):
            for other_rel, other_mod in mods.items():
                if other_rel == rel:
                    continue
                if m == other_mod or m.startswith(other_mod + "."):
                    imported[other_rel].add(rel)

    # 2) 文本/命令行引用（排除自身文件）
    stems = {rel: Path(rel).stem for rel in mods}
    mentioned: Dict[str, Set[str]] = {rel: set() for rel in mods}
    text_files = list(_iter_text())
    for tf in text_files:
        try:
            text = tf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        trel = str(tf.relative_to(ROOT)).replace("\\", "/")
        for rel, stem in stems.items():
            if trel == rel:
                continue
            if len(stem) < 4:
                continue
            if re.search(rf"(?<![\w-]){re.escape(stem)}(?![\w-])", text):
                mentioned[rel].add(trel)

    out: Dict[str, Dict[str, object]] = {}
    for rel in mods:
        imp, men = imported[rel], mentioned[rel]
        # 被任何非自身文件提到（代码/CI/文档/配置）都算有人用。
        # 之前只认 tests/scripts/docs，会把「被 core 里 subprocess 调用的脚本」
        # 误判成死代码（compile_agent_report 就中过这个误报）。
        real_men = {m for m in men if m != rel}
        if rel in ALLOW:
            verdict, why = "ENTRY", ALLOW[rel]
        elif imp:
            verdict, why = "LIVE", f"被 {len(imp)} 个文件 import"
        elif real_men:
            verdict, why = "SCRIPT", "被脚本/CI/文档调用"
        else:
            verdict, why = "DEAD", "没有任何引用者"
        out[rel] = {"module": mods[rel], "verdict": verdict, "why": why,
                    "imported_by": sorted(imp)[:8],
                    "mentioned_by": sorted(real_men)[:8]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    data = census()
    dead = {k: v for k, v in data.items() if v["verdict"] == "DEAD"}
    counts: Dict[str, int] = {}
    for v in data.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    if a.json:
        print(json.dumps({"counts": counts, "dead": dead}, ensure_ascii=False,
                         indent=2))
    else:
        print(f"文件总数 {len(data)}：{counts}")
        if dead:
            print(f"\n没人用的文件（{len(dead)}）：")
            for k in sorted(dead):
                print(f"  {k}")
    return 1 if (a.check and dead) else 0


if __name__ == "__main__":
    raise SystemExit(main())
