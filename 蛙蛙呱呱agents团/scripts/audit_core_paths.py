# -*- coding: utf-8 -*-
"""scripts/audit_core_paths.py —— core/ 内部耦合审计（为后续合并提供证据）。

为什么要有它：
    「card 六合一」「claim 四合一」这类合并，难点不在删文件，而在先弄清
    一条 import 边被多少模块依赖。凭印象动手，很容易合到一半发现环。
    本脚本用静态 import 分析给出确定性证据：

        - 包间耦合边（core.a.* → core.b.*）计数
        - 模块扇入 / 扇出 Top 20
        - 模块级循环依赖（强连通分量）

生成物：docs/_migration/couplings.md（`--write` 生成，`--check` 校验最新）。

用法：
    python scripts/audit_core_paths.py
    python scripts/audit_core_paths.py --write
    python scripts/audit_core_paths.py --check
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
OUT = ROOT / "docs" / "_migration" / "couplings.md"
TOP_N = 20


def _dot(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _modules() -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    for p in CORE.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        out[_dot(p.relative_to(ROOT))] = p
    return out


def _resolve(name: str, mods: Set[str]) -> str:
    """把 import 名归一到 core 下的某个模块（最长前缀）。"""
    cur = name
    while cur.startswith("core"):
        if cur in mods:
            return cur
        if "." not in cur:
            break
        cur = cur.rsplit(".", 1)[0]
    return name if name in mods else ""


def _imports(path: Path, mod: str, mods: Set[str]) -> Set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return set()
    pkg = mod.rsplit(".", 1)[0]
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                hit = _resolve(a.name, mods)
                if hit:
                    found.add(hit)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = pkg.split(".")
                keep = len(parts) - (node.level - 1)
                base = ".".join(parts[:max(keep, 1)] + ([base] if base else []))
            for a in node.names:
                hit = _resolve(f"{base}.{a.name}" if base else a.name, mods)
                if hit:
                    found.add(hit)
            if base:
                hit = _resolve(base, mods)
                if hit:
                    found.add(hit)
    found.discard(mod)
    return found


def _package(mod: str) -> str:
    parts = mod.split(".")
    return ".".join(parts[:2]) if len(parts) > 2 else ".".join(parts)


def _scc(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Tarjan，返回大小 > 1 的强连通分量。"""
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on: Set[str] = set()
    stack: List[str] = []
    out: List[List[str]] = []
    counter = [0]

    def visit(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp: List[str] = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in sorted(graph):
        if v not in index:
            visit(v)
    return sorted(out)


def collect() -> Dict[str, object]:
    mods = _modules()
    names = set(mods)
    graph: Dict[str, Set[str]] = {}
    for mod, path in mods.items():
        graph[mod] = _imports(path, mod, names)
    fan_out = {m: len(v) for m, v in graph.items()}
    fan_in: Dict[str, int] = Counter()
    for v in graph.values():
        for dst in v:
            fan_in[dst] += 1
    cross: Counter = Counter()
    sample: Dict[Tuple[str, str], str] = {}
    for src in sorted(graph):
        for dst in sorted(graph[src]):
            a, b = _package(src), _package(dst)
            if a != b:
                cross[(a, b)] += 1
                edge = f"{src} → {dst}"
                if (a, b) not in sample or edge < sample[(a, b)]:
                    sample[(a, b)] = edge
    return {"modules": mods, "graph": graph, "fan_in": dict(fan_in),
            "fan_out": fan_out, "cross": cross, "sample": sample,
            "cycles": _scc(graph)}


def render(data: Dict[str, object]) -> str:
    graph: Dict[str, Set[str]] = data["graph"]  # type: ignore[assignment]
    fan_in: Dict[str, int] = data["fan_in"]  # type: ignore[assignment]
    fan_out: Dict[str, int] = data["fan_out"]  # type: ignore[assignment]
    cross: Counter = data["cross"]  # type: ignore[assignment]
    sample: Dict[Tuple[str, str], str] = data["sample"]  # type: ignore[assignment]
    cycles: List[List[str]] = data["cycles"]  # type: ignore[assignment]
    edges = sum(len(v) for v in graph.values())
    lines = [
        "# core/ 内部耦合审计（couplings）",
        "",
        "> 由 `python scripts/audit_core_paths.py --write` 生成，禁止手改。",
        "> 口径：静态 import 分析；只统计 core 内部模块之间的边，不含 tests/scripts。",
        "",
        "## 汇总",
        "",
        "| 指标 | 数量 |",
        "|---|---:|",
        f"| core 模块 | {len(graph)} |",
        f"| 内部 import 边 | {edges} |",
        f"| 跨包边 | {sum(cross.values())} |",
        f"| 循环（SCC>1） | {len(cycles)} |",
        "",
        "## 包间耦合",
        "",
        "| 从 | 到 | 边数 | 代表 |",
        "|---|---|---:|---|",
    ]
    for (a, b), n in sorted(cross.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| `{a}` | `{b}` | {n} | {sample[(a, b)]} |")
    lines += ["", f"## 扇出 Top {TOP_N}（这个模块 import 了多少 core 模块）", "",
              "| 模块 | 扇出 |", "|---|---:|"]
    for m, n in sorted(fan_out.items(), key=lambda x: (-x[1], x[0]))[:TOP_N]:
        lines.append(f"| `{m}` | {n} |")
    lines += ["", f"## 扇入 Top {TOP_N}（有多少模块依赖它）", "",
              "| 模块 | 扇入 |", "|---|---:|"]
    for m, n in sorted(fan_in.items(), key=lambda x: (-x[1], x[0]))[:TOP_N]:
        lines.append(f"| `{m}` | {n} |")
    lines += ["", "## 循环依赖（SCC > 1）", ""]
    if cycles:
        for comp in cycles:
            lines.append("- " + " ↔ ".join(f"`{m}`" for m in comp))
    else:
        lines.append("无。")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="生成 couplings.md")
    ap.add_argument("--check", action="store_true", help="文件过期则失败")
    a = ap.parse_args(argv)
    text = render(collect())
    if a.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(f"[core-paths] 已更新 {OUT}")
        return 0
    if a.check:
        if not OUT.is_file():
            print("[core-paths] FAIL 缺 couplings.md：先跑 --write")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print("[core-paths] FAIL couplings.md 过期：重跑 --write 并提交")
            return 1
        print("[core-paths] PASS 耦合表最新")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
