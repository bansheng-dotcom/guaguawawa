# -*- coding: utf-8 -*-
"""s04 商业模式与变现（business）：canvas / monetize 两动作。

- canvas：商业模式画布——9 宫格完整性校验。
- monetize：变现模式与单位经济——毛利率、LTV/CAC、盈亏平衡。
阈值：thresholds.json → business.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "business"
DESC = "商业模式与变现：画布、单位经济"

ACTIONS = {
    "canvas": "商业模式画布",
    "monetize": "变现模式与单位经济",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# canvas
# --------------------------------------------------------------------------- #
def canvas(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["business"]
    required_blocks = th["canvas_blocks"]

    blocks = data.get("blocks") or {}
    checks: List[Dict[str, Any]] = []

    if not blocks:
        checks.append(c.ck(False, "blocks 为空，无画布可校验", "business:canvas", "CRITICAL"))

    fit_gaps: List[str] = []
    blocks_complete = 0

    for blk in required_blocks:
        val = blocks.get(blk)
        if val is None or (isinstance(val, str) and not val.strip()):
            fit_gaps.append(blk)
            checks.append(c.ck(False, f"画布块 {blk!r} 缺失或为空", "business:canvas_block", "HIGH", **{"block": blk}))
        else:
            blocks_complete += 1
            checks.append(c.ck(True, f"画布块 {blk!r} 就绪", "business:canvas_block", **{"block": blk}))

    # monetization_paths：与收入相关的块数
    revenue_blocks = ["revenue_streams", "value_propositions", "customer_segments"]
    monetization_paths = sum(1 for b in revenue_blocks if blocks.get(b) and str(blocks.get(b)).strip())

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   blocks_complete=blocks_complete,
                   fit_gaps=fit_gaps,
                   monetization_paths=monetization_paths,
                   verdict=verdict,
                   next="商业模式画布完整" if ok else "补齐缺失画布块后重新 canvas",
                   )
    return out


# --------------------------------------------------------------------------- #
# monetize
# --------------------------------------------------------------------------- #
def monetize(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["business"]
    monetization_types = th["monetization_types"]
    ltv_cac_healthy = th["ltv_cac_healthy"]
    ltv_cac_warning = th["ltv_cac_warning"]

    model = data.get("model") or {}
    checks: List[Dict[str, Any]] = []

    model_type = str(model.get("type") or "")
    pricing_tiers = model.get("pricing_tiers") or []
    unit_economics = model.get("unit_economics") or {}

    if not model:
        checks.append(c.ck(False, "model 为空，无变现模式可分析", "business:monetize", "CRITICAL"))

    # model.type 白名单
    if model_type not in monetization_types:
        checks.append(c.ck(False, f"model.type={model_type!r} 不在白名单", "business:model_type", "HIGH", **{"model_type": model_type}))
    else:
        checks.append(c.ck(True, f"model.type={model_type} 合规", "business:model_type", **{"model_type": model_type}))

    # unit_economics 必填字段
    required_ue = ["price", "cogs", "cac", "ltv"]
    for field in required_ue:
        if field not in unit_economics or unit_economics[field] is None:
            checks.append(c.ck(False, f"unit_economics 缺少字段 {field!r}", "business:unit_economics", "HIGH", **{"field": field}))
        else:
            checks.append(c.ck(True, f"unit_economics.{field}={unit_economics[field]}", "business:unit_economics", **{"field": field}))

    # 计算
    price = float(unit_economics.get("price", 0) or 0)
    cogs = float(unit_economics.get("cogs", 0) or 0)
    cac = float(unit_economics.get("cac", 0) or 0)
    ltv = float(unit_economics.get("ltv", 0) or 0)

    gross_margin = (price - cogs) / price if price > 0 else 0.0
    ltv_cac_ratio = ltv / cac if cac > 0 else 0.0
    break_even = cac / (price - cogs) if (price - cogs) > 0 else None

    # LTV/CAC 健康度检查
    if ltv_cac_ratio >= ltv_cac_healthy:
        checks.append(c.ck(True, f"LTV/CAC={round(ltv_cac_ratio, 2)} 健康（≥{ltv_cac_healthy}）", "business:ltv_cac", **{"ltv_cac_ratio": round(ltv_cac_ratio, 4)}))
    elif ltv_cac_ratio >= ltv_cac_warning:
        checks.append(c.ck(False, f"LTV/CAC={round(ltv_cac_ratio, 2)} 预警（≥{ltv_cac_warning} 但 <{ltv_cac_healthy}）", "business:ltv_cac", "HIGH", **{"ltv_cac_ratio": round(ltv_cac_ratio, 4)}))
    else:
        checks.append(c.ck(False, f"LTV/CAC={round(ltv_cac_ratio, 2)} 不健康（<{ltv_cac_warning}）", "business:ltv_cac", "CRITICAL", **{"ltv_cac_ratio": round(ltv_cac_ratio, 4)}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   gross_margin=round(gross_margin, 4),
                   ltv_cac_ratio=round(ltv_cac_ratio, 4),
                   break_even=round(break_even, 4) if break_even is not None else None,
                   verdict=verdict,
                   next="变现模式与单位经济健康" if ok else "修复 model type / unit_economics / LTV-CAC 后重新 monetize",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "canvas":
        result = canvas(data)
    elif args.action == "monetize":
        result = monetize(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
