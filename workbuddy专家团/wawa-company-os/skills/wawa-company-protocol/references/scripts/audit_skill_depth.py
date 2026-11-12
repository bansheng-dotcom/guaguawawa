# -*- coding: utf-8 -*-
"""技能深度审计：区分「校验器」与「模型」，并按方法深度分级。

L1 校验器：只做 schema/规则检查，不产出估计量
L2 能算：有计算/评分/估计，但无不确定性
L3 可解释：估计 + 不确定性（CI/方差/自助）或敏感性
L4 可审计：估计 + 不确定性 + 敏感性/假设 + 契约/测试
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"__init__.py", "_common.py"}

CALC = re.compile(r"\b(mean|median|std|variance|sum\(|math\.|statistics|regression|elasticity|"
                  r"simulat|optimi|forecast|solve|score|probab|bootstrap|monte|matrix|"
                  r"correlat|linear|logistic|tco|npv|irr|wip|inventory|runway)\b", re.I)
UNC = re.compile(r"ci95|confidence|interval|std|variance|bootstrap|p_value|\bse_|uncertain|"
                 r"z_score|percentile", re.I)
SENS = re.compile(r"sensitivity|scenario|what_if|sweep|stress|grid|breakeven|翻转|敏感性|情景", re.I)
ASSUME = re.compile(r"assumption|assume|hypothesis|caveat|limitation|precondition|"
                    r"假设|前提|限制", re.I)


def role_dirs() -> list[Path]:
    return sorted(p for p in ROOT.iterdir() if p.is_dir() and re.match(r"r\d\d-", p.name))


def audit_role(d: Path) -> dict:
    files = sorted(p for p in (d / "skills").glob("*.py") if p.name not in SKIP)
    rows = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        explicit = re.search(r'DEPTH\s*=\s*["\']L([1-4])', text)
        if explicit:
            rows.append({"skill": f.stem, "level": f"L{explicit.group(1)}",
                         "lines": len(text.splitlines())})
            continue
        calc = bool(CALC.search(text))
        unc = bool(UNC.search(text))
        sens = bool(SENS.search(text))
        assume = bool(ASSUME.search(text))
        if not calc:
            level = "L1"
        elif unc and sens:
            level = "L4" if assume else "L3"
        elif unc or sens:
            level = "L3"
        else:
            level = "L2"
        rows.append({"skill": f.stem, "level": level, "lines": len(text.splitlines())})
    counts = {lv: sum(1 for r in rows if r["level"] == lv) for lv in ("L1", "L2", "L3", "L4")}
    has_tests = (d / "tests").is_dir() or (d / "run_tests.py").exists()
    return {"role": d.name, "n": len(rows), "counts": counts,
            "tests": has_tests, "rows": rows}


def main() -> None:
    data = [audit_role(d) for d in role_dirs()]
    out = ROOT / "workspace" / "skill_depth_audit.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'角色':<26}{'技能':<6}{'L1':<5}{'L2':<5}{'L3':<5}{'L4':<5}{'测试':<5}最低分技能")
    print("-" * 110)
    for r in data:
        low = [x["skill"] for x in r["rows"] if x["level"] == "L1"][:3]
        c = r["counts"]
        print(f"{r['role']:<26}{r['n']:<6}{c['L1']:<5}{c['L2']:<5}{c['L3']:<5}{c['L4']:<5}"
              f"{'有' if r['tests'] else '无':<5}{','.join(low) or '—'}")
    total = {lv: sum(r["counts"][lv] for r in data) for lv in ("L1", "L2", "L3", "L4")}
    print(f"\n合计 {sum(total.values())} 个技能：L1 {total['L1']} / L2 {total['L2']} / L3 {total['L3']} / L4 {total['L4']}")
    print(f"明细：{out}")


if __name__ == "__main__":
    main()
