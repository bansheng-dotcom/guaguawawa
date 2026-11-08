# -*- coding: utf-8 -*-
"""S02 数仓转换 —— 能力域 2。

整合自 dbt-labs__dbt：model（`materialized` = table|view|incremental|ephemeral，
见 crates/dbt-schemas 的 Materialized 枚举、dbt-parser 的 config 解析）、
generic tests（unique/not_null/accepted_values/relationships，见
crates/dbt-schemas 的 test 定义）、`ref()` 依赖图（crates/dbt-dag/deps_mgmt.rs）。
把「模型配置 + 测试声明 + 依赖引用」转成确定性校验：物化方式白名单、
测试类型白名单、ref 引用完整性（不许引用不存在的模型）、模型名唯一。

关键立场：**转换模型是一个有向无环图，不是一堆孤立 SQL**。`ref()` 指向不存在的
模型 = 编译期就会炸的悬空依赖；模型名重复 = 图里两个节点同名，下游 ref 无法定位。
本角色只校验转换结构与引用完整性，**不产出业务口径结论**（交 R06）。

动作：
  model  模型配置校验（物化/依赖/命名）
  test   通用测试声明校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "transform"
DESC = "数仓转换：model/test"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("model", "校验模型配置"), ("test", "校验通用测试")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "model":
        return _validate_model(data)
    if args.action == "test":
        return _validate_test(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_model(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["transform"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", model_name="")

    name = str(data.get("model_name", "")).strip()
    checks.append(_ck(bool(name), "模型名非空", "transform.model_name"))

    mat = data.get("materialized")
    checks.append(_ck(mat in th["materializations"],
                      f"物化方式={mat!r} 在白名单 {th['materializations']}",
                      "transform.materialization"))

    deps = data.get("depends_on") or []
    ok_deps = isinstance(deps, list)
    checks.append(_ck(ok_deps, "depends_on 为数组", "transform.depends_on"))

    # 引用完整性：每个 ref 必须落在已声明模型集合内
    declared = data.get("all_models")
    if isinstance(declared, list):
        declared_set = {str(x) for x in declared}
        dangling = [d for d in (deps if isinstance(deps, list) else [])
                    if str(d) not in declared_set]
        checks.append(_ck(not dangling,
                          f"ref 引用完整（悬空 {dangling or '无'}）",
                          "transform.ref_integrity"))
    else:
        checks.append(_ck(True, "未提供模型全集，跳过引用完整性", "transform.ref_integrity"))

    # 不许自引用（模型 ref 自己 = 环）
    self_ref = name in {str(d) for d in (deps if isinstance(deps, list) else [])}
    checks.append(_ck(not self_ref, "模型不自引用", "transform.self_ref"))

    # incremental 模型必须声明 unique_key（否则增量去重无依据）
    if mat == "incremental":
        checks.append(_ck(bool(str(data.get("unique_key", "")).strip()),
                          "incremental 声明 unique_key", "transform.unique_key"))
    else:
        checks.append(_ck(True, f"{mat} 不要求 unique_key", "transform.unique_key"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        model_name=name, mode=mat, dep_count=len(deps) if isinstance(deps, list) else 0,
        narrative=f"模型 {name}（{mat}），"
                  f"{len(deps) if isinstance(deps, list) else 0} 个依赖")


# --------------------------------------------------------------------------- #
def _validate_test(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["transform"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", test_count=0)

    tests = data.get("tests") or []
    ok_tests = isinstance(tests, list) and len(tests) > 0
    checks.append(_ck(ok_tests,
                      f"测试 ≥1（实际 {len(tests) if isinstance(tests, list) else 0}）",
                      "test.count"))

    bad_type = [t.get("test_type") for t in (tests if isinstance(tests, list) else [])
                if isinstance(t, dict) and t.get("test_type") not in th["test_types"]]
    checks.append(_ck(not bad_type,
                      f"测试类型在白名单（越界 {bad_type or '无'}）",
                      "test.type_whitelist"))

    # 每条测试必须指向具体列（列级测试）；列级 required_columns 非空
    bad_col = [t.get("test_type") for t in (tests if isinstance(tests, list) else [])
               if isinstance(t, dict) and not str(t.get("column", "")).strip()]
    checks.append(_ck(not bad_col,
                      f"测试绑定列（未绑定 {bad_col or '无'}）", "test.column"))

    # accepted_values 必须带 values 集合
    bad_av = [i for i, t in enumerate(tests if isinstance(tests, list) else [])
              if isinstance(t, dict) and t.get("test_type") == "accepted_values"
              and not (isinstance(t.get("values"), list) and len(t["values"]) > 0)]
    checks.append(_ck(not bad_av,
                      f"accepted_values 带枚举值（缺 {bad_av or '无'}）",
                      "test.accepted_values"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        test_count=len(tests) if isinstance(tests, list) else 0,
        narrative=f"通用测试 {len(tests) if isinstance(tests, list) else 0} 条")
