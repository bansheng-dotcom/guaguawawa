# -*- coding: utf-8 -*-
"""S06 数据目录与口径接口 —— 能力域 6。

整合自 dbt（model/source 文档 + lineage，crates/dbt-lineage-core）+
airbyte catalog（stream schema）+ airflow lineage。把「表/字段/血缘/更新时间/
负责人」转成确定性校验：字段类型白名单、血缘引用完整性（上游表必须存在）、
owner 非空、更新时间口径声明、表名唯一。

关键立场：**目录是 R06 的唯一入口**——没有登记的表/字段，分析层就不该消费。
血缘里出现未登记的上游表 = 断链（无法溯源）；owner 缺失 = 出事没人认领。
本角色只交「数据目录与口径接口」，**不交「数字结论」**（红线 3 边界，交 R06）。

动作：
  entry    目录条目校验（表/字段/owner/更新时间）
  lineage  血缘校验（引用完整性 + 无环）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "catalog"
DESC = "数据目录与口径接口：entry/lineage"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("entry", "目录条目校验"), ("lineage", "血缘校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "entry":
        return _validate_entry(data)
    if args.action == "lineage":
        return _validate_lineage(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_entry(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["catalog"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", table="", field_count=0)

    table = str(data.get("table", "")).strip()
    checks.append(_ck(bool(table), "表名非空", "catalog.table"))

    # owner 非空（出事有人认领）
    checks.append(_ck(bool(str(data.get("owner", "")).strip()),
                      "owner 非空", "catalog.owner"))

    # 更新时间口径声明
    checks.append(_ck(bool(str(data.get("updated_at", "")).strip()),
                      "声明 updated_at（新鲜度口径）", "catalog.updated_at"))

    fields = data.get("fields") or []
    ok_fields = isinstance(fields, list) and len(fields) > 0
    checks.append(_ck(ok_fields,
                      f"字段 ≥1（实际 {len(fields) if isinstance(fields, list) else 0}）",
                      "catalog.fields"))

    # 字段类型白名单
    bad_type = [f.get("name") for f in (fields if isinstance(fields, list) else [])
                if isinstance(f, dict) and f.get("type") not in th["field_types"]]
    checks.append(_ck(not bad_type,
                      f"字段类型在白名单（越界 {bad_type or '无'}）",
                      "catalog.field_type"))

    # 字段名非空 + 唯一
    fnames = [str(f.get("name", "")) for f in (fields if isinstance(fields, list) else [])
              if isinstance(f, dict)]
    checks.append(_ck(all(x.strip() for x in fnames) and len(fnames) == len(set(fnames)),
                      "字段名非空且唯一", "catalog.field_unique"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        table=table, field_count=len(fields) if isinstance(fields, list) else 0,
        narrative=f"目录条目 {table}：{len(fields) if isinstance(fields, list) else 0} 字段")


# --------------------------------------------------------------------------- #
def _validate_lineage(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", table_count=0)

    tables = [str(t) for t in (data.get("tables") or []) if str(t).strip()]
    checks.append(_ck(len(tables) > 0, f"表 ≥1（实际 {len(tables)}）",
                      "lineage.tables"))
    checks.append(_ck(len(tables) == len(set(tables)), "表名唯一",
                      "lineage.unique_tables"))

    edges = data.get("edges") or []
    # 每条血缘边指向已声明表
    dangling = []
    for e in (edges if isinstance(edges, list) else []):
        if not (isinstance(e, list) and len(e) == 2):
            dangling.append(e)
            continue
        if str(e[0]) not in tables or str(e[1]) not in tables:
            dangling.append(e)
    checks.append(_ck(not dangling,
                      f"血缘引用完整（悬空 {dangling or '无'}）",
                      "lineage.ref_integrity"))

    # 血缘无环（Kahn）
    indeg = {t: 0 for t in tables}
    adj: Dict[str, List[str]] = {t: [] for t in tables}
    for e in (edges if isinstance(edges, list) else []):
        if isinstance(e, list) and len(e) == 2 and str(e[0]) in adj and str(e[1]) in indeg:
            adj[str(e[0])].append(str(e[1]))
            indeg[str(e[1])] += 1
    queue = [t for t in tables if indeg[t] == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    checks.append(_ck(seen == len(tables), "血缘无环", "lineage.acyclic"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        table_count=len(tables),
        edge_count=len(edges) if isinstance(edges, list) else 0,
        narrative=f"血缘：{len(tables)} 表，"
                  f"{len(edges) if isinstance(edges, list) else 0} 条边")
