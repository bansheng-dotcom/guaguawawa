#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/wiring_truth.py —— 接线真相表：哪些模块真的在产线上。

为什么需要它：
    仓库里同时存在「文档说有」「测试在测」「产线在用」三种状态。三者不一致时，
    新人会「知道错的」；这比不知道更贵。本脚本用确定性证据把三者摊开：

        LIVE      —— 被非测试代码 import，或被打包/CLI 以 core.X 调用
        TEST_ONLY —— 只有 tests/ 引用（绿的是孤儿，不是产线）
        DOC_ONLY  —— 只在文档里被提到
        UNWIRED   —— 以上都没有

同时检查文档死链：文档里写的 core/X.py、python -m core.X 是否真的存在。

用法：
    python scripts/wiring_truth.py                 # 人读
    python scripts/wiring_truth.py --json          # 机器读
    python scripts/wiring_truth.py --write docs/_migration/wiring-truth.md
    python scripts/wiring_truth.py --check         # 门禁：UNWIRED / DOC_DEAD / 过期债

债务登记（WIRING_DEBT）：已经确认未接线、但需要产品决定「接回还是删除」的模块。
禁止新增未登记项；登记项一旦接线，必须同步删掉，否则 --check 报「过期债务」。
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
SKIP_PARTS = {"__pycache__", ".git", ".pytest_cache", "workspace", "vendor",
              "agent-packs", "_attic"}
DOC_ROOTS = [ROOT]
DOC_DIRS = [ROOT / "docs"]
DEBT_FILE = ROOT / "docs" / "_migration" / "wiring-debt.json"

#: 模块名 → 为什么暂时允许未接线（必须写清「接回还是删除」的待决事项）
DEFAULT_DEBT: Dict[str, str] = {
    "claim_card": "待决：接回 report_flow 恢复头条门禁，或归档",
    "claim_gate": "待决：同上；归档文档 docs/archive/REPORT-CLAIM-GATE.md 需要同步",
    "chart_fit": "待删：report_flow.chart_fitness_errors 已覆盖同判据",
    "prose_critic": "待删：prose_style + F10/F12 已覆盖正文门禁",
    "evidence_graph": "待删：证据图未接入任何产线路径",
    "argument_plan": "待删：论证计划未接入任何产线路径",
    "spec_extract": "待删：规格抽取未接入任何产线路径",
    "coverage_cli": "待决：收成 guagua coverage 命令，或删除",
    "task_frame": "随 coverage_cli 一起决定",
    "task_research": "随 coverage_cli 一起决定",
    "analysis_lab": "待决：保留为手工分析工具（补入口）或删除",
    "gate_chain": "待决：让 audit_dod 真跑，或连文本检查一起删",
}

#: F7 职责键 → 唯一模块（点路径）。一个职责只许一个出处，一个模块只许承担一个职责；
#: 指向不存在的模块、或同一模块被两个职责占用，--check 即失败。
RESPONSIBILITY: Dict[str, str] = {
    "正文契约": "core.prose.prose_contract",
    "正文生成": "core.prose.prose_render",
    "拆卡": "core.cards.pipeline",
    "ClaimCard 契约": "core.claims.contract",
}


def _py_files() -> List[Path]:
    out = []
    for p in ROOT.rglob("*.py"):
        if any(s in p.parts for s in SKIP_PARTS):
            continue
        out.append(p)
    return out


def _core_files() -> Dict[str, Path]:
    """core 下全部实现文件：键是 rel 路径，值为文件（含子包）。"""
    out = {}
    for p in CORE.rglob("*.py"):
        if any(s in p.parts for s in SKIP_PARTS):
            continue
        out[_rel(p)] = p
    return out


