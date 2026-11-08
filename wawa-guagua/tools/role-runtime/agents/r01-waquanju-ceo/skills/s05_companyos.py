# -*- coding: utf-8 -*-
"""S05 公司 OS 与治理 —— 能力域 5。

整合自 c-level-advisor company-os + microsoft/agent-governance-toolkit 治理模型。
核心主张：六大组件缺一不可；记分卡 ≤15 个指标数值目标；越界即被发现并截停。
  os         六大组件门禁（责任图/记分卡/会议节奏/IDS/Rocks/沟通）
  scorecard  记分卡校验（5-15 指标 + owner + 数值目标 + 只看红）
  ids        问题解决 IDS（一 owner + 一动作 + 一到期日，单议题 ≤15min）
  freeze     冷却锁（防冲动再决策，解锁永久留痕）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "companyos"
DESC = "公司OS与治理：os/scorecard/ids/freeze"


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": sev or ("OK" if ok else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("os", "公司 OS 六大组件门禁"),
                 ("scorecard", "记分卡校验（数值目标+只看红）"),
                 ("ids", "问题解决 IDS 门禁"),
                 ("freeze", "冷却锁判定（防冲动再决策）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"os": _os, "scorecard": _scorecard, "ids": _ids,
          "freeze": _freeze}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _os(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["companyos"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    components = data.get("components") or {}
    for comp in t["components"]:
        present = bool(components.get(comp))
        checks.append(_ck(present, f"OS 组件[{comp}] 就位", f"os.{comp}"))

    # 记分卡数量红线（40 个 KPI=看数而非管数）
    sc = components.get("scorecard") or {}
    metrics = sc.get("metrics") if isinstance(sc, dict) else None
    if isinstance(metrics, list):
        checks.append(_ck(t["scorecard_min"] <= len(metrics) <= t["scorecard_max"],
                          f"记分卡 {len(metrics)} 项 ∈ [{t['scorecard_min']}, "
                          f"{t['scorecard_max']}]", "os.scorecard_size"))

    # Rocks 二元：每人 3-7 个，done/not_done 无「60% 完成」
    rocks = components.get("rocks") or {}
    items = rocks.get("items") if isinstance(rocks, dict) else None
    if isinstance(items, list) and items:
        per_owner: Dict[str, int] = {}
        for r in items:
            if isinstance(r, dict):
                per_owner[r.get("owner", "?")] = per_owner.get(r.get("owner", "?"), 0) + 1
        bad = {o: n for o, n in per_owner.items()
               if not (t["rocks_min"] <= n <= t["rocks_max"])}
        checks.append(_ck(not bad,
                          f"每人 Rocks 3-7 个" + (f"（越界: {bad}）" if bad else ""),
                          "os.rocks_count"))
        partial = [r.get("title") for r in items
                   if isinstance(r, dict) and str(r.get("status", "")).endswith("%")]
        checks.append(_ck(not partial,
                          "Rocks 二元判定（无「60% 完成」）"
                          + (f"（发现: {partial}）" if partial else ""),
                          "os.rocks_binary"))

    # 硬边界（不可弱化）
    hard = data.get("hard_boundaries") or {}
    checks.append(_ck(bool(hard.get("default_deny")),
                      "护栏 default-deny 就位", "os.default_deny"))
    checks.append(_ck(bool(hard.get("audit_log")),
                      "审计日志就位（越界即被发现）", "os.audit_log"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "components": t["components"], "checks": checks}


def _scorecard(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["companyos"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}
    metrics = data.get("metrics") or []

    checks.append(_ck(t["scorecard_min"] <= len(metrics) <= t["scorecard_max"],
                      f"记分卡 {len(metrics)} 项 ∈ [{t['scorecard_min']}, "
                      f"{t['scorecard_max']}]", "scorecard.size"))

    range_targets, no_owner = [], []
    for i, m in enumerate(metrics):
        if not m.get("owner"):
            no_owner.append(i)
        target = m.get("target")
        # 数值目标（非区间）：区间字符串如 "10-20" / "10~20" 判违规
        if isinstance(target, str) and any(sep in target for sep in ("-", "~", "至")):
            range_targets.append((i, target))
        checks.append(_ck(m.get("status") in ("red", "yellow", "green", ""),
                          f"指标[{m.get('name', i)}] 红黄绿状态合法",
                          f"scorecard.{i}.status"))

    checks.append(_ck(not no_owner, "每项指标有 owner" +
                      (f"（缺: {no_owner}）" if no_owner else ""),
                      "scorecard.owner"))
    checks.append(_ck(not range_targets,
                      "目标为数值（非区间）" +
                      (f"（区间: {range_targets}）" if range_targets else ""),
                      "scorecard.target"))

    reds = [m.get("name") for m in metrics if m.get("status") == "red"]
    agenda = data.get("agenda_discusses")
    if agenda is not None:
        # 周会只讨论红项：议程里出现绿项=跑偏
        checks.append(_ck(all(r in (agenda or []) for r in reds) or not reds,
                          "议程覆盖全部红项", "scorecard.agenda_red"))
        checks.append(_ck(not [a for a in (agenda or [])
                               if a not in reds and a in
                               [m.get("name") for m in metrics
                                if m.get("status") != "red"]],
                          "议程只含红项（看到红线只看红）", "scorecard.agenda_only_red"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "metric_count": len(metrics), "red_items": reds,
            "checks": checks}


def _ids(data: Any) -> Dict[str, Any]:
    t = c.load_thresholds()["companyos"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}
    issues = data.get("issues") or []
    checks.append(_ck(bool(issues), "问题清单非空", "ids.issues"))

    for i, x in enumerate(issues):
        name = x.get("problem", f"issue[{i}]")
        checks.append(_ck(bool(x.get("problem")), f"[{name}] 真问题已定义",
                          f"ids.{i}.identify"))
        checks.append(_ck(bool(x.get("owner")) and bool(x.get("action"))
                          and bool(x.get("due_date")),
                          f"[{name}] 一个 owner + 一个动作 + 一个到期日",
                          f"ids.{i}.solve"))
        tb = x.get("timebox_min")
        checks.append(_ck(isinstance(tb, (int, float)) and tb <= t["ids_timebox_min"],
                          f"[{name}] 单议题 ≤{t['ids_timebox_min']}min（实际 {tb}）",
                          f"ids.{i}.timebox"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "issue_count": len(issues), "checks": checks}


def _freeze(data: Any) -> Dict[str, Any]:
    """冷却锁：募资 30d / 定价 60d / 市场进出 & 战略 pivot 90d / 裁员 30d。
    锁定期间拒绝重议，除非杀死标准触发或创始人显式 release（永久留痕）。"""
    t = c.load_thresholds()["companyos"]
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return {"ok": False, "checks": [_ck(False, "必须是 JSON 对象", "structure")]}

    dtype = data.get("decision_type", "")
    days = t["freeze_days"].get(dtype)
    checks.append(_ck(days is not None,
                      f"决策类型 {dtype} 在冷却锁范围 {list(t['freeze_days'])}",
                      "freeze.type"))
    if days is None:
        return {"ok": False, "decision_type": dtype, "checks": checks}

    elapsed = data.get("days_since_decided") or 0
    in_lock = elapsed < days
    re_decide = bool(data.get("re_decide_requested"))
    kill_triggered = bool(data.get("kill_criteria_triggered"))
    founder_release = bool(data.get("founder_release"))
    release_logged = bool(data.get("release_logged"))

    allowed = (not in_lock) or kill_triggered or (founder_release and release_logged)
    blocked = in_lock and re_decide and not allowed
    checks.append(_ck(not blocked,
                      (f"冷却期内（{elapsed}/{days}d）重议被拒：需杀死标准触发"
                       " 或创始人显式 release（永久留痕）") if blocked
                      else f"冷却判定通过（{elapsed}/{days}d）",
                      "freeze.blocked", "" if not blocked else "CRITICAL"))
    if founder_release and not release_logged:
        checks.append(_ck(False, "强制解锁必须永久留痕", "freeze.release_log",
                          "CRITICAL"))

    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "decision_type": dtype, "freeze_days": days,
            "days_elapsed": elapsed, "in_lock": in_lock,
            "re_decide_allowed": allowed, "checks": checks}
