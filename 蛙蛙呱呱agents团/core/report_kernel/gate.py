# -*- coding: utf-8 -*-
"""report_kernel.gate —— 交付门禁（ship gate）。

它把「报告能不能交付」收敛为一次确定性检查：
  契约、档位、深度、图卡、表头单位、重复句、manifest、来源计数、
  序列/时点、跨报告一致性、版式、字体。

用法：
    python -m core.report_kernel ship <report.html>
    python -m core.report_kernel ship <report.html> --contract x.ship.json --json x.ship.json
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import report_kernel
from core.report_kernel import consistency, contract as C, series

LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def _check(cid: str, ok: bool, detail: str, evidence: str = "",
           severity: str = "blocker") -> Dict[str, Any]:
    return {"id": cid, "ok": bool(ok), "detail": detail,
            "evidence": evidence, "severity": severity}


def _find_sibling(html: Path, suffix: str) -> Optional[Path]:
    for cand in (html.with_suffix(suffix), html.parent / suffix.lstrip(".")):
        if cand.exists():
            return cand
    return None


def run_gate(html_path: str | Path,
             ship_path: Optional[str | Path] = None,
             registry_path: Optional[str | Path] = None,
             peers: Optional[List[str | Path]] = None,
             strict: bool = True) -> Dict[str, Any]:
    html_path = Path(html_path)
    checks: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []

    # 1) 契约
    ship_file = Path(ship_path) if ship_path else C.find_for(html_path)
    ship = C.load(ship_file) if ship_file and ship_file.exists() else {}
    cv = C.validate(ship) if ship else {"ok": False, "errors": ["缺 ship 契约"],
                                        "warnings": [], "normalized": {}}
    if not cv["ok"]:
        sev = "blocker" if strict else "warn"
        checks.append(_check("C1_contract", False,
                             "；".join(cv["errors"][:4]) or "缺 ship 契约",
                             str(ship_file or ""), sev))
        if strict:
            errors.extend(cv["errors"])
        else:
            warnings.extend(cv["errors"])
    else:
        checks.append(_check("C1_contract", True, "契约六项齐备",
                             str(ship_file)))
    warnings.extend(cv.get("warnings") or [])
    target = str((cv.get("normalized") or {}).get("target_level") or "L4")

    # 2) 档位
    from scripts.grade_report_level import grade
    g = grade(html_path)
    level = str(g.get("level") or "L0")
    checks.append(_check("C2_level", LEVEL_ORDER.get(level, 0) >= LEVEL_ORDER.get(target, 4),
                         f"报告 {level} / 目标 {target}",
                         f"chars={g.get('chars')} figures={g.get('figures')}"))
    if LEVEL_ORDER.get(level, 0) < LEVEL_ORDER.get(target, 4):
        errors.append(f"档位 {level} 低于目标 {target}：{g.get('reasons')}")

    # 3) 深度门禁
    from core.report.report_quality import audit
    q = audit(str(html_path))
    checks.append(_check("C3_quality", bool(q.get("ok")),
                         f"report_quality {'PASS' if q.get('ok') else 'FAIL'}（{q.get('score')}）",
                         json.dumps([c for c in q.get("checks", []) if not c["ok"]],
                                    ensure_ascii=False)[:300]))
    if not q.get("ok"):
        errors.append("深度门禁未过")

    # 4) 图卡与来源
    figs = int(g.get("figures") or 0)
    fig_src = int(g.get("fig_with_source") or 0)
    checks.append(_check("C4_figures", figs >= 3 and fig_src >= figs,
                         f"fig-card {figs} 张，带来源 {fig_src} 张",
                         "要求 ≥3 且全部带 fig-src"))
    if figs < 3 or fig_src < figs:
        errors.append(f"图卡不足或缺口径：{figs} / {fig_src}")

    # 5) 表头单位
    tables = int(g.get("tables") or 0)
    units = int(g.get("tables_with_unit") or 0)
    need_units = max(2, tables // 3)
    checks.append(_check("C5_table_units", units >= need_units,
                         f"表头带单位 {units}/{tables}（需 ≥{need_units}）",
                         "按 grade_report_level 统计"))
    if units < need_units:
        errors.append(f"表头单位不足：{units}/{tables}")

    # 6) 重复句与禁用词
    dup = int(g.get("dup_sentences") or 0)
    banned = list(g.get("banned") or [])
    checks.append(_check("C6_duplicates", dup == 0, f"重复句 {dup} 条",
                         "按 grade_report_level 统计"))
    if dup:
        errors.append(f"内部重复句 {dup} 条")
    checks.append(_check("C6b_banned", not banned, f"禁用词 {banned or '无'}",
                         "REPORT-STANDARD 禁用词"))
    if banned:
        errors.append(f"命中禁用词：{banned}")

    # 7) manifest
    man_file = _find_sibling(html_path, ".manifest.json")
    man = {}
    if man_file:
        try:
            man = json.loads(man_file.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"manifest 读不了：{exc}")
    man_ok = bool(man) and str(man.get("status") or "").lower() in {"rendered", "ok", "pass"}
    sev = "blocker" if target == "L4" else "warn"
    checks.append(_check("C7_manifest", man_ok,
                         f"manifest {'存在' if man_file else '缺失'}；status={man.get('status')}",
                         str(man_file or ""), sev))
    if not man_ok:
        (errors if sev == "blocker" else warnings).append("manifest 缺失或未渲染")

    # 8) 来源计数
    html = html_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)\s*个(?:外部)?来源", re.sub(r"<[^>]+>", "", html))
    html_src = int(m.group(1)) if m else 0
    contract_src = int((cv.get("normalized") or {}).get("source_count") or 0)
    man_src = int(man.get("sources") or 0) if isinstance(man, dict) else 0
    counts = [x for x in (html_src, contract_src, man_src) if x]
    src_ok = len(set(counts)) <= 1 if counts else False
    checks.append(_check("C8_source_count", src_ok,
                         f"来源计数 html={html_src} contract={contract_src} manifest={man_src}",
                         "三处必须一致"))
    if not src_ok:
        errors.append(f"来源计数不一致：{counts}")

    # 9) 序列 / 时点
    if cv.get("ok"):
        sr = series.check_series(cv["normalized"])
    else:
        sr = {"ok": False, "errors": ["无契约，无法校验序列/时点"], "warnings": []}
    checks.append(_check("C9_series_time", bool(sr.get("ok")),
                         "序列/时点通过" if sr.get("ok") else "；".join(sr.get("errors", [])[:3]),
                         f"periods={sr.get('periods')} span={sr.get('time_span_days')}",
                         "blocker" if strict else "warn"))
    if not sr.get("ok"):
        (errors if strict else warnings).extend(sr.get("errors") or [])
    warnings.extend(sr.get("warnings") or [])

    # 10) 跨报告一致性
    cons_errs: List[str] = []
    if registry_path:
        reg = consistency.load_registry(registry_path)
        cr = consistency.check_registry(reg)
        cons_errs += cr["errors"]
    if peers:
        pc = consistency.compare_contracts([html_path] + list(peers))
        cons_errs += pc["errors"]
        warnings.extend(pc.get("warnings") or [])
    checks.append(_check("C10_consistency", not cons_errs,
                         "无冲突" if not cons_errs else "；".join(cons_errs[:3]),
                         f"peers={len(peers or [])} registry={bool(registry_path)}"))
    errors.extend(cons_errs)

    # 11) 版式与字体
    try:
        from scripts.check_report_layout import check_html
        lay = check_html(html_path)
        checks.append(_check("C11_layout", bool(lay.get("ok")),
                             "版式 PASS" if lay.get("ok") else "；".join(lay.get("violations", [])[:3]),
                             f"duplicate_sentences={lay.get('duplicate_sentences')}"))
        if not lay.get("ok"):
            errors.append("版式门禁未过")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"版式检查跳过：{exc}")

    try:
        from scripts.check_report_style import check as style_check
        se = style_check(html_path)
        checks.append(_check("C12_style", not se,
                             "字体 PASS" if not se else "；".join(se[:3])))
        if se:
            errors.append("字体门禁未过")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"字体检查跳过：{exc}")

    blockers = [c for c in checks if c["severity"] == "blocker"]
    passed = sum(1 for c in checks if c["ok"])
    score = round(100 * passed / max(1, len(checks)), 1)
    out = {
        "schema": "report-ship/v1",
        "ok": all(c["ok"] for c in blockers),
        "report": str(html_path),
        "report_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest()[:16],
        "level": level,
        "target": target,
        "score": score,
        "checks": checks,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reproduce": "python -m core.report_kernel ship " + str(html_path),
    }
    return out
