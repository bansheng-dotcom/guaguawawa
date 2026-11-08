# -*- coding: utf-8 -*-
"""S06 主数据与权限 —— 能力域 6。

整合自 frappe__erpnext 的主数据与权限体系：
  - Item / Supplier / Warehouse / Customer / UOM / Price List 六类主数据
  - role profile：buyer（采购）/ warehouse_keeper（仓管）/ sales（销售）/
    accountant（会计）/ auditor（审计）/ admin（管理员）
  - 文档级权限动作：read/create/write/delete/submit/amend/cancel

关键立场：**权限是 ERP 的「谁能在哪张单上做什么」的硬边界**。本门禁只做
静态校验：主数据编码合规、权限动作在白名单、职责分离（SoD）冲突识别
（同一角色不能既 create 又 delete 同一文档，防「自己录自己删」）。
审计/税务/法务归 R03；本角色不做真实授权，只产出权限矩阵工件。

动作：
  master_data   主数据编码与类型校验
  permission    权限矩阵与职责分离校验
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "masterdata"
DESC = "主数据与权限：master_data/permission"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("master_data", help="校验主数据编码与类型")
    a.add_argument("--input", required=True)
    b = act.add_parser("permission", help="校验权限矩阵与职责分离")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"master_data": _validate_master_data,
          "permission": _validate_permission}.get(args.action)
    if fn is None:
        return {"error": f"未知动作: {args.action}"}
    return fn(data)


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_master_data(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["masterdata"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", master_count=0)

    records = data.get("records")
    if not isinstance(records, list) or not records:
        return c.result([_ck(False, "records 必须是非空列表", "master.list")],
                        ok=False, verdict="FAIL", master_count=0)

    bad_type = [r.get("code") for r in records if isinstance(r, dict)
                and r.get("type") not in th["master_types"]]
    checks.append(_ck(not bad_type, f"主数据类型在白名单（越界 {bad_type or '无'}）",
                      "master.type"))

    # 编码合规：主数据 code 必须符合白名单字符集（防空格/中文/超长编码污染外键）
    pat = th["code_pattern"]
    bad_code = []
    for r in records:
        if not isinstance(r, dict):
            continue
        code = str(r.get("code", "")).strip()
        if not code or not re.match(pat, code):
            bad_code.append(code or "(空)")
    checks.append(_ck(not bad_code, f"主数据编码合规（异常 {bad_code or '无'}）",
                      "master.code"))

    # 唯一性：主数据编码在同一类型内不得重复
    seen: Dict[str, set] = {}
    dup = []
    for r in records:
        if not isinstance(r, dict):
            continue
        key = (r.get("type"), str(r.get("code", "")).strip())
        if key[0] and key[1]:
            seen.setdefault(key, set()).add(id(r))
            if len(seen[key]) > 1:
                dup.append(f"{key[0]}:{key[1]}")
    checks.append(_ck(not dup, f"主数据编码唯一（重复 {dup or '无'}）",
                      "master.unique"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        master_count=len(records),
        narrative=f"主数据 {len(records)} 条，编码与类型通过门禁")


# --------------------------------------------------------------------------- #
def _validate_permission(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["masterdata"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", matrix_count=0)

    matrix = data.get("matrix")
    if not isinstance(matrix, list) or not matrix:
        return c.result([_ck(False, "matrix 必须是非空列表", "permission.list")],
                        ok=False, verdict="FAIL", matrix_count=0)

    bad_role = [m.get("role") for m in matrix if isinstance(m, dict)
                and m.get("role") not in th["role_types"]]
    checks.append(_ck(not bad_role, f"角色在白名单（越界 {bad_role or '无'}）",
                      "permission.role"))

    bad_action = [m.get("action") for m in matrix if isinstance(m, dict)
                  and m.get("action") not in th["permission_actions"]]
    checks.append(_ck(not bad_action, f"权限动作在白名单（越界 {bad_action or '无'}）",
                      "permission.action"))

    # 职责分离（SoD）：同一角色对同一文档不得同时拥有冲突动作对
    sod_conflicts = []
    per_role_doc: Dict[tuple, set] = {}
    for m in matrix:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        doc = m.get("doctype")
        action = m.get("action")
        if role is None or doc is None or action is None:
            continue
        acts = per_role_doc.setdefault((role, doc), set())
        acts.add(action)
    for (role, doc), acts in per_role_doc.items():
        for a, b in th["sod_pairs"]:
            if a in acts and b in acts:
                sod_conflicts.append(f"{role}@{doc}:{a}+{b}")
    checks.append(_ck(not sod_conflicts,
                      f"无职责分离冲突（冲突 {sod_conflicts or '无'}）",
                      "permission.sod"))

    # 高危动作（delete/cancel）必须声明审计备注
    risky = [m.get("role") for m in matrix if isinstance(m, dict)
             and m.get("action") in th["high_risk_actions"]
             and not str(m.get("note", "")).strip()]
    checks.append(_ck(not risky,
                      f"高危动作声明审计备注（缺 {risky or '无'}）",
                      "permission.high_risk"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        matrix_count=len(matrix),
        narrative=f"权限矩阵 {len(matrix)} 条，SoD 与高危动作通过门禁")
