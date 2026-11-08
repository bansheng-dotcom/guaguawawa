# -*- coding: utf-8 -*-
"""S08 归因与 RevOps —— 能力域 8。

整合自 coreyhaines31__marketingskills（attribution / revops）。
把「归因与 RevOps」从口头建议转成确定性校验：归因模型枚举、去重口径（不跨平台
求和）、埋点需求字段白名单、CAC/LTV/回收期/ROI 算术实算。

动作：
  attribution  归因（模型枚举 + 去重口径 + 埋点字段）
  roi          ROI 复盘（CAC/LTV/回收期/ROI 实算）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "revops"
DESC = "归因与 RevOps：attribution/roi"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    b = act.add_parser("attribution", help="校验归因方案")
    b.add_argument("--input", required=True)
    u = act.add_parser("roi", help="校验 ROI 复盘")
    u.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "attribution":
        return _validate_attribution(data)
    if args.action == "roi":
        return _validate_roi(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_attribution(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    model = data.get("model")
    ok_model = model in th["revops"]["attribution_models"]
    checks.append(_ck(ok_model, f"归因模型 model={model!r} 在白名单", "revops.model"))
    if not ok_model:
        return c.result(checks, ok=False, verdict="FAIL", model=model, field_count=0)

    # 去重口径：不得跨平台求和（dedup 必须声明单一真源）
    dedup = data.get("dedup_source")
    ok_dedup = bool(str(dedup or "").strip())
    checks.append(_ck(ok_dedup, "去重口径声明单一真源（不跨平台求和）", "revops.dedup"))

    fields = data.get("tracking_fields")
    want = th["revops"]["tracking_fields"]
    ok_fields = isinstance(fields, list) and len(fields) > 0
    checks.append(_ck(ok_fields,
                      f"埋点字段 ≥1（实际 {len(fields) if isinstance(fields, list) else 0}）",
                      "revops.fields"))
    if ok_fields:
        bad = [f for f in fields if f not in want]
        checks.append(_ck(not bad, f"埋点字段在白名单（越界 {bad or '无'}）",
                          "revops.field_enum"))

    ok = ok_model and ok_dedup and ok_fields and (
        not ok_fields or not any(f not in want for f in fields))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    model=model, field_count=len(fields) if isinstance(fields, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_roi(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    def num(k):
        v = data.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    arpa, gm, churn = num("arpa"), num("gross_margin"), num("churn_rate")
    spend, new_customers = num("spend"), num("new_customers")

    ok_nums = all(v is not None for v in (arpa, gm, churn, spend, new_customers))
    checks.append(_ck(ok_nums, "ROI 复盘数字字段齐备", "roi.fields"))
    if not ok_nums:
        return c.result(checks, ok=False, verdict="FAIL", ltv=None, cac=None,
                        payback_months=None, roi=None)

    ltv = c.safe_div(arpa * gm, churn)
    cac = c.safe_div(spend, new_customers)
    payback = c.safe_div(cac, (arpa * gm)) if (arpa and gm) else None
    roi = c.safe_div(ltv - cac, cac)

    checks.append(_ck(churn > 0, f"churn_rate={churn} 为正", "roi.churn"))
    checks.append(_ck(new_customers > 0, f"new_customers={new_customers} 为正",
                      "roi.customers"))

    healthy = th["revops"]["ltv_cac_healthy"]
    ltv_cac = c.safe_div(ltv, cac)
    checks.append(_ck(ltv_cac >= healthy,
                      f"LTV:CAC={ltv_cac} ≥ {healthy}", "roi.ltv_cac"))
    checks.append(_ck(roi >= 0, f"ROI={roi} 非负", "roi.roi"))

    ok = ok_nums and ltv_cac >= healthy and roi >= 0
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ltv=ltv, cac=cac, payback_months=payback, roi=roi, ltv_cac=ltv_cac)
