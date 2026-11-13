# -*- coding: utf-8 -*-
"""S07 高层汇报与创始人陪练 —— 能力域 7。

整合自 c-level-agents boardroom / office-hours / coach。
核心主张：董事会材料三段式（成绩/问题/计划/求助）；miss 不许掩盖；
陪练产出行动项而非鸡汤。
  memo   董事会材料门禁（成绩/问题/计划/求助 + 有 miss 必有归因）
  coach  创始人陪练（卡点 + ≥2 视角 + 行动项带 owner/due）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "boardroom"
DESC = "高层汇报与创始人陪练：memo/coach"


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("memo", "董事会材料门禁"),
                 ("coach", "创始人陪练门禁")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    return _memo(data) if args.action == "memo" else _coach(data)


# --------------------------------------------------------------------------- #
def _memo(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["boardroom"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    for sec in t["memo_sections"]:
        present = bool(data.get(sec))
        checks.append(_ck(present, f"材料含 {sec}", f"memo.{sec}"))

    wins = data.get("wins") or []
    checks.append(_ck(bool(wins), "成绩非空（先说好消息）", "memo.wins"))

    # misses 不许掩盖：有 miss 必有归因
    misses = data.get("misses") or []
    unattributed = [m.get("title", i) for i, m in enumerate(misses)
                    if isinstance(m, dict) and not m.get("root_cause")]
    checks.append(_ck(not unattributed,
                      "每个 miss 带归因" +
                      (f"（缺归因: {unattributed}）" if unattributed else ""),
                      "memo.miss_attribution"))

    # 求助明确：ask 必须带「向谁要什么」
    asks = data.get("asks") or []
    bad_asks = [i for i, a in enumerate(asks)
                if not (isinstance(a, dict) and a.get("from") and a.get("what"))]
    checks.append(_ck(not bad_asks,
                      "每条求助向谁要什么" + (f"（含糊: {bad_asks}）" if bad_asks else ""),
                      "memo.asks"))

    # 指标可追溯：每个 win/miss 的数字来自记分卡
    metrics = {m.get("name") for m in (data.get("metrics") or [])
               if isinstance(m, dict)}
    referenced = set()
    for m in wins + misses:
        if isinstance(m, dict) and m.get("metric"):
            referenced.add(m.get("metric"))
    orphan = referenced - metrics if metrics else set()
    checks.append(_ck(not orphan,
                      "win/miss 引用的指标在记分卡内" +
                      (f"（孤儿指标: {sorted(orphan)}）" if orphan else ""),
                      "memo.metric_traceability"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "sections": t["memo_sections"],
            "win_count": len(wins), "miss_count": len(misses), "checks": checks}


def _coach(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["boardroom"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    for f in t["coach_fields"]:
        checks.append(_ck(bool(data.get(f)), f"陪练卡含 {f}", f"coach.{f}"))

    views = data.get("alternative_views") or []
    checks.append(_ck(len(views) >= t["alternative_views_min"],
                      f"替代视角 ≥{t['alternative_views_min']} 个", "coach.views"))

    actions = data.get("action_items") or []
    checks.append(_ck(bool(actions), "陪练产出行动项（非鸡汤）", "coach.actions"))
    for i, a in enumerate(actions):
        checks.append(_ck(bool(a.get("action")) and bool(a.get("owner"))
                          and bool(a.get("due")),
                          f"行动项[{i}] 带 action+owner+due", f"coach.action.{i}"))

    # 陪练不替创始人拍板：不给「最终决定」，只给视角与行动项
    checks.append(_ck(not data.get("final_decision"),
                      "陪练不替创始人拍板（无 final_decision 字段）",
                      "coach.no_decision"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "coach_fields": t["coach_fields"],
            "action_count": len(actions), "checks": checks}
