# -*- coding: utf-8 -*-
"""s05 市场规模测算（sizing）：size / sensitivity 两动作。

- size：TAM/SAM/SOM 测算——自上而下加总 + 自下而上乘法链双口径互证，
  场景化（serviceable_fraction × obtainable_share），方差超阈 FAIL。
- sensitivity：敏感性分析——每个 driver 的 swing/swing_pct，按影响排序出关键驱动。
阈值：thresholds.json → sizing.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "sizing"
DESC = "市场规模测算：TAM/SAM/SOM 双口径互证与敏感性"

ACTIONS = {
    "size": "TAM/SAM/SOM 场景化测算",
    "sensitivity": "关键驱动敏感性分析",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# size
# --------------------------------------------------------------------------- #
def size(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["sizing"]
    warn_pct = th["variance_warning_pct"]
    crit_pct = th["variance_critical_pct"]

    top_down = data.get("top_down") or {}
    bottom_up = data.get("bottom_up") or {}
    scenarios = data.get("scenarios") or []
    checks: List[Dict[str, Any]] = []

    components = top_down.get("components") or []
    if not components:
        checks.append(c.ck(False, "top_down.components 为空，自上而下口径不可算", "sizing:components", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"top_down 含 {len(components)} 个互斥分项", "sizing:components", **{"components": len(components)}))

    # 自上而下：互斥分项加总（覆盖去重守则由输入方负责声明互斥）
    tam_top = sum(float(comp.get("value", 0) or 0) for comp in components)

    # 自下而上：customer_count × addressable_fraction × annual_quantity × price_per_unit
    cc = bottom_up.get("customer_count")
    af = bottom_up.get("addressable_fraction")
    aq = bottom_up.get("annual_quantity")
    ppu = bottom_up.get("price_per_unit")
    for field, val in [("customer_count", cc), ("addressable_fraction", af),
                       ("annual_quantity", aq), ("price_per_unit", ppu)]:
        if val is None or not isinstance(val, (int, float)) or val < 0:
            checks.append(c.ck(False, f"bottom_up.{field}={val!r} 缺失或非正数", "sizing:bottom_up", "HIGH", **{"field": field}))
        else:
            checks.append(c.ck(True, f"bottom_up.{field}={val}", "sizing:bottom_up", **{"field": field}))

    # addressable_fraction 必须在 0-1
    if af is not None and isinstance(af, (int, float)) and not (0 <= af <= 1):
        checks.append(c.ck(False, f"addressable_fraction={af} 不在 [0,1]", "sizing:fraction_range", "HIGH"))
    elif af is not None:
        checks.append(c.ck(True, f"addressable_fraction={af} 在 [0,1]", "sizing:fraction_range"))

    tam_bottom = 0.0
    if all(isinstance(v, (int, float)) and v is not None
           for v in (cc, af, aq, ppu)) and None not in (cc, af, aq, ppu):
        tam_bottom = float(cc) * float(af) * float(aq) * float(ppu)

    # 双口径互证：variance = |top - bottom| / max(top, bottom)
    ref = max(tam_top, tam_bottom)
    variance = abs(tam_top - tam_bottom) / ref if ref > 0 else 0.0
    if ref > 0:
        if variance >= crit_pct:
            checks.append(c.ck(False, f"双口径方差 {round(variance, 4)} ≥ 临界阈 {crit_pct}，测算不可信", "sizing:variance", "CRITICAL", **{"variance": round(variance, 4)}))
        elif variance >= warn_pct:
            checks.append(c.ck(False, f"双口径方差 {round(variance, 4)} ≥ 预警阈 {warn_pct}", "sizing:variance", "HIGH", **{"variance": round(variance, 4)}))
        else:
            checks.append(c.ck(True, f"双口径方差 {round(variance, 4)} 在容差内（<{warn_pct}）", "sizing:variance", **{"variance": round(variance, 4)}))

    # TAM 取双口径均值（互证通过时两者接近，均值稳定）
    tam = (tam_top + tam_bottom) / 2 if (tam_top > 0 or tam_bottom > 0) else 0.0

    # 场景化 SAM/SOM
    by_scenario: List[Dict[str, Any]] = []
    if not scenarios:
        checks.append(c.ck(False, "scenarios 为空，无 SAM/SOM 可算", "sizing:scenarios", "HIGH"))
    for sc in scenarios:
        sc_name = str(sc.get("name") or "")
        sf = sc.get("serviceable_fraction")
        os_ = sc.get("obtainable_share")
        bad = False
        for field, val in [("serviceable_fraction", sf), ("obtainable_share", os_)]:
            if val is None or not isinstance(val, (int, float)) or not (0 <= val <= 1):
                bad = True
                checks.append(c.ck(False, f"scenario {sc_name!r} {field}={val!r} 缺失或不在 [0,1]", "sizing:scenario_fraction", "HIGH", **{"scenario": sc_name, "field": field}))
        if bad:
            continue
        sam = tam * float(sf)
        som = sam * float(os_)
        by_scenario.append({"scenario": sc_name, "serviceable_fraction": sf,
                            "obtainable_share": os_,
                            "sam": round(sam, 2), "som": round(som, 2)})
        checks.append(c.ck(True, f"scenario {sc_name!r}：SAM={round(sam, 2)} SOM={round(som, 2)}", "sizing:scenario", **{"scenario": sc_name}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   tam=round(tam, 2),
                   tam_top=round(tam_top, 2),
                   tam_bottom=round(tam_bottom, 2),
                   variance=round(variance, 4),
                   by_scenario=by_scenario,
                   verdict=verdict,
                   next="市场规模测算双口径互证通过" if ok else "修复分项/口径/场景参数后重新 size",
                   )
    return out


# --------------------------------------------------------------------------- #
# sensitivity
# --------------------------------------------------------------------------- #
def sensitivity(data: Dict[str, Any]) -> Dict[str, Any]:
    drivers = data.get("drivers") or []
    base_value = data.get("base_value")
    checks: List[Dict[str, Any]] = []

    if not drivers:
        checks.append(c.ck(False, "drivers 为空，无敏感性可分析", "sizing:sensitivity", "CRITICAL"))
    if base_value is None or not isinstance(base_value, (int, float)):
        checks.append(c.ck(False, f"base_value={base_value!r} 缺失或非数值", "sizing:base_value", "HIGH"))

    sensitivity_matrix: List[Dict[str, Any]] = []
    for d in drivers:
        name = str(d.get("name") or "")
        bv = d.get("base_value")
        low = d.get("low")
        high = d.get("high")
        if low is None or high is None or bv is None:
            checks.append(c.ck(False, f"driver {name!r} 缺 base_value/low/high", "sizing:driver_fields", "HIGH", **{"driver": name}))
            continue
        if low > high:
            checks.append(c.ck(False, f"driver {name!r} low={low} > high={high}", "sizing:driver_range", "HIGH", **{"driver": name}))
            continue
        if not (low <= bv <= high):
            checks.append(c.ck(False, f"driver {name!r} base_value={bv} 不在 [low={low}, high={high}] 区间", "sizing:driver_base", "HIGH", **{"driver": name}))
            continue
        swing = float(high) - float(low)
        swing_pct = swing / float(bv) if bv != 0 else 0.0
        sensitivity_matrix.append({"driver": name, "base_value": bv,
                                   "low": low, "high": high,
                                   "swing": round(swing, 4),
                                   "swing_pct": round(swing_pct, 4)})
        checks.append(c.ck(True, f"driver {name!r} swing={round(swing, 2)} swing_pct={round(swing_pct, 4)}", "sizing:driver", **{"driver": name}))

    # 关键驱动：按 swing_pct 降序取前 3
    key_drivers = [row["driver"] for row in
                   sorted(sensitivity_matrix, key=lambda r: r["swing_pct"], reverse=True)[:3]]

    if drivers and sensitivity_matrix:
        checks.append(c.ck(True, f"敏感性矩阵覆盖 {len(sensitivity_matrix)}/{len(drivers)} 个驱动", "sizing:matrix_coverage"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   sensitivity_matrix=sensitivity_matrix,
                   key_drivers=key_drivers,
                   verdict=verdict,
                   next="敏感性分析完成，关键驱动已排序" if ok else "修复 driver 区间与基数后重新 sensitivity",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "size":
        result = size(data)
    elif args.action == "sensitivity":
        result = sensitivity(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
