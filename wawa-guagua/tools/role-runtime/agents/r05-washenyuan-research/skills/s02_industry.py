# -*- coding: utf-8 -*-
"""s02 行业与市场扫描（industry）：landscape / concentration 两动作。

- landscape：行业格局地图——players、segments、value_chain 校验与利润结构。
- concentration：市场集中度分析——HHI、CR4/CR8、市场结构判定。
阈值：thresholds.json → industry.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "industry"
DESC = "行业与市场扫描：格局、集中度、利润结构"

ACTIONS = {
    "landscape": "行业格局地图",
    "concentration": "市场集中度分析",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# landscape
# --------------------------------------------------------------------------- #
def landscape(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["industry"]
    player_roles = th["player_roles"]

    players = data.get("players") or []
    segments = data.get("segments") or []
    value_chain = data.get("value_chain") or []
    checks: List[Dict[str, Any]] = []

    if not players:
        checks.append(c.ck(False, "players 为空，无格局可构建", "industry:landscape", "CRITICAL"))

    segment_names = {str(s.get("name") or "") for s in segments}

    role_distribution: Dict[str, int] = {}
    for pl in players:
        name = str(pl.get("name") or "")
        role = str(pl.get("role") or "")
        seg = str(pl.get("segment") or "")

        if role not in player_roles:
            checks.append(c.ck(False, f"player {name!r} role={role!r} 不在白名单", "industry:player_role", "HIGH", **{"player": name}))
        else:
            role_distribution[role] = role_distribution.get(role, 0) + 1
            checks.append(c.ck(True, f"player {name!r} role={role} 合规", "industry:player_role", **{"player": name}))

        if seg and seg not in segment_names:
            checks.append(c.ck(False, f"player {name!r} 引用了不存在的 segment {seg!r}", "industry:player_segment", "HIGH", **{"player": name}))

    if not value_chain:
        checks.append(c.ck(False, "value_chain 为空，至少需 1 个环节", "industry:value_chain", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"value_chain 含 {len(value_chain)} 个环节", "industry:value_chain", **{"stages": len(value_chain)}))

    profit_structure: List[Dict[str, Any]] = []
    for stage in value_chain:
        stage_name = str(stage.get("stage") or "")
        stage_players = stage.get("players")
        margin = stage.get("margin_pct")
        profit_structure.append({"stage": stage_name, "players": stage_players, "margin_pct": margin})

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   player_count=len(players),
                   segment_count=len(segments),
                   value_chain_stages=len(value_chain),
                   profit_structure=profit_structure,
                   role_distribution=role_distribution,
                   verdict=verdict,
                   next="行业格局地图完整" if ok else "修复 player role/segment 与 value_chain 后重新 landscape",
                   )
    return out


# --------------------------------------------------------------------------- #
# concentration
# --------------------------------------------------------------------------- #
def concentration(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["industry"]
    hhi_th = th["hhi_thresholds"]
    cr_n_list = th["cr_n"]
    min_players = th["min_players"]

    shares = data.get("shares") or []
    checks: List[Dict[str, Any]] = []

    if not shares:
        checks.append(c.ck(False, "shares 为空，无集中度可计算", "industry:concentration", "CRITICAL"))

    if len(shares) < min_players:
        checks.append(c.ck(False, f"players 数量 {len(shares)} < 最低要求 {min_players}", "industry:min_players", "HIGH"))

    # 校验份额正数
    all_positive = True
    for s in shares:
        val = s.get("share")
        if val is None or not isinstance(val, (int, float)) or val <= 0:
            all_positive = False
            checks.append(c.ck(False, f"player {s.get('player')!r} share={val!r} 非正数", "industry:share_positive", "HIGH", **{"player": s.get("player")}))
    if all_positive and shares:
        checks.append(c.ck(True, "所有份额均为正数", "industry:share_positive"))

    total_share = sum(s.get("share", 0) for s in shares) if shares else 0
    if shares and abs(total_share - 100) > 5:
        checks.append(c.ck(False, f"份额总和 {total_share} 偏离 100 超过 ±5", "industry:share_sum", "HIGH", **{"total_share": total_share}))
    elif shares:
        checks.append(c.ck(True, f"份额总和 {total_share} 在 100±5 容差内", "industry:share_sum", **{"total_share": total_share}))

    # 计算 HHI
    hhi = sum(int(s.get("share", 0)) ** 2 for s in shares) if shares else 0

    # CR4 / CR8
    sorted_shares = sorted([s.get("share", 0) for s in shares], reverse=True) if shares else []
    cr4 = sum(sorted_shares[:4])
    cr8 = sum(sorted_shares[:8])

    # 市场结构判定
    if hhi < hhi_th["competitive"]:
        market_structure = "competitive"
    elif hhi < hhi_th["moderate"]:
        market_structure = "moderate"
    elif hhi < hhi_th["oligopoly"]:
        market_structure = "oligopoly"
    else:
        market_structure = "monopoly"

    checks.append(c.ck(True, f"HHI={hhi}，市场结构={market_structure}", "industry:hhi", **{"hhi": hhi, "market_structure": market_structure}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   hhi=hhi,
                   cr4=cr4,
                   cr8=cr8,
                   market_structure=market_structure,
                   total_share=total_share,
                   verdict=verdict,
                   next="集中度分析完成" if ok else "修复份额数据后重新 concentration",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "landscape":
        result = landscape(data)
    elif args.action == "concentration":
        result = concentration(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
