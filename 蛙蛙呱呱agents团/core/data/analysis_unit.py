# -*- coding: utf-8 -*-
"""core.data.analysis_unit —— 分析单元（DATA-LAYER-SOP v3.0 · S0）。

v2.0 的钻取把「品类」当输入、把品牌/价格带写死在代码里；v3.0 改成：
    **一个分析单元 = 度量 + 维度集 + 时间粒度**，维度集只能来自语义层。

三条硬约束：
    C1 dims 只能来自 sem["entities"]，缺了抛 MISSING_ENTITY（不套默认值）
    C2 rows_expected 必须由「维度基数 × 期数」算出，缺枚举抛 NO_CARDINALITY
    C3 一个 must 问至少 1 个 unit（上游 G6' 校验）

用法：
    from core.data import analysis_unit as au
    sem  = au.load("semantic_layer.yaml")
    unit = au.from_measure("asp", sem)
    au.rows_expected(unit, sem)          # 6×7×12 ...
    au.plan_units(sem)                   # 全部单元

CLI：
    python -m core.data.analysis_unit --sem <语义层> [--measure asp]

接线：pipeline.bootstrap 在 prepare 成功后调用 plan_units()，把单元清单
    挂到返回值的 prepare.analysis_units（解析失败只记录，不阻断发卡）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PERIODS = {"year": 3, "quarter": 12, "month": 36, "week": 104, "day": 365}
TIME_NAMES = ("year", "quarter", "month", "week", "day")

# 通用词白名单（来自 configs/analysis_vocab.yaml 的默认值）：
# 只有这些词可以不来自 sem；业务词（品牌/品类/省/价格带）一律不许写死。
GENERIC_DIMS = ("period", "time", "date", "month", "year", "week", "quarter", "day")


def _index(items: Any, key: str = "id") -> Dict[str, Dict[str, Any]]:
    """sem 的 entities / grain_declarations / measures 可能是 list 也可能是 dict，统一成 dict。"""
    if isinstance(items, dict):
        return {str(k): dict(v or {}) for k, v in items.items()}
    out: Dict[str, Dict[str, Any]] = {}
    for it in items or []:
        if isinstance(it, dict) and it.get(key):
            out[str(it[key])] = dict(it)
    return out


def load(path: str | Path) -> Dict[str, Any]:
    """读语义层，返回统一结构；缺 entities / grain_declarations / measures 直接报错。"""
    import yaml

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    sem = {
        "entities": _index(raw.get("entities")),
        "grain_declarations": _index(raw.get("grain_declarations")),
        "measures": _index(raw.get("measures")),
        "schema": raw.get("schema"),
        "path": str(path),
    }
    for k in ("entities", "grain_declarations", "measures"):
        if not sem[k]:
            raise KeyError(f"SEM_MISSING {k}（语义层缺这一段，不能钻取）")
    return sem


def _dims_of_grain(grain_id: str, sem: Dict[str, Any]) -> List[str]:
    g = sem["grain_declarations"].get(str(grain_id))
    if not g:
        raise KeyError(f"MISSING_GRAIN {grain_id}")
    return [str(d) for d in (g.get("dims") or [])]


def from_measure(mid: str, sem: Dict[str, Any]) -> Dict[str, Any]:
    """度量 → 分析单元。维度 = 该度量 grain 里的维度 ∩ sem.entities。"""
    m = sem["measures"].get(str(mid))
    if not m:
        raise KeyError(f"MISSING_MEASURE {mid}")
    dims_all = _dims_of_grain(str(m.get("grain") or ""), sem)
    unknown = [d for d in dims_all
               if d not in sem["entities"] and d not in GENERIC_DIMS]
    if unknown:
        raise KeyError(f"MISSING_ENTITY {unknown}（sem 里没有这个维度，不许猜）")
    dims = [d for d in dims_all if d in sem["entities"]]
    # 时间粒度取 grain 声明里的时间维（G_a_b_month → month），不拿全局 period.grain 顶替
    period_ent = sem["entities"].get("period") or {}
    tg = next((d for d in dims_all if d in TIME_NAMES), "")
    return {
        "measure": str(mid),
        "dims": dims,
        "time_grain": tg or str(period_ent.get("grain") or "month"),
        "unit": str(m.get("unit") or ""),
        "agg": str(m.get("agg") or "sum"),
        "grain": str(m.get("grain") or ""),
    }


def cardinality(dim: str, sem: Dict[str, Any]) -> int:
    ent = sem["entities"].get(dim) or {}
    levels = ent.get("levels")
    if not levels:
        raise KeyError(f"NO_CARDINALITY {dim}（维度没给枚举，算不出行数）")
    return len(levels)


def rows_expected(unit: Dict[str, Any], sem: Dict[str, Any],
                  periods: Optional[int] = None) -> int:
    n = 1
    for d in unit["dims"]:
        n *= cardinality(d, sem)
    return n * (periods if periods is not None else PERIODS.get(unit["time_grain"], 12))


def dataset_id(unit: Dict[str, Any]) -> str:
    return "DS-%s-%s" % (unit["measure"], "-".join(unit["dims"] + [unit["time_grain"]]))


def plan_units(sem: Dict[str, Any], only: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """把语义层里所有度量展开成分析单元；only 用于只跑指定度量。"""
    units = []
    for mid in sem["measures"]:
        if only and mid not in only:
            continue
        try:
            u = from_measure(mid, sem)
            u["rows_expected"] = rows_expected(u, sem)
            u["dataset_id"] = dataset_id(u)
            units.append(u)
        except KeyError as e:      # 缺维度/缺枚举：记下来，不吞
            units.append({"measure": mid, "error": str(e)})
    return units


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="把语义层展开成分析单元")
    ap.add_argument("--sem", required=True)
    ap.add_argument("--measure", action="append", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    sem = load(a.sem)
    units = plan_units(sem, a.measure)
    if a.json:
        print(json.dumps(units, ensure_ascii=False, indent=1))
        return 0
    ok = [u for u in units if "error" not in u]
    bad = [u for u in units if "error" in u]
    print(f"分析单元 {len(ok)} 个，报错 {len(bad)} 个")
    for u in ok:
        print(f"  {u['dataset_id']:<44} dims={u['dims']} {u['time_grain']} "
              f"rows_expected={u['rows_expected']}")
    for u in bad:
        print(f"  !! {u['measure']:<16} {u['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
