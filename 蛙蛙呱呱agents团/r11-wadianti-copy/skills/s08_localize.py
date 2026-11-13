# -*- coding: utf-8 -*-
"""S08 持续本地化 —— 能力域 8。

整合自 WeblateOrg__weblate（翻译协作/术语/审校/版本同步）。weblate 是重依赖
（完整服务/API），本角色只做「翻译项目管理」的确定性校验 + 如实降级探测：
术语表齐备、翻译项目标记、审校记录状态枚举。真实翻译执行交 weblate 服务，
本机无 weblate 客户端则 status=blocked，不假装会翻译。

动作：
  term    术语表（source/target/glossary）
  review  审校记录（term/source_lang/target_lang/status/reviewer）
  probe   重依赖探测（weblate 可用性，如实降级）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "localize"
DESC = "持续本地化：term/review/probe"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    t = act.add_parser("term", help="校验术语表")
    t.add_argument("--input", required=True)
    r = act.add_parser("review", help="校验审校记录")
    r.add_argument("--input", required=True)
    pr = act.add_parser("probe", help="weblate 可用性探测")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        return _probe()
    data = c.load_json(args.input)
    if args.action == "term":
        return _validate_term(data)
    if args.action == "review":
        return _validate_review(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_term(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["localize"]["terms_required"]:
        if k == "glossary":
            ok = isinstance(data.get(k), list) and len(data.get(k)) > 0
        else:
            ok = bool(str(data.get(k, "")).strip())
        checks.append(_ck(ok, f"术语表字段 {k} 齐备", f"localize.term.{k}"))

    src = data.get("source")
    tgt = data.get("target")
    ok_lang = src in th["localize"]["languages"] and tgt in th["localize"]["languages"]
    checks.append(_ck(ok_lang, f"语言对 {src}→{tgt} 在白名单", "localize.lang"))

    glossary = data.get("glossary", [])
    ok_gloss = isinstance(glossary, list) and all(
        isinstance(g, dict) and g.get("source") and g.get("target") for g in glossary)
    checks.append(_ck(ok_gloss, "glossary 条目含 source/target", "localize.glossary"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    glossary_count=len(glossary) if isinstance(glossary, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_review(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["localize"]["review_required"]:
        checks.append(_ck(bool(str(data.get(k, "")).strip()),
                          f"审校字段 {k} 非空", f"localize.review.{k}"))

    status = data.get("status")
    ok_status = status in th["localize"]["status_enum"]
    checks.append(_ck(ok_status, f"status={status!r} 在枚举 {th['localize']['status_enum']}",
                      "localize.review.status"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL", status=status)


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    """weblate 重依赖探测：如实降级（ok=true + status=ready/blocked），非门禁。"""
    th = c.load_thresholds()
    status = "blocked"
    note = "本机未检测到 weblate 客户端/服务，翻译执行降级为「术语表 + 审校记录」管理"
    try:
        import shutil
        if shutil.which("weblate") or shutil.which("wlc"):
            status = "ready"
            note = "检测到 weblate 客户端，可执行翻译协作"
    except Exception:
        pass
    checks = [c.ck(True, note, "localize.probe", status=status)]
    return c.result(checks, ok=True, verdict="PASS", status=status,
                    languages=th["localize"]["languages"], next="weblate 能力如实降级")