def _dot(rel: str) -> str:
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imports(path: Path) -> Set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, OSError):
        return set()
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "core" or a.name.startswith("core."):
                    out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "core":
                out.update("core." + a.name for a in node.names)
            elif node.module and node.module.startswith("core."):
                out.add(node.module)
                for a in node.names:
                    out.add(node.module + "." + a.name)
    return out


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def build() -> Dict[str, object]:
    files = _core_files()
    dotted = {}
    for rel in files:
        dotted.setdefault(_dot(rel), rel)
    # 平铺模块（仅为报告口径保留；包内模块也参与可达性）
    mods = {rel[len("core/"):-3]: p for rel, p in files.items()
            if rel.count("/") == 1 and not rel.endswith("/__init__.py")}

    importers: Dict[str, Set[str]] = {rel: set() for rel in files}
    cli_refs: Dict[str, Set[str]] = {rel: set() for rel in files}
    doc_refs: Dict[str, Set[str]] = {m: set() for m in mods}

    for p in _py_files():
        rel = _rel(p)
        for name in _imports(p):
            target = dotted.get(name)
            if target and target != rel:
                importers[target].add(rel)

    # CLI 引用只认“真的会被执行”的写法，避免把注释/说明里的 core.xxx 当调用。
    py_cli = re.compile(
        r"(?:-m\s+|import_module\(\s*[\"']|[\"']-m[\"']\s*,\s*[\"'])"
        r"core\.([a-z0-9_.]+)")
    cfg_cli = re.compile(r"\bcore\.([a-z0-9_.]+)\b")
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(s in p.parts for s in SKIP_PARTS):
            continue
        suf = p.suffix.lower()
        if suf not in {".py", ".json", ".yaml", ".yml", ".sh", ".ps1", ".toml"}:
            continue
        rel = _rel(p)
        if rel.startswith("core/"):
            continue  # core 内部引用走 import 图，不靠文本
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if suf in {".json", ".yaml", ".yml", ".toml"}:
            found = cfg_cli.findall(text)
        else:
            found = py_cli.findall(text)
        for name in found:
            target = dotted.get("core." + name)
            if target:
                cli_refs[target].add(rel)

    doc_words: List[Tuple[str, Set[str]]] = []
    for p in list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md")):
        if not p.is_file() or any(x in p.parts for x in ("_archive", "archive")):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        head = "\n".join(text.splitlines()[:20])
        if re.search(r"status\s*:\s*ARCHIVED", head, re.I):
            continue
        doc_words.append((_rel(p), set(re.findall(r"[A-Za-z0-9_]{4,}", text))))
    for m in mods:
        for rel, words in doc_words:
            if m in words:
                doc_refs[m].add(rel)

    # 可达性：从「非 core、非 tests 的 .py」与 CLI 引用出发，沿 import 图反向传递。
    # 只看直接引用者会把「死模块引用另一个模块」误判成 LIVE（claim_gate → claim_card）。
    root_files = {_rel(p) for p in _py_files()
                  if not _rel(p).startswith(("core/", "tests/"))}
    reach: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for rel in files:
            if rel in reach:
                continue
            if any(x in root_files or x in reach
                   for x in importers[rel] if not x.startswith("tests/")):
                reach.add(rel)
                changed = True
                continue
            if cli_refs[rel]:
                reach.add(rel)
                changed = True

    rows = {}
    for m, path in sorted(mods.items()):
        rel = "core/" + m + ".py"
        non_test_imp = {x for x in importers[rel] if not x.startswith("tests/")}
        test_imp = {x for x in importers[rel] if x.startswith("tests/")}
        cli = {x for x in cli_refs[rel] if not x.startswith("tests/")}
        if rel in reach:
            status = "LIVE"
        elif test_imp:
            status = "TEST_ONLY"
        elif doc_refs[m]:
            status = "DOC_ONLY"
        else:
            status = "UNWIRED"
        rows[m] = {
            "module": m,
            "lines": len(path.read_text(encoding="utf-8", errors="ignore").splitlines()),
            "status": status,
            "imported_by": sorted(non_test_imp)[:6],
            "cli_refs": sorted(cli)[:6],
            "tests": sorted(test_imp)[:4],
            "docs": sorted(doc_refs[m])[:4],
        }

    # 文档死链（跳过 archive 与标记为 ARCHIVED 的历史文档）
    # __init__ 不参与“是否接线”，但它是真实存在的文件，文档引用不算死链
    def _exists(dotted: str, is_dir: bool = False) -> bool:
        """core 下路径是否真实存在；支持 P4 之后的嵌套包路径。"""
        p = CORE.joinpath(*dotted.split("/" if "/" in dotted else "."))
        return p.is_dir() if is_dir else p.with_suffix(".py").is_file()

    doc_dead: List[Dict[str, str]] = []
    seen = set()
    # 明说“已删除/不新增/不再”的行是历史说明，不算失效承诺
    hints = ("已删除", "已删", "已下线", "已废弃", "不新增", "不再", "历史",
             "不宜", "removed", "deprecated", "archived")
    for p in list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md")):
        if not p.is_file() or any(x in p.parts for x in ("_archive", "archive")):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        head = "\n".join(text.splitlines()[:20])
        if re.search(r"status\s*:\s*ARCHIVED", head, re.I):
            continue
        skip_block = False
        for line in text.splitlines():
            low = line.lower()
            if not line.strip():
                skip_block = False
                continue
            if any(h in low for h in hints):
                skip_block = True
                continue
            if skip_block and (line.startswith((" ", "\t")) or line.strip().startswith(("-", "`", "|"))):
                continue
            skip_block = False
            for m in re.findall(r"core/([a-z0-9_/]+)\.py", line):
                if not _exists(m) and (m, _rel(p), "file") not in seen:
                    seen.add((m, _rel(p), "file"))
                    doc_dead.append({"module": m, "doc": _rel(p), "kind": "file"})
            for m in re.findall(r"python -m core\.([a-z0-9_.]+)", line):
                if not _exists(m) and (m, _rel(p), "cli") not in seen:
                    seen.add((m, _rel(p), "cli"))
                    doc_dead.append({"module": m, "doc": _rel(p), "kind": "cli"})
    return {"rows": rows, "doc_dead": doc_dead}


