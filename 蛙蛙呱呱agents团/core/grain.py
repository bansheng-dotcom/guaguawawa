# -*- coding: utf-8 -*-
"""core.grain —— 粒度运算与校验（SYSTEM-UPGRADE-SOP v3.1 · S1）。

这是整个采集层的核心，只有四件事：

    atomic_of(source)              源能捕获的最低粒度
    analysis_of(rollup)            分析要的粒度
    check(source, rollup)          G-A~G-E 五道校验（空 = 合法）
    rollup_rows(staging, rollup)   原子行 → 分析行（group by + agg）

**业务无关**：这里不认识「脚垫」「品牌」「月」，只认字段名和声明。

硬规矩（Kimball）：分析粒度的每一维都必须能从原子粒度推导；
不同 grain 不能混在一张表里。
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from core import source_profile as sp

AGGS = ("sum", "mean", "count", "min", "max")
# 时间类字段名（用于判断 rollup 是否要「序列」）
TIME_HINTS = ("date", "month", "year", "week", "quarter", "day", "period", "期", "月", "年")

# 安全的算术求值白名单：只允许 数字/列名/四则/括号
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Load)


def _safe_eval(expr: str, names: Dict[str, Any]) -> Any:
    """只算四则运算；不调用任何函数、不访问属性。"""
    tree = ast.parse(str(expr), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError("非法表达式: %s" % expr)
    return eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, names)


def atomic_of(source: Dict[str, Any]) -> List[str]:
    return [str(x) for x in (source.get("atomic_grain") or []) if str(x).strip()]


def analysis_of(rollup: Dict[str, Any]) -> List[str]:
    return [str(x) for x in (rollup.get("grain") or []) if str(x).strip()]


def _is_time(name: str) -> bool:
    low = str(name).lower()
    return any(h in low for h in TIME_HINTS)


def _expr_columns(expr: str) -> List[str]:
    """从表达式里抽出列名（ast 的 Name 节点）。"""
    try:
        tree = ast.parse(str(expr), mode="eval")
    except SyntaxError:
        return []
    return sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})


def check(source: Dict[str, Any], rollup: Dict[str, Any]) -> List[str]:
    """G-A~G-E；空 = 合法。"""
    errs: List[str] = []
    fields = set(sp.field_names(source))
    atomic = atomic_of(source)
    analysis = analysis_of(rollup)
    derive = dict(rollup.get("derive") or {})
    measures = dict(rollup.get("measures") or {})

    # G-A 原子粒度必须已声明
    if not atomic:
        errs.append("G-A: 源没有 atomic_grain")
    # G-D grain 不混：必须有 grain，且不能是空串
    if not analysis:
        errs.append("G-D: rollup 没有 grain（一行代表什么）")
    # G-B 分析粒度每一维都要能推导
    for dim in analysis:
        if dim in derive:
            continue
        if dim in fields:
            continue
        errs.append("G-B: grain 里的 %r 既不是源字段也没有 derive" % dim)
    # derive 引用的列必须在源里
    for k, v in derive.items():
        for col in _expr_columns(str(v)) if "calc:" not in str(v) else []:
            if col not in fields:
                errs.append("G-B: derive[%s] 引用了不存在的列 %r" % (k, col))
    # G-C 度量可算
    if not measures:
        errs.append("G-C: rollup 没有 measures")
    for name, m in measures.items():
        agg = str((m or {}).get("agg") or "")
        if agg not in AGGS:
            errs.append("G-C: measures[%s].agg 非法: %r" % (name, agg))
        expr = str((m or {}).get("expr") or "")
        if not expr:
            errs.append("G-C: measures[%s] 缺 expr" % name)
            continue
        for col in _expr_columns(expr):
            if col not in fields and col not in derive:
                errs.append("G-C: measures[%s] 用了不存在的列 %r" % (name, col))
    # G-E 要序列就必须有历史
    needs_series = bool(rollup.get("series")) or any(_is_time(d) for d in analysis)
    if needs_series and str(source.get("history") or "") != "historical":
        errs.append("G-E: 该 rollup 需要时间序列，但源 history=%r（只能采当下）"
                    % source.get("history"))
    return errs


def _derive_value(row: Dict[str, Any], spec: str) -> Any:
    """derive 表达式 DSL（业务无关）：

        field:<col>
        substr:<col>:<start>:<end>
        token:<col>:<index>            取第 n 个空白分隔 token
        bucket:<col>:<t1,t2>:<l1,l2,l3>
        calc:<expr>                    四则运算
    """
    s = str(spec)
    if s.startswith("field:"):
        return row.get(s.split(":", 1)[1])
    if s.startswith("substr:"):
        _, col, a, b = s.split(":", 3)
        return str(row.get(col) or "")[int(a):int(b)]
    if s.startswith("token:"):
        _, col, idx = s.split(":", 2)
        parts = str(row.get(col) or "").split()
        i = int(idx)
        return parts[i] if 0 <= i < len(parts) else ""
    if s.startswith("split:"):
        # split:<col>:<sep>:<index>；sep 写 \t 表示制表符
        _, col, sep, idx = s.split(":", 3)
        sep = "\t" if sep == "\\t" else sep
        parts = [x.strip() for x in str(row.get(col) or "").split(sep)]
        i = int(idx)
        return parts[i] if 0 <= i < len(parts) else ""
    if s.startswith("bucket:"):
        _, col, bounds, labels = s.split(":", 3)
        v = _num(row.get(col))
        ts = [float(x) for x in bounds.split(",") if x.strip()]
        ls = [x for x in labels.split(",")]
        if v is None:
            return ""
        for i, t in enumerate(ts):
            if v < t:
                return ls[i] if i < len(ls) else ""
        return ls[len(ts)] if len(ls) > len(ts) else ""
    if s.startswith("calc:"):
        return _safe_eval(s.split(":", 1)[1], _num_names(row))
    return row.get(s)


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:  # noqa: BLE001
        return None


def _num_names(row: Dict[str, Any]) -> Dict[str, float]:
    out = {}
    for k, v in row.items():
        n = _num(v)
        if n is not None:
            out[str(k)] = n
    return out


def rollup_rows(staging_rows: List[Dict[str, Any]],
                rollup: Dict[str, Any]) -> List[Dict[str, Any]]:
    """原子行 → 分析行（group by grain + agg measures）。"""
    grain = analysis_of(rollup)
    derive = dict(rollup.get("derive") or {})
    measures = dict(rollup.get("measures") or {})
    if not grain or not measures:
        return []

    buckets: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in staging_rows or []:
        key = tuple(_derive_value(row, derive[d]) if d in derive else row.get(d)
                    for d in grain)
        buckets[key].append(row)

    out: List[Dict[str, Any]] = []
    for key, rows in sorted(buckets.items(), key=lambda kv: str(kv[0])):
        rec: Dict[str, Any] = dict(zip(grain, key))
        for name, m in measures.items():
            agg = str((m or {}).get("agg") or "sum")
            expr = str((m or {}).get("expr") or "")
            vals = []
            for r in rows:
                try:
                    v = _safe_eval(expr, _num_names(r))
                    if isinstance(v, bool):
                        continue
                    vals.append(float(v))
                except Exception:  # noqa: BLE001
                    continue
            if not vals:
                rec[name] = None
                continue
            if agg == "sum":
                rec[name] = round(sum(vals), 4)
            elif agg == "mean":
                rec[name] = round(sum(vals) / len(vals), 4)
            elif agg == "count":
                rec[name] = float(len(vals))
            elif agg == "min":
                rec[name] = round(min(vals), 4)
            else:
                rec[name] = round(max(vals), 4)
        rec["_rows"] = len(rows)
        out.append(rec)
    return out


def chain_check(source: Dict[str, Any], rollup: Dict[str, Any],
                claim: Dict[str, Any]) -> List[str]:
    """再往上一跳：claim 的查询能不能在这张 mart 上跑。

    复用 cell_claim 的校验思路，但只查「列存不存在」，不查业务语义。
    """
    errs: List[str] = []
    mart_cols = set(analysis_of(rollup)) | set((rollup.get("measures") or {}).keys())
    q = (claim or {}).get("query") or {}
    bad_f = [k for k in (q.get("filters") or {}) if k not in mart_cols]
    if bad_f:
        errs.append("claim.filters 用了 mart 没有的列: %s" % bad_f)
    bad_g = [k for k in (q.get("group_by") or []) if k not in mart_cols]
    if bad_g:
        errs.append("claim.group_by 用了 mart 没有的列: %s" % bad_g)
    bad_m = [k for k in (q.get("metrics") or []) if k not in mart_cols]
    if bad_m:
        errs.append("claim.metrics 用了 mart 没有的列: %s" % bad_m)
    return errs
