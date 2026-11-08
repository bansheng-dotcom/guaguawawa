# -*- coding: utf-8 -*-
"""S05 品牌语调与编辑 —— 能力域 5。

整合自 bzwh321__article-director 的 style-harmonizer + style-guide 纪律。
把「统一称谓/口吻/术语/禁词/语法/标点」转成确定性校验：品牌指南六维齐备 +
清洁终稿的禁词命中与术语修复可追溯。禁词口径与 s04 copy 同源（thresholds）。

动作：
  guide  品牌语调指南（audience/tone/terms/forbidden/grammar）
  edit   清洁终稿（forbidden_hits/term_fixes 可追溯）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "voice"
DESC = "品牌语调与编辑：guide/edit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    g = act.add_parser("guide", help="校验品牌语调指南")
    g.add_argument("--input", required=True)
    e = act.add_parser("edit", help="校验清洁终稿")
    e.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "guide":
        return _validate_guide(data)
    if args.action == "edit":
        return _validate_edit(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_guide(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["voice"]["guide_required"]:
        v = data.get(k)
        if k == "terms" or k == "forbidden":
            ok = isinstance(v, list) and len(v) > 0
        else:
            ok = bool(str(v or "").strip())
        checks.append(_ck(ok, f"语调指南字段 {k} 齐备", f"voice.guide.{k}"))

    # 六维覆盖检查（dimensions 白名单至少覆盖 4 维）
    dims = data.get("dimensions", [])
    if isinstance(dims, list):
        covered = [d for d in th["voice"]["dimensions"] if d in dims]
        checks.append(_ck(len(covered) >= 4,
                          f"语调维度覆盖 ≥4（实际 {len(covered)}：{covered}）",
                          "voice.dimensions"))
    else:
        checks.append(_ck(False, "dimensions 缺列表", "voice.dimensions"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    dimension_count=len(dims) if isinstance(dims, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_edit(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["voice"]["edit_required"]:
        checks.append(_ck(k in data, f"清洁终稿字段 {k} 存在", f"voice.edit.{k}"))

    text = str(data.get("text", ""))
    hits = data.get("forbidden_hits", [])
    ok_hits = isinstance(hits, list)
    checks.append(_ck(ok_hits, "forbidden_hits 为列表", "voice.edit.hits"))

    # 终稿不得再含禁词（若声明已清洁但文本仍含禁词 → FAIL）
    if text:
        remaining = [w for w in th["copy"]["forbidden_zh"] if w in text]
        checks.append(_ck(not remaining,
                          f"终稿无残留禁词（残留 {remaining[:5] or '无'}）",
                          "voice.edit.residual"))

    fixes = data.get("term_fixes", [])
    ok_fixes = isinstance(fixes, list) and all(
        isinstance(f, dict) and "from" in f and "to" in f for f in fixes)
    checks.append(_ck(ok_fixes, "term_fixes 条目含 from/to", "voice.edit.fixes"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    forbidden_count=len(hits) if isinstance(hits, list) else 0,
                    fix_count=len(fixes) if isinstance(fixes, list) else 0)