def _debt() -> Dict[str, str]:
    if DEBT_FILE.is_file():
        try:
            return json.loads(DEBT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_DEBT)


def _render(data: Dict[str, object]) -> str:
    rows = data["rows"]
    groups = {"UNWIRED": [], "TEST_ONLY": [], "DOC_ONLY": []}
    for r in rows.values():
        if r["status"] in groups:
            groups[r["status"]].append(r)
    lines = ["# 接线真相表", "",
             "> 由 `python scripts/wiring_truth.py --write` 生成，禁止手改。",
             "> LIVE=非测试代码 import 或 core.X 调用；TEST_ONLY=只有测试；"
             "DOC_ONLY=只有文档；UNWIRED=都没有。", ""]
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("|---|---:|")
    for k in ("LIVE", "TEST_ONLY", "DOC_ONLY", "UNWIRED"):
        n = sum(1 for r in rows.values() if r["status"] == k)
        lines.append(f"| {k} | {n} |")
    lines.append(f"| DOC_DEAD | {len(data['doc_dead'])} |")
    lines.append("")
    for k, title in (("UNWIRED", "未接线"), ("TEST_ONLY", "只有测试引用"),
                     ("DOC_ONLY", "只有文档提及")):
        lines.append(f"## {title}（{len(groups[k])}）")
        lines.append("")
        if not groups[k]:
            lines.append("无。")
            lines.append("")
            continue
        lines.append("| 模块 | 行数 | 证据 |")
        lines.append("|---|---:|---|")
        for r in sorted(groups[k], key=lambda x: -x["lines"]):
            ev = (r["cli_refs"] or r["tests"] or r["docs"] or ["-"])[0]
            lines.append(f"| `{r['module']}` | {r['lines']} | {ev} |")
        lines.append("")
    lines.append(f"## 文档死链（{len(data['doc_dead'])}）")
    lines.append("")
    if data["doc_dead"]:
        lines.append("| 模块 | 文档 | 类型 |")
        lines.append("|---|---|---|")
        for d in data["doc_dead"]:
            lines.append(f"| `{d['module']}` | {d['doc']} | {d['kind']} |")
    else:
        lines.append("无。")
    lines.append("")
    lines.append("## 职责登记（F7）")
    lines.append("")
    lines.append("| 职责 | 唯一模块 |")
    lines.append("|---|---|")
    for key, dotted in RESPONSIBILITY.items():
        lines.append(f"| {key} | `{dotted}` |")
    lines.append("")
    return "\n".join(lines)


def _check_responsibility(files: Dict[str, Path]) -> List[str]:
    problems: List[str] = []
    seen: Dict[str, str] = {}
    for key, dotted in RESPONSIBILITY.items():
        rel = dotted.replace(".", "/") + ".py"
        if rel not in files:
            problems.append(f"职责登记指向不存在的模块：{key} → {dotted}")
        if dotted in seen:
            problems.append(f"职责重复声明同一模块：{key} / {seen[dotted]} → {dotted}")
        seen[dotted] = key
    return problems


def _check(data: Dict[str, object]) -> List[str]:
    debt = _debt()
    problems: List[str] = _check_responsibility(_core_files())
    unwired = [r for r in data["rows"].values()
               if r["status"] in ("UNWIRED", "TEST_ONLY", "DOC_ONLY")]
    for r in unwired:
        if r["module"] not in debt:
            problems.append(
                f"{r['module']}（{r['status']}，{r['lines']} 行）未接线且未登记债务")
    for m in debt:
        if m not in data["rows"]:
            problems.append(f"债务登记过期：{m} 已不存在，请从 wiring-debt.json 删除")
        elif data["rows"][m]["status"] == "LIVE":
            problems.append(f"债务登记过期：{m} 已接线，请从 wiring-debt.json 删除")
    for d in data["doc_dead"]:
        problems.append(f"文档死链：{d['doc']} 引用不存在的 core/{d['module']}.py")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wiring_truth")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", default="")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    data = build()
    if a.write:
        p = Path(a.write)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_render(data), encoding="utf-8")
        print(f"已写入 {p}")
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif not a.write:
        print(_render(data))
    if a.check:
        problems = _check(data)
        if problems:
            print("接线真相门禁 FAIL：", file=sys.stderr)
            for x in problems:
                print("  - " + x, file=sys.stderr)
            return 1
        print("接线真相门禁 PASS：无未登记未接线模块，无文档死链")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
