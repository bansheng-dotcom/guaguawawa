# -*- coding: utf-8 -*-
"""S01 指标与语义建模 —— 能力域 1（T5 语义↔数据真联动）。

整合自 data-analytics-skills 的 `semantic-model-builder`（dbt MetricFlow 三层：
entity → dimension → measure，加上独立 metrics 定义）与 `metric-reconciliation`
（口径对账）。

主张：**指标无口径即不可复算；语义模型必须能落到真实数据列上，否则就是幻觉**。

本技能把语义层做成五个确定性动作：
    validate  校验语义模型 YAML/JSON（必填字段 + 类型白名单 + 引用完整性 + 占位符）
    tree      把 metrics 按类型归类成指标树
    link      把 semantic_model 的 entity/dimension/measure 的 expr 联动到数据列（防幻觉）
    compute   真正对数据执行 measure 的 agg，验证「语义定义 ↔ 真实数据」一致
    reconcile 口径对账（两数容差比较 + 六根因提示）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "semantics"
DESC = "指标与语义建模：validate / tree / link / compute / reconcile"

# ---- dbt MetricFlow 白名单 -------------------------------------------------
VALID_AGG = {"sum", "count", "count_distinct", "avg", "min", "max"}
VALID_METRIC_TYPE = {"simple", "ratio", "cumulative", "derived"}
VALID_DIM_TYPE = {"categorical", "time", "numeric"}
VALID_ENTITY_TYPE = {"primary", "foreign", "unique", "natural"}
VALID_GRANULARITY = {"day", "week", "month", "quarter", "year"}
# 需要数值列的聚合
NUMERIC_AGG = {"sum", "avg", "min", "max"}
# 对账容差（%），沿用 reference 01 的阈值
TOLERANCE = {"ledger": 0.0, "finance": 0.1, "marketing": 1.0,
             "product": 2.0, "ml": 0.5}

_MEASURE_REQ = [("name", "name"), ("agg", "agg"), ("expr", "expr")]
_DIM_REQ = [("name", "name"), ("type", "type"), ("expr", "expr")]
_ENTITY_REQ = [("name", "name"), ("type", "type"), ("expr", "expr")]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    v = act.add_parser("validate", help="校验语义层 JSON（semantic_models + metrics）")
    v.add_argument("--input", required=True, help="语义模型 JSON 路径")
    v.add_argument("--strict", action="store_true", help="一并检查未填的 [REQUIRED] 占位符")

    t = act.add_parser("tree", help="把 metrics 按类型归类成指标树")
    t.add_argument("--input", required=True)

    lk = act.add_parser("link", help="把语义模型 expr 联动到数据列（防幻觉）")
    lk.add_argument("--input", required=True, help="语义模型 JSON")
    lk.add_argument("--data", required=True, help="实际数据 CSV")

    cp = act.add_parser("compute", help="对真实数据执行 measure 的 agg，验证口径")
    cp.add_argument("--input", required=True, help="语义模型 JSON")
    cp.add_argument("--data", required=True, help="实际数据 CSV")

    r = act.add_parser("reconcile", help="口径对账：比较两数是否在容差内")
    r.add_argument("--a", type=float, required=True)
    r.add_argument("--b", type=float, required=True)
    r.add_argument("--domain", default="product", choices=list(TOLERANCE))
    r.add_argument("--label", default="metric", help="指标名")


def run(args) -> Dict[str, Any]:
    if args.action == "validate":
        return _validate(c.load_json(args.input), strict=getattr(args, "strict", False))
    if args.action == "tree":
        return _tree(c.load_json(args.input))
    if args.action == "link":
        return _link(c.load_json(args.input), c.load_csv(args.data))
    if args.action == "compute":
        return _compute(c.load_json(args.input), c.load_csv(args.data))
    if args.action == "reconcile":
        return _reconcile(args.a, args.b, args.domain, args.label)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
# 结构归一：把 semantic_models 里的 measures 拉平成 {name: measure}，供引用检查/计算
# --------------------------------------------------------------------------- #
def _all_measures(model: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(model, dict):
        return out
    for sm in model.get("semantic_models", []) or []:
        for m in sm.get("measures", []) or []:
            if m.get("name"):
                out[m["name"]] = m
    return out


def _all_dimensions(model: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(model, dict):
        return out
    for sm in model.get("semantic_models", []) or []:
        for d in sm.get("dimensions", []) or []:
            if d.get("name"):
                out[d["name"]] = d
    return out


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #
def _validate(model: Any, strict: bool = False) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(model, dict):
        return {"ok": False, "errors": ["语义模型必须是 JSON 对象"]}
    if not any(k in model for k in ("semantic_models", "metrics")):
        errors.append("文件必须含 semantic_models 或 metrics 至少其一")

    sms = model.get("semantic_models", []) or []
    sm_names = set()
    for sm in sms:
        sn = sm.get("name", "")
        if not sn:
            errors.append("semantic_model 缺 name")
        elif sn in sm_names:
            errors.append(f"semantic_model[{sn}] 重名")
        sm_names.add(sn)

        for e in sm.get("entities", []) or []:
            _req(errors, f"entity", e, _ENTITY_REQ)
            if e.get("type") and e["type"] not in VALID_ENTITY_TYPE:
                errors.append(f"entity[{e.get('name')}] type 非法 {e['type']!r}")

        for d in sm.get("dimensions", []) or []:
            _req(errors, "dimension", d, _DIM_REQ)
            if d.get("type") and d["type"] not in VALID_DIM_TYPE:
                errors.append(f"dimension[{d.get('name')}] type 非法 {d['type']!r}")
            # 时间维度必须有 time_granularity
            if d.get("type") == "time":
                g = (d.get("type_params") or {}).get("time_granularity")
                if g not in VALID_GRANULARITY:
                    errors.append(f"dimension[{d.get('name')}] 时间维度缺合法 time_granularity")

        for m in sm.get("measures", []) or []:
            _req(errors, "measure", m, _MEASURE_REQ)
            if m.get("agg") and m["agg"] not in VALID_AGG:
                errors.append(f"measure[{m.get('name')}] agg 非法 {m['agg']!r}")

    measure_names = set(_all_measures(model))
    # metrics 引用完整性：metric 的 type_params 必须引用已定义的 measure
    for mt in model.get("metrics", []) or []:
        name = mt.get("name", "")
        if not name:
            errors.append("metric 缺 name")
            continue
        mtype = mt.get("type", "")
        if mtype not in VALID_METRIC_TYPE:
            errors.append(f"metric[{name}] type 非法 {mtype!r}")
            continue
        tp = mt.get("type_params") or {}
        if mtype == "simple":
            _chk_ref(errors, name, (tp.get("measure") or {}).get("name"),
                     measure_names, "measure")
        elif mtype == "ratio":
            _chk_ref(errors, name, (tp.get("numerator") or {}).get("name"),
                     measure_names, "numerator.measure")
            _chk_ref(errors, name, (tp.get("denominator") or {}).get("name"),
                     measure_names, "denominator.measure")
        elif mtype == "cumulative":
            _chk_ref(errors, name, (tp.get("measure") or {}).get("name"),
                     measure_names, "measure")
        elif mtype == "derived":
            if not tp.get("expr"):
                errors.append(f"metric[{name}] derived 缺 expr")
            for ref in tp.get("metrics", []) or []:
                _chk_ref(errors, name, ref.get("name"), set(
                    x.get("name") for x in model.get("metrics", []) if x.get("name")),
                    "metric")

    if strict:
        errors += _find_placeholders(model)

    return {
        "ok": not errors,
        "semantic_models": len(sms),
        "metrics": len(model.get("metrics", []) or []),
        "measures": len(measure_names),
        "errors": errors,
        "valid_agg": sorted(VALID_AGG),
        "valid_metric_type": sorted(VALID_METRIC_TYPE),
        "valid_dim_type": sorted(VALID_DIM_TYPE),
        "valid_entity_type": sorted(VALID_ENTITY_TYPE),
    }


def _req(errors: List[str], kind: str, obj: Dict[str, Any],
         fields: List[tuple]) -> None:
    name = obj.get("name", "<unnamed>")
    for f, _ in fields:
        if not obj.get(f):
            errors.append(f"{kind}['{name}'] 缺必填字段 '{f}'")


def _chk_ref(errors: List[str], metric: str, ref: Any, defined: set,
             what: str) -> None:
    if not ref:
        errors.append(f"metric[{metric}] 缺 {what} 引用")
    elif ref not in defined:
        errors.append(f"metric[{metric}] 引用未定义的 {what} '{ref}'")


def _find_placeholders(obj: Any, path: str = "") -> List[str]:
    out: List[str] = []
    if isinstance(obj, str):
        if "[REQUIRED]" in obj:
            out.append(f"{path}: 未填 [REQUIRED] 占位符")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out += _find_placeholders(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _find_placeholders(v, f"{path}[{i}]")
    return out


# --------------------------------------------------------------------------- #
# tree
# --------------------------------------------------------------------------- #
def _tree(model: Any) -> Dict[str, Any]:
    metrics = model.get("metrics", []) if isinstance(model, dict) else []
    by_type: Dict[str, List[str]] = {t: [] for t in VALID_METRIC_TYPE}
    by_type["unknown"] = []
    for m in metrics:
        t = m.get("type", "unknown")
        if t not in by_type:
            t = "unknown"
        by_type[t].append(m.get("name", ""))
    return {"metric_tree": by_type, "metric_count": len(metrics)}


# --------------------------------------------------------------------------- #
# link：语义模型 expr ↔ 数据列 真联动（防幻觉）
# --------------------------------------------------------------------------- #
def _link(model: Any, rows: List[Dict[str, str]]) -> Dict[str, Any]:
    cols = set(rows[0].keys()) if rows else set()
    links: List[Dict[str, Any]] = []
    hallucinated = 0
    for sm in model.get("semantic_models", []) or []:
        for e in sm.get("entities", []) or []:
            expr = e.get("expr", "")
            present = expr in cols
            if not present:
                hallucinated += 1
            links.append({"obj": "entity", "name": e.get("name"),
                          "expr": expr, "present": present})
        for d in sm.get("dimensions", []) or []:
            expr = d.get("expr", "")
            present = expr in cols
            decl = d.get("type")
            infer = c.infer_column_type(rows, expr) if present else None
            mismatch = None
            if present:
                if decl == "time" and infer != "time":
                    mismatch = {"declared": decl, "inferred": infer}
                elif decl == "numeric" and infer != "numeric":
                    mismatch = {"declared": decl, "inferred": infer}
            if not present:
                hallucinated += 1
            links.append({"obj": "dimension", "name": d.get("name"),
                          "expr": expr, "present": present,
                          "declared_type": decl, "inferred_type": infer,
                          "type_mismatch": mismatch})
        for m in sm.get("measures", []) or []:
            expr = m.get("expr", "")
            agg = m.get("agg")
            present = expr in cols
            if not present:
                hallucinated += 1
                computable = False
                reason = f"列缺失: {expr}"
            elif agg in NUMERIC_AGG:
                infer = c.infer_column_type(rows, expr)
                computable = (infer == "numeric")
                reason = (None if computable
                          else f"{agg} 需要数值列，实际推断为 {infer}")
            else:
                computable = True
                reason = None
            links.append({"obj": "measure", "name": m.get("name"),
                          "expr": expr, "agg": agg, "present": present,
                          "computable": computable, "reason": reason})

    return {"ok": hallucinated == 0,
            "columns_in_data": sorted(cols),
            "links": links,
            "hallucinated_count": hallucinated,
            "linked_count": len(links),
            "total_columns": len(cols),
            "note": "expr 引用的列必须在数据中存在（否则为语义幻觉）；measure 数值聚合须能算"}


# --------------------------------------------------------------------------- #
# compute：真正执行 measure agg，验证语义口径 ↔ 真实数据
# --------------------------------------------------------------------------- #
def _compute(model: Any, rows: List[Dict[str, str]]) -> Dict[str, Any]:
    computed: Dict[str, Any] = {}
    for sm in model.get("semantic_models", []) or []:
        for m in sm.get("measures", []) or []:
            computed[m["name"]] = _agg(rows, m.get("expr", ""), m.get("agg", ""))
    return {"computed_measures": computed, "measure_count": len(computed)}


def _agg(rows: List[Dict[str, str]], expr: str, agg: str) -> Any:
    if not expr or expr not in (rows[0] if rows else {}):
        return None
    if agg == "count":
        return sum(1 for r in rows if str(r.get(expr, "")).strip())
    if agg == "count_distinct":
        return c.distinct([str(r.get(expr)) for r in rows
                           if str(r.get(expr, "")).strip()])
    vals = c.numeric(rows, expr)
    if agg == "sum":
        return round(sum(vals), 4)
    if agg == "avg":
        return round(sum(vals) / len(vals), 4) if vals else None
    if agg == "min":
        return round(min(vals), 4) if vals else None
    if agg == "max":
        return round(max(vals), 4) if vals else None
    return None


# --------------------------------------------------------------------------- #
# reconcile
# --------------------------------------------------------------------------- #
def _reconcile(a: float, b: float, domain: str, label: str) -> Dict[str, Any]:
    tol = TOLERANCE.get(domain, 1.0)
    diff = a - b
    pct = (diff / b * 100.0) if b else 0.0
    within = abs(pct) <= tol
    root_hints = []
    if not within:
        root_hints = ["过滤口径不同", "JOIN 类型不同(LEFT 多行/INNER 丢行)",
                      "粒度不同(订单级 vs 行级)", "时区 UTC vs 本地",
                      "指标定义漂移", "刷新滞后"]
    return {
        "metric": label, "a": a, "b": b, "diff": round(diff, 6),
        "pct_diff": round(pct, 6), "domain": domain, "tolerance_pct": tol,
        "within_tolerance": within, "status": "pass" if within else "fail",
        "possible_root_causes": root_hints,
    }