# -*- coding: utf-8 -*-
"""S08 采购总拥有成本（analyze-procurement 的确定性落地）。

把采购分析里的 landed cost / TCO 公式做成可复算的计算器：
  compare    多份报价的 landed cost、landed unit cost、资金占用后的 effective unit cost 对比排序
  lifecycle  生命周期 TCO：acquisition + implementation + integration + operation + support
             + switching + expected_failure − credits − rebates − residual

规则出处：analyze-procurement/references/calculation-catalog.md（Landed cost / TCO 两节）
口径约束（上游明确要求）：
  - 可抵扣 VAT/GST 不计入经济成本（本实现用 nonrecoverable_tax 单独入账）；
  - 只在「发票价 + 运费」两项时不允许称之为 TCO（lifecycle 至少 3 类成本非零）；
  - 单位、币种、数量口径必须先对齐（compare 会校验币种一致）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "tco"
DESC = "采购总拥有成本：compare/lifecycle（landed cost + TCO）"

DUTY_MAX = 50.0
LEAD_DAYS_WARN = 60
DEFECT_WARN = 2.0


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    cp = act.add_parser("compare", help="多报价 landed/effective unit cost 对比")
    cp.add_argument("--input", required=True)
    lc = act.add_parser("lifecycle", help="生命周期 TCO 汇总")
    lc.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    return _compare(data) if args.action == "compare" else _lifecycle(data)


# --------------------------------------------------------------------------- #
def _num(item: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(item.get(key, default) or 0)
    except (TypeError, ValueError):
        return 0.0


def _compare(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    quotes = data.get("quotes")
    if not isinstance(quotes, list) or not quotes:
        return c.result([_ck(False, "quotes ≥1", "tco.quotes")], verdict="FAIL")

    rate = _num(data, "annual_rate_pct", 0.0)
    checks.append(_ck(0 <= rate <= 30, f"资金年化 0–30%（{rate}%）", "tco.rate", warn=(rate > 15)))

    currencies = {str(q.get("currency", "CNY")).upper() for q in quotes if isinstance(q, dict)}
    checks.append(_ck(len(currencies) <= 1,
                      f"报价币种一致（{currencies or 'CNY'}，混合币种须先按 FX 归一）",
                      "tco.currency"))

    rows = []
    for i, q in enumerate(quotes):
        if not isinstance(q, dict):
            checks.append(_ck(False, f"quotes[{i}] 非对象", "tco.quotes"))
            continue
        supplier = str(q.get("supplier", f"quote-{i + 1}")).strip()
        unit = _num(q, "unit_price")
        qty = _num(q, "qty")
        moq = _num(q, "moq")
        defects = _num(q, "defects_pct")
        duty_pct = _num(q, "duty_pct")
        lead = _num(q, "lead_days")
        terms = _num(q, "payment_terms_days")

        checks.append(_ck(unit > 0, f"{supplier} 单价 >0（{unit}）", "tco.unit_price"))
        checks.append(_ck(qty > 0, f"{supplier} 数量 >0（{qty}）", "tco.qty"))
        checks.append(_ck(0 <= duty_pct <= DUTY_MAX,
                          f"{supplier} 关税率 0–{DUTY_MAX:.0f}%（{duty_pct}%）", "tco.duty"))
        checks.append(_ck(0 <= defects < 100, f"{supplier} 不良率 0–100%（{defects}%）",
                          "tco.defects"))
        if qty <= 0 or unit <= 0:
            continue

        goods = unit * qty
        duty = goods * duty_pct / 100
        origin = _num(q, "origin_charges")
        freight = _num(q, "main_freight")
        insurance = _num(q, "insurance")
        tax = _num(q, "nonrecoverable_tax")
        brokerage = _num(q, "brokerage")
        destination = _num(q, "destination_charges")
        accessorials = _num(q, "accessorials")
        landed = goods + origin + freight + insurance + duty + tax + brokerage + destination + accessorials
        usable = qty * (1 - defects / 100)
        landed_unit = landed / usable if usable > 0 else 0.0
        financing = landed * rate / 100 * terms / 365
        effective_unit = (landed + financing) / usable if usable > 0 else 0.0

        checks.append(_ck(usable > 0, f"{supplier} 可用数量 >0（{usable:.0f}）", "tco.usable"))
        checks.append(_ck(not (moq and moq > qty),
                          f"{supplier} MOQ ≤ 采购量（MOQ {moq:g} / 量 {qty:g}）",
                          "tco.moq", warn=bool(moq and moq > qty)))
        checks.append(_ck(freight + insurance + duty > 0,
                          f"{supplier} landed cost 含运费/保险/关税（勿只用货值比较）",
                          "tco.landed_components", warn=True))
        checks.append(_ck(lead <= LEAD_DAYS_WARN or lead == 0,
                          f"{supplier} 交期 ≤{LEAD_DAYS_WARN} 天（{lead:g}）",
                          "tco.lead", warn=(lead > LEAD_DAYS_WARN)))
        checks.append(_ck(defects <= DEFECT_WARN,
                          f"{supplier} 不良率 ≤{DEFECT_WARN}%（{defects:g}%）",
                          "tco.quality", warn=(defects > DEFECT_WARN)))

        rows.append({"supplier": supplier, "currency": str(q.get("currency", "CNY")).upper(),
                     "goods": round(goods, 2), "duty": round(duty, 2),
                     "landed_cost": round(landed, 2), "usable_qty": round(usable, 2),
                     "landed_unit_cost": round(landed_unit, 2),
                     "financing_cost": round(financing, 2),
                     "effective_unit_cost": round(effective_unit, 2),
                     "lead_days": lead})

    rows.sort(key=lambda r: r["effective_unit_cost"])
    if rows:
        best = rows[0]
        second = rows[1] if len(rows) > 1 else None
        gap = (round((second["effective_unit_cost"] - best["effective_unit_cost"])
                     / second["effective_unit_cost"] * 100, 1) if second else None)
        gap_text = f"较次优低 {gap}%" if gap is not None else "仅一份报价"
        checks.append(_ck(True, f"最优 {best['supplier']}（{gap_text}）", "tco.rank"))
    ok = all(x["ok"] for x in checks if x["sev"] == "BLOCKER")
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ranked=rows, best=rows[0] if rows else None,
                    next=("按 effective_unit_cost 排序谈判；MOQ/交期/质量旗标一并谈" if ok
                          else "补齐单价/数量/关税口径后重算"))


def _lifecycle(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    components = ["acquisition", "implementation", "integration", "operation", "support",
                  "switching", "expected_failure"]
    positives = {k: _num(data, k) for k in components}
    negatives = {k: _num(data, k) for k in ("credits", "rebates", "residual")}
    present = [k for k, v in positives.items() if v > 0]
    checks = [_ck(len(present) >= 3,
                  f"至少 3 类成本非零才算 TCO（当前 {present or '无'}，仅发票+运费不算 TCO）",
                  "tco.lifecycle_components")]
    checks.append(_ck(_num(data, "acquisition") > 0, "acquisition >0", "tco.acquisition"))
    total = sum(positives.values()) - sum(negatives.values())
    checks.append(_ck(total > 0, f"TCO 合计 >0（{total:.2f}）", "tco.total"))
    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    tco=round(total, 2), components=positives, offsets=negatives,
                    note="可抵扣 VAT/GST 不计入经济成本；committed-but-unused 容量需单列",
                    next="TCO 可用于审批件；同时给出 baseline 与 savings 对比")


def _validate_compare(data):
    return _compare(data)


def _validate_lifecycle(data):
    return _lifecycle(data)

