# -*- coding: utf-8 -*-
"""scripts/check_role_thickness.py —— 20 角色厚度地板（T1）。

两种口径：
  1. **棘轮地板**（默认 --check）：以 configs/role_thickness_baseline.json 为基线，
     任何角色的参考篇数/KB、生产模块、黄金/误用、端到端只要下降就失败；
  2. **L2 目标**（--report 展示）：方案 §5.2 的 L2 刻度，
     参考 ≥6 篇 / ≥30KB、生产模块 ≥5、黄金 ≥2、误用 ≥2、端到端 ≥1。
     当前只展示差距，不阻断；逐角色补厚后再把目标写进基线。

为什么先做棘轮：直接按 L2 绝对门槛会一次判 20 个角色全红，无法区分“存量薄”
与“这次改坏了”。棘轮先保证不退化，再用 L2 报表驱动补厚。

用法：
    python scripts/check_role_thickness.py --write-baseline
    python scripts/check_role_thickness.py --check
    python scripts/check_role_thickness.py --report
    python scripts/check_role_thickness.py --json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "configs" / "role_thickness_baseline.json"
DOC = ROOT / "docs" / "ROLE-THICKNESS.md"
L2 = {"refs": 6, "ref_kb": 30.0, "modules": 5, "golden": 2, "misuse": 2, "e2e": 1}


def _role_dirs2() -> List[Path]:
    out = []
    for p in sorted(ROOT.iterdir()):
        if not (p.is_dir() and p.name.startswith("r") and "-" in p.name):
            continue
        rid = p.name.split("-")[0]
        if len(rid) == 3 and rid[1:].isdigit():
            out.append(p)
    return out


def _count_glob(path: Path, pattern: str) -> int:
    return len(list(path.glob(pattern))) if path.is_dir() else 0


def metrics(role: Path) -> Dict[str, Any]:
    refs_dir = role / "references"
    ref_files = list(refs_dir.glob("*.md")) if refs_dir.is_dir() else []
    ref_kb = round(sum(f.stat().st_size for f in ref_files) / 1024, 1)
    modules = 0
    for sub in ("skills", "engines"):
        d = role / sub
        if d.is_dir():
            modules += sum(1 for f in d.glob("*.py")
                           if f.name != "__init__.py" and not f.name.startswith("_"))
    golden = _count_glob(role / "golden", "*.html")
    misuse = _count_glob(role / "misuse", "*.json")
    tests = _count_glob(role / "tests", "test_*.py")
    e2e = 1 if (role / "run_tests.py").is_file() else 0
    return {"refs": len(ref_files), "ref_kb": ref_kb, "modules": modules,
            "golden": golden, "misuse": misuse, "tests": tests, "e2e": e2e}


def census() -> Dict[str, Dict[str, Any]]:
    return {p.name.split("-")[0]: {"dir": p.name, **metrics(p)} for p in _role_dirs2()}


def _gaps(m: Dict[str, Any]) -> Dict[str, float]:
    return {k: round(max(0, L2[k] - m.get(k, 0)), 1) for k in L2}


def render(cur: Dict[str, Dict[str, Any]],
           base: Dict[str, Dict[str, Any]]) -> str:
    lines = [
        "# 角色厚度报表（ROLE-THICKNESS）",
        "",
        "> 由 `python scripts/check_role_thickness.py --write-baseline` 生成。",
        "> 口径：参考篇数/KB、生产模块（skills+engines）、黄金 HTML、误用 JSON、端到端脚本。",
        "> L2 目标来自方案 §5.2：参考 ≥6 篇 / ≥30KB、模块 ≥5、黄金 ≥2、误用 ≥2、端到端 ≥1。",
        "",
        "| 角色 | 参考 | KB | 模块 | 黄金 | 误用 | 测试 | E2E | L2 缺口 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rid, m in cur.items():
        g = _gaps(m)
        gap = "、".join(f"{k}+{v}" for k, v in g.items() if v > 0) or "达标"
        lines.append(f"| {rid} | {m['refs']} | {m['ref_kb']} | {m['modules']} | "
                     f"{m['golden']} | {m['misuse']} | {m['tests']} | {m['e2e']} | {gap} |")
    ok = sum(1 for m in cur.values() if not any(_gaps(m).values()))
    lines += ["", f"- 角色数：{len(cur)}；L2 达标：{ok}；未达标：{len(cur) - ok}。"]
    if base:
        lines += ["", "基线即上表（棘轮：只许上升）。"]
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_role_thickness")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    cur = census()
    if a.write_baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({"generated_by": "scripts/check_role_thickness.py",
                                        "rule": "ratchet: 只许上升",
                                        "l2": L2, "roles": cur},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
        DOC.write_text(render(cur, {}), encoding="utf-8")
        print(f"[thickness] 已写入基线 {BASELINE} 与报表 {DOC}（{len(cur)} 个角色）")
        return 0
    base = {}
    if BASELINE.is_file():
        base = json.loads(BASELINE.read_text(encoding="utf-8")).get("roles", {})
    problems = []
    if a.check:
        if not base:
            problems.append("缺少基线：先运行 --write-baseline")
        for rid, m in cur.items():
            b = base.get(rid)
            if not b:
                problems.append(f"{rid} 未登记基线")
                continue
            for k in ("refs", "ref_kb", "modules", "golden", "misuse", "tests", "e2e"):
                if m.get(k, 0) < b.get(k, 0):
                    problems.append(f"{rid}.{k} 从 {b.get(k)} 降到 {m.get(k)}")
        for rid in sorted(set(base) - set(cur)):
            problems.append(f"{rid} 基线存在、磁盘角色缺失")
    if a.json:
        print(json.dumps({"roles": cur, "baseline": base, "l2": L2,
                          "problems": problems}, ensure_ascii=False, indent=1))
    else:
        if a.report or not a.check:
            print(render(cur, base))
        print(f"[thickness] {len(cur)} 个角色；L2 达标 "
              f"{sum(1 for m in cur.values() if not any(_gaps(m).values()))}；问题 {len(problems)}")
        for p in problems[:12]:
            print(f"  - {p}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
