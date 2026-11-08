# -*- coding: utf-8 -*-
"""S07 组织运营报表 —— 能力域 7。

整合自 frappe__hrms 的报表层 + `frappe-ui`（前端子模块，UI 来源登记）：
人员花名册汇总（headcount）、组织运营指标（流动率、出勤率、薪酬输入条数等）。
把「分组计数 → 指标实算」转成确定性校验：分组恒等（Σ分组 = 总数）、
指标字段白名单、流动率实算、数值非负。

关键立场：**报表是「经营事实的投影」，不是「经营判断」**。本角色只保证
计数与比例的口径正确、字段合法；**趋势解读、归因与「该不该裁/该不该招」的
结论交 R01 决策 + R06 分析**（红线 3 的延伸：不做组织决策结论）。

动作：
  headcount  花名册汇总校验（分组计数恒等 + 字段白名单）
  report     运营指标校验（流动率实算 + 数值非负）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "report"
DESC = "组织运营报表：headcount/report"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("headcount", "校验花名册汇总"), ("report", "校验运营指标")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "headcount":
        return _validate_headcount(data)
    if args.action == "report":
        return _validate_report(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_headcount(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["report"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", headcount=0)

    groups = data.get("groups") or []
    total = c._num(data.get("total"))
    ok_groups = isinstance(groups, list) and len(groups) > 0
    checks.append(_ck(ok_groups,
                      f"分组 ≥1（实际 "
                      f"{len(groups) if isinstance(groups, list) else 0}）",
                      "headcount.groups"))

    # 分组计数恒等：Σ分组计数 = total
    group_sum = int(sum(c._num(g.get("count")) for g in groups
                        if isinstance(g, dict)))
    checks.append(_ck(group_sum == int(total),
                      f"分组计数恒等：Σ分组 {group_sum} = 总数 {int(total)}",
                      "headcount.identity"))

    # 每分组的维度值非空
    bad_dim = [g.get("dim") or g.get("name") or "?" for g in groups
               if isinstance(g, dict)
               and not str(g.get("dim") or g.get("name") or "").strip()]
    checks.append(_ck(not bad_dim,
                      f"分组维度非空（缺 {bad_dim or '无'}）",
                      "headcount.dim"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        headcount=int(total), group_count=len(groups) if isinstance(groups, list) else 0,
        narrative=f"花名册汇总：总数 {int(total)}，{len(groups) if isinstance(groups, list) else 0} 组")


# --------------------------------------------------------------------------- #
def _validate_report(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["report"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", headcount=0)

    metrics = data.get("metrics") or {}
    ok_metrics = isinstance(metrics, dict) and len(metrics) > 0
    checks.append(_ck(ok_metrics, "指标对象非空", "report.metrics"))

    # 指标字段白名单：未知字段拦下（防止报表字段漂移）
    unknown = [k for k in (metrics.keys() if isinstance(metrics, dict) else [])
               if k not in th["metric_fields"]]
    checks.append(_ck(not unknown,
                      f"指标字段在白名单（越界 {unknown or '无'}）",
                      "report.field_whitelist"))

    # 数值非负（比率/计数/金额都不该为负）
    neg = [k for k, v in (metrics.items() if isinstance(metrics, dict) else [])
           if isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0]
    checks.append(_ck(not neg, f"指标非负（负值 {neg or '无'}）",
                      "report.nonneg"))

    # 流动率实算：若有期初人数与期内离职，流动率 = 离职/期初
    if "turnover_rate" in metrics and data.get("period_starts") is not None \
            and data.get("period_exits") is not None:
        starts = c._num(data.get("period_starts"))
        exits = c._num(data.get("period_exits"))
        exp = c.safe_div(exits, starts)
        got = c._num(metrics["turnover_rate"])
        checks.append(_ck(abs(got - exp) <= 0.0001,
                          f"流动率恒等：声明 {got:g} = 离职 {exits:g}/期初 "
                          f"{starts:g} = {exp:g}", "report.turnover"))
    else:
        checks.append(_ck(True, "未提供流动率口径，跳过实算", "report.turnover"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        headcount=0, metric_count=len(metrics) if isinstance(metrics, dict) else 0,
        narrative=f"运营报表：{len(metrics) if isinstance(metrics, dict) else 0} 项指标")
