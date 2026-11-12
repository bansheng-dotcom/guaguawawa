# -*- coding: utf-8 -*-
"""S09 选品评分（smart-product-selector 的确定性落地）。

把选品规范里的「五维评分 + 利润红线 + 假设卡」变成可执行计算：
  score   五维打分（1–5）→ 归一化加权 → 综合分与推荐等级；推荐品必须有假设卡预期指标
  profit  单件利润测算：毛利率 <30% 警告、<15% 建议放弃（标注"仅供参考"）

规则出处：r14-wajiaoyi-commerce/references/external/smart-product-selector/SKILL.md
注意：上游文档五维权重写作 30/20/25/30/15（合计 120%），本实现按合计归一化，
      并在 checks 里显式提示这一口径问题，避免"照抄错误权重"。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "selection"
DESC = "选品评分：score/profit（五维加权 + 利润红线 + 假设卡门禁）"

DIMS = {"capacity": "市场容量", "growth": "增长趋势", "entry": "竞争可进入性",
        "margin": "利润空间", "supply": "供应链难度"}
DOC_WEIGHTS = {"capacity": 30, "growth": 20, "entry": 25, "margin": 30, "supply": 15}
GRADES = ((4.0, "强烈推荐"), (3.0, "值得尝试"), (2.0, "谨慎考虑"), (0.0, "建议放弃"))


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    s = act.add_parser("score", help="五维评分与推荐等级")
    s.add_argument("--input", required=True)
    pr = act.add_parser("profit", help="单件利润测算")
    pr.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    return _score(data) if args.action == "score" else _profit(data)


# --------------------------------------------------------------------------- #
def _weights() -> Dict[str, float]:
    total = sum(DOC_WEIGHTS.values())
    return {k: v / total for k, v in DOC_WEIGHTS.items()}


def _grade(score: float) -> str:
    for threshold, label in GRADES:
        if score >= threshold:
            return label
    return GRADES[-1][1]


def _score(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    products = data.get("products")
    if not isinstance(products, list) or not products:
        return c.result([_ck(False, "products ≥1", "selection.products")], verdict="FAIL")

    total = sum(DOC_WEIGHTS.values())
    checks.append(_ck(total == 100, f"权重合计（上游文档为 {total}%，已归一化）",
                      "selection.weights", warn=(total != 100)))
    weights = _weights()
    ranked = []
    for i, item in enumerate(products):
        if not isinstance(item, dict):
            checks.append(_ck(False, f"products[{i}] 非对象", "selection.products"))
            continue
        name = str(item.get("name", "")).strip()
        checks.append(_ck(bool(name), f"products[{i}] name 非空", "selection.name"))
        dims = item.get("dims") or {}
        dim_ok = True
        for key in DIMS:
            val = dims.get(key)
            if not isinstance(val, (int, float)) or not (1 <= float(val) <= 5):
                checks.append(_ck(False, f"{name or i} 维度 {key} 需 1–5（实际 {val}）",
                                  "selection.dims"))
                dim_ok = False
        if not dim_ok:
            continue

        score = round(sum(float(dims[k]) * weights[k] for k in DIMS), 2)
        grade = _grade(score)
        # 数据来源：上游要求每个数字标注来源类型，推荐品必须有依据
        sources = item.get("source_types") or []
        valid_sources = {"检索核实", "用户提供", "经验参考值"}
        checks.append(_ck(bool(sources) and set(sources) <= valid_sources,
                          f"{name} 数据来源标注合法（{sources or '缺失'}）", "selection.sources"))

        if grade in ("强烈推荐", "值得尝试"):
            hyp = item.get("hypothesis") or {}
            have = all(str(hyp.get(k, "")).strip() for k in ("click_rate", "cvr", "margin", "verify_at"))
            checks.append(_ck(have,
                              f"{name} 假设卡预期指标完整（SP-09：缺预期指标禁止交付）",
                              "selection.hypothesis"))
            checks.append(_ck(bool(item.get("risks")),
                              f"{name} 至少 1 条风险（{item.get('risks') or '缺失'}）",
                              "selection.risks"))
        ranked.append({"name": name, "score": score, "grade": grade,
                       "dims": {DIMS[k]: dims[k] for k in DIMS}})

    ranked.sort(key=lambda x: x["score"], reverse=True)
    checks.append(_ck(len(ranked) >= 1, f"有效评分 {len(ranked)} 个", "selection.ranked"))
    ok = all(x["ok"] for x in checks if x["sev"] != "WARN")
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ranked=ranked,
                    weights_used={DIMS[k]: round(v * 100, 1) for k, v in weights.items()},
                    next=("按排名推进；每个推荐品带假设卡上架验证" if ok
                          else "补齐维度/来源/假设卡后重算"))


def _profit(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    try:
        price = float(data.get("price", 0))
        cost = float(data.get("cost", 0))
        shipping = float(data.get("shipping", 0))
        packaging = float(data.get("packaging", 0))
        fee_pct = float(data.get("platform_fee_pct", 0))
        ad_pct = float(data.get("ad_pct", 0))
        return_pct = float(data.get("return_rate_pct", 0))
        other = float(data.get("other_cost", 0))
    except (TypeError, ValueError):
        return c.result([_ck(False, "价格/成本字段必须是数字", "profit.fields")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    checks.append(_ck(price > 0, f"售价 >0（{price}）", "profit.price"))
    checks.append(_ck(0 <= fee_pct <= 30, f"平台费率 0–30%（{fee_pct}%）", "profit.fee"))
    checks.append(_ck(0 <= ad_pct <= 50, f"推广费率 0–50%（{ad_pct}%）", "profit.ad"))
    checks.append(_ck(0 <= return_pct <= 50, f"退货率 0–50%（{return_pct}%）", "profit.return"))

    fee = price * fee_pct / 100
    ad = price * ad_pct / 100
    total_cost = cost + shipping + packaging + fee + ad + other
    profit = price - total_cost
    margin = (profit / price * 100) if price else 0.0
    roi = (profit / total_cost * 100) if total_cost else 0.0

    checks.append(_ck(margin >= 15, f"毛利率 ≥15%（实际 {margin:.1f}%，<15% 建议放弃）",
                      "profit.margin", warn=(15 <= margin < 30)))
    checks.append(_ck(margin >= 30, f"毛利率 ≥30%（当前 {margin:.1f}%，30% 为健康线）",
                      "profit.health", warn=(15 <= margin < 30)))
    ok = margin >= 15 and price > 0 and all(
        x["ok"] for x in checks if x["sev"] == "BLOCKER")
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    price=price, total_cost=round(total_cost, 2),
                    profit=round(profit, 2), margin_pct=round(margin, 1), roi_pct=round(roi, 1),
                    breakdown={"goods": cost, "shipping": shipping, "packaging": packaging,
                               "platform_fee": round(fee, 2), "ad": round(ad, 2), "other": other},
                    disclaimer="仅供参考，实际以真实采购价与经营情况为准",
                    next=("利润达标，可进五维评分" if ok else "低于 15% 红线：换价带或换品"))


def _validate_score(data):
    return _score(data)


def _validate_profit(data):
    return _profit(data)

