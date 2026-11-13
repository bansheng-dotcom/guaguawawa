# -*- coding: utf-8 -*-
"""S05 薪酬准备 —— 能力域 5。**L4 制度性幻觉防护的主战场。**

整合自 frappe__hrms：`hr/doctype/salary_structure/salary_structure.json`
（payroll_frequency = Monthly | Fortnightly | Bimonthly | Weekly | Daily）、
`hr/doctype/salary_component/salary_component.json`
（type = Earning | Deduction | Employer Contribution）、
`hr/doctype/salary_slip/salary_slip.json`（gross_pay / total_deduction / net_pay
的数量勾稽）。把「薪酬输入 → 组成项 → 净额」转成确定性校验。

关键立场（红线 3 + L4 制度性幻觉防护）：**薪酬是「准备」，不是「发放」**。
- 本角色产出**薪酬输入表与核算草稿**，交 R03（税务/合规）+ 外部专业人士复核，
  绝不直接发薪、绝不代发工资、绝不打款（红线 1）。
- **不得凭空发明制度性字段**：Lance/免税额度/税率/社保基数等「看起来专业」
  的字段，必须能在输入表找到源头（source）。找不到源头 = 制度性幻觉 → 拦下。
- **净额恒等**：gross_pay − Σdeduction ± Σemployer_contribution 的分组必须对得上，
  容差 0.01（分位误差）。数字对不上，后面所有报表都是错的。

动作：
  input  薪酬输入表校验（频率白名单 + 组成项类型 + 字段来源可追溯）
  calc   核算记录校验（净额恒等 + 考勤勾稽 + 无凭空字段）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "payroll"
DESC = "薪酬准备：input/calc"

# 制度性字段关键词：出现但无 source → 幻觉（L4 防护）
_SYSTEM_FIELD_TOKENS = ["lance", "免税额度", "税率", "社保基数", "公积金基数",
                        "专项附加扣除", "起征点", "速算扣除"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("input", "校验薪酬输入表"), ("calc", "校验核算记录")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "input":
        return _validate_input(data)
    if args.action == "calc":
        return _validate_calc(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_input(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["payroll"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", payroll_input_count=0)

    freq = data.get("payroll_frequency")
    checks.append(_ck(freq in th["frequencies"],
                      f"发放频率={freq!r} 在白名单", "payroll.frequency"))

    emp = str(data.get("employee", "")).strip()
    checks.append(_ck(bool(emp), "薪酬关联人员非空", "payroll.employee"))

    comps = data.get("components") or []
    ok_comps = isinstance(comps, list) and len(comps) > 0
    checks.append(_ck(ok_comps,
                      f"组成项 ≥1（实际 "
                      f"{len(comps) if isinstance(comps, list) else 0}）",
                      "payroll.components"))

    # 组成项类型白名单 + 每项必须有来源（source），无来源 = 凭空
    bad_type: List[str] = []
    no_source: List[str] = []
    for comp in comps if isinstance(comps, list) else []:
        if not isinstance(comp, dict):
            continue
        if comp.get("type") not in th["component_types"]:
            bad_type.append(str(comp.get("name", "?")))
        if not str(comp.get("source", "")).strip():
            no_source.append(str(comp.get("name", "?")))
    checks.append(_ck(not bad_type,
                      f"组成项类型合法（越界 {bad_type or '无'}）",
                      "payroll.component_type"))
    checks.append(_ck(not no_source,
                      f"组成项均有来源 source（缺 {no_source or '无'}）",
                      "payroll.component_source"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        payroll_input_count=1, payroll_frequency=freq,
        component_count=len(comps) if isinstance(comps, list) else 0,
        narrative=(f"薪酬输入 {emp}（{freq}）"
                   f"{len(comps) if isinstance(comps, list) else 0} 项"))


# --------------------------------------------------------------------------- #
def _validate_calc(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["payroll"]
    tol = th["tolerance"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", payroll_input_count=0)

    comps = data.get("components") or []
    earnings = sum(c.money(x.get("amount")) for x in comps
                   if isinstance(x, dict) and x.get("type") == "Earning")
    deductions = sum(c.money(x.get("amount")) for x in comps
                     if isinstance(x, dict) and x.get("type") == "Deduction")
    employer = sum(c.money(x.get("amount")) for x in comps
                   if isinstance(x, dict)
                   and x.get("type") == "Employer Contribution")
    earnings = round(earnings, 2)
    deductions = round(deductions, 2)

    gross = c.money(data.get("gross_pay"))
    net = c.money(data.get("net_pay"))
    exp_gross = earnings
    exp_net = round(earnings - deductions, 2)

    # 毛额恒等：gross_pay = ΣEarning
    checks.append(_ck(abs(gross - exp_gross) <= tol,
                      f"毛额恒等：声明 {gross:g} = ΣEarning {exp_gross:g}",
                      "payroll.gross"))
    # 净额恒等：net_pay = ΣEarning − ΣDeduction
    checks.append(_ck(abs(net - exp_net) <= tol,
                      f"净额恒等：声明 {net:g} = 毛额 {exp_gross:g} − 扣除 "
                      f"{deductions:g} = {exp_net:g}", "payroll.net"))

    # 考勤勾稽：payment_days ≤ total_working_days
    if data.get("payment_days") is not None and data.get("total_working_days") is not None:
        pd = c._num(data.get("payment_days"))
        twd = c._num(data.get("total_working_days"))
        checks.append(_ck(pd <= twd,
                          f"计薪天数 {pd:g} ≤ 计薪基数 {twd:g}", "payroll.days"))
    else:
        checks.append(_ck(True, "未提供计薪天数，跳过勾稽", "payroll.days"))

    # L4 制度性幻觉防护：出现制度性字段必须能在输入表找到源头
    used = data.get("system_fields") or []
    missing_src: List[str] = []
    if isinstance(used, list):
        for sf in used:
            if not isinstance(sf, dict):
                continue
            if not str(sf.get("source", "")).strip():
                missing_src.append(str(sf.get("name", "?")))
    checks.append(_ck(not missing_src,
                      f"制度性字段均可溯源（凭空 {missing_src or '无'}）",
                      "payroll.system_source"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        payroll_input_count=1, gross_pay=gross, net_pay=net,
        total_deduction=deductions, employer_contribution=round(employer, 2),
        narrative=(f"核算：毛额 {gross:g} 扣除 {deductions:g} 净额 {net:g}"
                   "（待 R03/外部复核，非发放）"))
