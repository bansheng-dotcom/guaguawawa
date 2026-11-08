# -*- coding: utf-8 -*-
"""S07 运营报表 —— 能力域 7。

整合自 frappe__erpnext 的报表与查询口径：
  - 采购报表（PO 状态分布 / 供应商在途）
  - 库存报表（Bin 现值 / 物料周转）
  - 履约报表（SO 交付率 / 发货及时率）
  - 财务台账（发票应收应付 / 未结账款）

关键立场：**报表是「读已经发生的业务事实」，不是「下结论」**。本门禁只校验
报表结构（report_type/period/kpis 必填）与周期口径（YYYY / YYYY-MM / YYYY-Qn），
并保证每个 KPI 有「分子 / 分母 / 值」三要素，可复算。结论归 R06（数据分析）
或 R03（财务口径）；本角色产出的是**可复算的运营台账**。

动作：
  report   运营报表结构与 KPI 口径校验
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "report"
DESC = "运营报表：report"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("report", help="校验运营报表结构与 KPI 口径")
    a.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "report":
        return _validate_report(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_report(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["report"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", report_count=0)

    missing = [k for k in th["report_required"] if not data.get(k)]
    checks.append(_ck(not missing, f"报表必填齐备（缺 {missing or '无'}）",
                      "report.required"))

    report_type = data.get("report_type")
    checks.append(_ck(report_type in th["report_types"],
                      f"报表类型={report_type!r} 在白名单", "report.type"))

    period = str(data.get("period", "")).strip()
    period_ok = bool(re.match(th["period_pattern"], period))
    checks.append(_ck(period_ok, f"周期口径={period!r} 合规（YYYY/YYYY-MM/YYYY-Qn）",
                      "report.period"))

    kpis = data.get("kpis") or []
    if not isinstance(kpis, list) or not kpis:
        checks.append(_ck(False, "kpis 必须是非空列表", "report.kpis"))
        kpis = []
    else:
        checks.append(_ck(True, f"KPI {len(kpis)} 个", "report.kpis"))

    # KPI 三要素：每个 KPI 必须可复算（有值 + 分子分母，纯数量指标分母=1）
    bad_kpi = []
    for k in kpis:
        if not isinstance(k, dict):
            bad_kpi.append("(非对象)")
            continue
        val = c._num(k.get("value"))
        num = c._num(k.get("numerator", val))
        den = c._num(k.get("denominator", 1))
        if val <= 0 or den <= 0:
            bad_kpi.append(k.get("name", "?"))
    checks.append(_ck(not bad_kpi, f"KPI 值/分母为正（异常 {bad_kpi or '无'}）",
                      "report.kpi_valid"))

    # 可复算：value 应等于 numerator/denominator（容差 0.01）
    mismatch = []
    for k in kpis:
        if not isinstance(k, dict):
            continue
        num = c._num(k.get("numerator"))
        den = c._num(k.get("denominator"))
        if not num and not den:
            continue
        if den:
            expect = round(num / den, 4)
            val = round(c._num(k.get("value")), 4)
            if abs(val - expect) > 0.01:
                mismatch.append(k.get("name", "?"))
    checks.append(_ck(not mismatch,
                      f"KPI 可复算（value=numerator/denominator，异常 {mismatch or '无'}）",
                      "report.kpi_recompute"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        report_count=1, kpi_count=len(kpis),
        narrative=f"{report_type} 报表（{period}）：{len(kpis)} 个 KPI 可复算")
