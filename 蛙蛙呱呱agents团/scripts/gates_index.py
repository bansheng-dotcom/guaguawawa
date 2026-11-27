# -*- coding: utf-8 -*-
"""scripts/gates_index.py —— 门禁索引：每个 check_*.py 必须说清「谁在跑」。

为什么要有它：
    仓库里有 28 个 check_*.py。有的进 CI，有的被 configs/gates.yaml 引用，
    有的只在手工流程里用。没有索引时，「这个门禁到底有没有在跑」只能靠人记，
    新增一个门禁也很容易悄悄变成孤儿脚本。

判据（按优先级）：
    CI          —— 出现在 scripts/ci_report_checks.py 或 scripts/ci_upgrade_checks.py
    GATES       —— 出现在 configs/gates.yaml
    INDIRECT    —— 被另一个 scripts/*.py 调用（evidence 写明是谁）
    MANUAL      —— 在本文件的 MANUAL 表里显式登记 + 写理由
    未登记      —— 以上都没有：--check 失败

用法：
    python scripts/gates_index.py            # 人读
    python scripts/gates_index.py --write    # 生成 docs/GATES.md
    python scripts/gates_index.py --check    # 门禁：未登记或文件过期就 exit 1
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
OUT = ROOT / "docs" / "GATES.md"
CI_FILES = ("ci_report_checks.py", "ci_upgrade_checks.py")
GATES_YAML = ROOT / "configs" / "gates.yaml"

#: 既不在 CI、也不在 gates.yaml、也没被其它脚本调用的门禁，必须写清理由。
#: 新增条目 = 承认它目前只能手工跑；能进 CI 的就不要往这里加。
MANUAL: Dict[str, str] = {
    "check_gates.py": "由 core/report/report_cli.py 的 gates 子命令在运行时调用",
}

STATUS_ORDER = ("CI", "GATES", "INDIRECT", "MANUAL", "未登记")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _purpose(p: Path) -> str:
    """脚本用途：取模块 docstring 的第一行有效文字。"""
    try:
        tree = ast.parse(_read(p))
    except SyntaxError:
        return ""
    doc = ast.get_docstring(tree) or ""
    for line in doc.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("scripts/") and "——" in s:
            s = s.split("——", 1)[1].strip()
        if s:
            return s
    return ""


def _gates_yaml_entries() -> List[Tuple[str, str, str]]:
    """读 gates.yaml 的 gates 段（只做轻量行解析，不引入 yaml 依赖）。"""
    rows: List[Tuple[str, str, str]] = []
    cur = ""
    in_gates = False
    for raw in _read(GATES_YAML).splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith((" ", "\t")):
            in_gates = line.strip() == "gates:"
            continue
        if not in_gates:
            continue
        if raw.startswith("  ") and not raw.startswith("    ") and line.strip().endswith(":"):
            cur = line.strip().rstrip(":")
            rows.append((cur, "", ""))
            continue
        if raw.startswith("    ") and rows and cur:
            key, _, val = line.strip().partition(":")
            if key in ("impl", "tool", "threshold", "registry", "golden_corpus"):
                g, ev, note = rows[-1]
                ev = f"{ev} {key}={val.strip()}".strip()
                rows[-1] = (g, ev, note)
    return rows


def classify() -> List[Dict[str, str]]:
    check_files = sorted(SCRIPTS.glob("check_*.py"))
    texts = {p.name: _read(p) for p in SCRIPTS.glob("*.py")}
    ci_text = "".join(texts.get(n, "") for n in CI_FILES)
    yaml_text = _read(GATES_YAML)
    rows: List[Dict[str, str]] = []
    for p in check_files:
        name = p.name
        if name in ci_text:
            status, ev = "CI", "ci_report_checks / ci_upgrade_checks"
        elif name in yaml_text:
            status, ev = "GATES", "configs/gates.yaml"
        else:
            refs = sorted(n for n, t in texts.items()
                          if n not in (name, Path(__file__).name)
                          and name in t and n not in CI_FILES)
            if refs:
                status, ev = "INDIRECT", "被 " + "、".join(refs[:2]) + " 调用"
            elif name in MANUAL:
                status, ev = "MANUAL", MANUAL[name]
            else:
                status, ev = "未登记", "没有任何 CI / gates.yaml / 脚本引用"
        rows.append({"script": name, "status": status, "evidence": ev,
                     "purpose": _purpose(p)})
    return rows


def render(rows: List[Dict[str, str]]) -> str:
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines = [
        "# 门禁索引（GATES）",
        "",
        "> 由 `python scripts/gates_index.py --write` 生成，禁止手改。",
        "> 状态：CI=进 CI；GATES=configs/gates.yaml 引用；INDIRECT=被其它脚本调用；"
        "MANUAL=显式登记（只能手工跑）；未登记=没有消费者。",
        "",
        "## 汇总",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for k in STATUS_ORDER:
        lines.append(f"| {k} | {counts.get(k, 0)} |")
    lines += ["", "## 脚本", "",
              "| 脚本 | 状态 | 证据 | 用途 |", "|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (STATUS_ORDER.index(x["status"]),
                                         x["script"])):
        purpose = (r["purpose"] or "-").replace("|", "\\|")
        lines.append(f"| `{r['script']}` | {r['status']} | {r['evidence']} | {purpose} |")
    gates = _gates_yaml_entries()
    lines += ["", "## configs/gates.yaml", ""]
    if gates:
        lines += ["| gate | 实现 / 阈值 |", "|---|---|"]
        for g, ev, _ in gates:
            lines.append(f"| `{g}` | {ev or '-'} |")
    else:
        lines.append("无。")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="生成 docs/GATES.md")
    ap.add_argument("--check", action="store_true", help="未登记/文件过期则失败")
    a = ap.parse_args(argv)
    rows = classify()
    text = render(rows)
    if a.write:
        OUT.write_text(text, encoding="utf-8")
        print(f"[gates-index] 已更新 {OUT}")
        return 0
    bad = [r["script"] for r in rows if r["status"] == "未登记"]
    if a.check:
        stale = not OUT.is_file() or OUT.read_text(encoding="utf-8") != text
        if bad:
            print("[gates-index] FAIL 未登记门禁：" + "、".join(bad))
            print("  接入 CI / gates.yaml，或在 scripts/gates_index.py 的 MANUAL 里写理由")
            return 1
        if stale:
            print("[gates-index] FAIL docs/GATES.md 过期：运行 --write 并提交")
            return 1
        print(f"[gates-index] PASS {len(rows)} 个门禁，全部有消费者，索引最新")
        return 0
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"[gates-index] {len(rows)} 个门禁：{counts}")
    for r in rows:
        if r["status"] == "未登记":
            print(f"  未登记：{r['script']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
