# -*- coding: utf-8 -*-
"""S05 ASO 与发布 —— 能力域 5。

整合自 coreyhaines31__marketingskills（aso / launch）。
把「ASO 与发布」从口头建议转成确定性校验：标题/副标题字符上限、六维加权评分
（权重外置）、PH 发布清单四要素、上市节奏三阶段。

动作：
  aso   应用商店优化（字符上限 + 六维加权评分）
  ph    Product Hunt / 上市节奏（发布清单 + 三阶段）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "launch"
DESC = "ASO 与发布：aso/ph"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("aso", help="校验 ASO 清单")
    b.add_argument("--input", required=True)
    u = act.add_parser("ph", help="校验发布清单与节奏")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "aso":
        return _validate_aso(data)
    if args.action == "ph":
        return _validate_ph(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_aso(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    store = data.get("store")
    ok_store = store in th["launch"]["stores"]
    checks.append(_ck(ok_store, f"store={store!r} 在白名单", "aso.store"))
    if not ok_store:
        return c.result(checks, ok=False, verdict="FAIL", store=store, score=0,
                        grade=None)

    title = str(data.get("title", ""))
    ok_title = 0 < len(title) <= th["launch"]["title_max"]
    checks.append(_ck(ok_title,
                      f"标题长度 {len(title)} ≤ {th['launch']['title_max']}",
                      "aso.title"))

    subtitle = str(data.get("subtitle", ""))
    ok_sub = len(subtitle) <= th["launch"]["subtitle_max"]
    checks.append(_ck(ok_sub,
                      f"副标题长度 {len(subtitle)} ≤ {th['launch']['subtitle_max']}",
                      "aso.subtitle"))

    scores = data.get("scores")
    weights = th["launch"]["weights"]
    ok_scores = isinstance(scores, dict)
    checks.append(_ck(ok_scores, "六维评分存在", "aso.scores"))
    score = None
    if ok_scores:
        missing_dim = [d for d in weights if d not in scores]
        checks.append(_ck(not missing_dim, f"六维评分齐备（缺 {missing_dim or '无'}）",
                          "aso.score_dims"))
        if not missing_dim:
            score = round(sum(float(scores[d]) * w / 100.0
                              for d, w in weights.items()), 1)
            checks.append(_ck(all(0 <= float(scores[d]) <= 10 for d in weights),
                              "各维评分在 0-10 区间", "aso.score_range"))
    else:
        checks.append(_ck(False, "六维评分缺失", "aso.score_dims"))

    ok_scores_full = ok_scores and not any(d not in scores for d in weights)
    if ok_scores_full:
        try:
            ok_range = all(0 <= float(scores[d]) <= 10 for d in weights)
        except (TypeError, ValueError):
            ok_range = False
    else:
        ok_range = False
    ok = ok_store and ok_title and ok_sub and ok_scores_full and ok_range
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    store=store, score=score, grade=_grade(score, th) if score is not None else None)


def _grade(score: float, th: dict) -> str:
    for g, cutoff in [("A", th["launch"]["grade_bands"]["A"]),
                      ("B", th["launch"]["grade_bands"]["B"]),
                      ("C", th["launch"]["grade_bands"]["C"]),
                      ("D", th["launch"]["grade_bands"]["D"])]:
        if score >= cutoff:
            return g
    return "F"


# --------------------------------------------------------------------------- #
def _validate_ph(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    missing = [k for k in th["launch"]["ph_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"PH 发布清单四要素齐备（缺 {missing or '无'}）",
                      "launch.ph"))

    stages = data.get("stages")
    ok_stages = isinstance(stages, list) and len(stages) == 3
    checks.append(_ck(ok_stages,
                      f"上市节奏三阶段（实际 {len(stages) if isinstance(stages, list) else 0}）",
                      "launch.stages"))
    if ok_stages:
        want = th["launch"]["launch_stages"]
        bad = [s for s in stages if s not in want]
        checks.append(_ck(not bad, f"节奏阶段在白名单（越界 {bad or '无'}）",
                          "launch.stage_enum"))

    want = th["launch"]["launch_stages"]
    bad = [s for s in (stages or []) if s not in want]
    ok = not missing and ok_stages and not bad
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    stage_count=len(stages) if isinstance(stages, list) else 0)
