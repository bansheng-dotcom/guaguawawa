# -*- coding: utf-8 -*-
"""L01 工具实体层 —— 真实本地分析型 SQL 沙箱（不是 print、不是写死 Mock）。

病灶（体检结论）：升级前 R18 的「数据质量门禁 / 增量策略 / 目录口径」全部是
Python 里对 JSON 字段做正则与阈值比较，没有任何真实查询引擎执行环节：
`row_count` 是输入里自己声明的、`null_ratio` 是输入里自己算好的，Agent 只是
复述人类给的数字（换一份假数据也能过门禁）。这属于典型「只有手脚模型、没有手脚」。

对标标杆（Stars > 1k）：
- `duckdb/duckdb`（> 25k）：嵌入式列式分析引擎，零依赖进程内执行真实 SQL；
- `apache/arrow`（> 14k）：列式内存格式，跨引擎零拷贝；
- `dbt-labs/dbt-core`（> 10k）：把「模型即 SQL + 门禁即查询」的确定性合同固化。

本引擎把三条真实能力落到物理执行层：
1. `run_sql`：把 rows 装载成真实表并执行任意只读 SQL，返回真实结果与 SHA256 指纹；
2. `profile_table` / `gate_quality`：行数、空值率、重复率、越界数全部由 SQL 聚合
   真实算出，容差 0 判定，输入里自报的数字不再被信任；
3. `incremental_conservation`：增量合并（INSERT OR REPLACE）后验证
   `目标行数 == 基线行数 + 新增行数` 的物料守恒等式，容差 0。
"""
from __future__ import annotations

import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

# 默认质量门禁（可被 experience/thresholds.json 或显式参数覆盖）
DEFAULT_QUALITY = {
    "max_null_ratio": 0.10,
    "max_dup_ratio": 0.05,
    "min_row_count": 1,
}

_EMPTY_AS_NULL = True  # 空串归一为 NULL（ELT 清洗口径，写进 DATAENG_SPEC §2）


def _quote_ident(name: str) -> str:
    """SQL 标识符转义：双引号包裹，内部双引号翻倍（DuckDB / SQLite 通用）。"""
    return '"' + str(name).replace('"', '""') + '"'


def _infer_sql_type(values: Iterable[Any]) -> str:
    """按实际值推断列类型：全部整数→BIGINT，含小数→DOUBLE，否则 VARCHAR。"""
    seen_int = False
    seen_num = False
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool) or isinstance(v, str):
            return "VARCHAR"
        if isinstance(v, int):
            seen_int = True
            continue
        if isinstance(v, float):
            seen_num = True
            continue
        return "VARCHAR"
    if seen_num:
        return "DOUBLE"
    if seen_int:
        return "BIGINT"
    return "VARCHAR"


def _coerce(value: Any, sql_type: str) -> Any:
    if value is None:
        return None
    if _EMPTY_AS_NULL and isinstance(value, str) and value == "":
        return None
    if sql_type == "VARCHAR":
        return value if isinstance(value, str) else str(value)
    if sql_type == "BIGINT":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return int(float(value))
    if sql_type == "DOUBLE":
        return float(value)
    return value


def _jsonable(value: Any) -> Any:
    """把 DuckDB 返回的 Decimal/date/datetime/UUID 等收敛成可 JSON 化的值。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


class DataEngRuntimeEngine:
    """L01 真实 SQL 执行沙箱：数据工程角色的「手和脚」。"""

    def __init__(self, workspace_dir: Optional[str] = None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(os.path.dirname(here)))
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.backend, self._driver = self._detect_backend()
        self.version = self._detect_version()

    # ------------------------------------------------------------------ #
    # 后端探测
    # ------------------------------------------------------------------ #
    @staticmethod
    def _detect_backend():
        try:
            import duckdb  # noqa: F401
            return "duckdb", duckdb
        except ImportError:
            import sqlite3  # 标准库兜底：同一套 SQL 方言子集
            return "sqlite3", sqlite3

    def _detect_version(self) -> str:
        try:
            if self.backend == "duckdb":
                return str(self._driver.__version__)
            return str(self._driver.sqlite_version)
        except Exception:  # pragma: no cover - 仅用于健康探测的兜底展示
            return "unknown"

    def _connect(self):
        if self.backend == "duckdb":
            return self._driver.connect(":memory:")
        return self._driver.connect(":memory:")

    # ------------------------------------------------------------------ #
    # 装载
    # ------------------------------------------------------------------ #
    @staticmethod
    def _columns(rows: Sequence[Dict[str, Any]]) -> List[str]:
        cols: List[str] = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    cols.append(str(key))
        return cols

    def _load_table(self, con, name: str, rows: Sequence[Dict[str, Any]]) -> Dict[str, str]:
        """真实建表 + 参数化批量插入，返回 {列名: SQL 类型}。"""
        cols = self._columns(rows)
        if not cols:
            raise ValueError(f"表 {name} 无任何列，无法装载")
        types = {
            col: _infer_sql_type([row.get(col) for row in rows]) for col in cols
        }
        ddl = ", ".join(f"{_quote_ident(c)} {types[c]}" for c in cols)
        con.execute(f"CREATE TABLE {_quote_ident(name)} ({ddl})")
        if rows:
            placeholders = ", ".join(["?"] * len(cols))
            insert = f"INSERT INTO {_quote_ident(name)} VALUES ({placeholders})"
            payload = [
                tuple(_coerce(row.get(c), types[c]) for c in cols) for row in rows
            ]
            con.executemany(insert, payload)
        return types

    def _load_mapping(self, con, tables: Dict[str, Sequence[Dict[str, Any]]]) -> Dict[str, Dict[str, str]]:
        if not isinstance(tables, dict) or not tables:
            raise ValueError("tables 必须是非空 {表名: rows} 映射")
        return {name: self._load_table(con, name, rows) for name, rows in tables.items()}

    # ------------------------------------------------------------------ #
    # 真实执行
    # ------------------------------------------------------------------ #
    def run_sql(self, tables: Dict[str, Sequence[Dict[str, Any]]], sql: str) -> Dict[str, Any]:
        """装载内存表 → 真实执行 SQL → 返回结果 + 确定性指纹。"""
        con = self._connect()
        try:
            self._load_mapping(con, tables)
            t0 = time.time()
            cur = con.execute(sql)
            rows = cur.fetchall()
            elapsed_ms = int((time.time() - t0) * 1000)
            columns = [d[0] for d in (cur.description or [])]
        finally:
            con.close()
        result_rows = [_jsonable(row) for row in rows]
        payload = {"columns": columns, "rows": result_rows}
        return {
            "ok": True,
            "engine": self.backend,
            "sql": sql,
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "elapsed_ms": elapsed_ms,
            "sha256": hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest(),
        }

    def fingerprint(self, rows: Sequence[Dict[str, Any]]) -> str:
        """行集 SHA256 指纹：同一份数据必须得到同一个指纹（确定性可复验）。"""
        canon = sorted(
            json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
            for row in rows
        )
        return hashlib.sha256("\n".join(canon).encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ #
    # 质量画像 / 门禁（全部由 SQL 聚合算出）
    # ------------------------------------------------------------------ #
    def profile_table(
        self,
        rows: Sequence[Dict[str, Any]],
        table: str = "t",
        numeric_columns: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """真实画像：行数、逐列空值率、重复率、数值列 min/max。"""
        con = self._connect()
        try:
            types = self._load_table(con, table, rows)
            total = int(con.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}").fetchone()[0])
            cols = list(types.keys())
            null_ratios: Dict[str, float] = {}
            for col in cols:
                if total == 0:
                    null_ratios[col] = 0.0
                    continue
                n_null = int(con.execute(
                    f"SELECT COUNT(*) FROM {_quote_ident(table)} WHERE {_quote_ident(col)} IS NULL"
                ).fetchone()[0])
                null_ratios[col] = round(n_null / total, 6)
            distinct_sql = ", ".join(_quote_ident(c) for c in cols)
            distinct = int(con.execute(
                f"SELECT COUNT(*) FROM (SELECT DISTINCT {distinct_sql} FROM {_quote_ident(table)})"
            ).fetchone()[0])
            ranges: Dict[str, Dict[str, Any]] = {}
            for col, sql_type in types.items():
                if sql_type not in ("BIGINT", "DOUBLE"):
                    continue
                row = con.execute(
                    f"SELECT MIN({_quote_ident(col)}), MAX({_quote_ident(col)}) FROM {_quote_ident(table)}"
                ).fetchone()
                ranges[col] = {"min": _jsonable(row[0]), "max": _jsonable(row[1])}
        finally:
            con.close()
        dup_ratio = round(1 - (distinct / total), 6) if total else 0.0
        return {
            "ok": total > 0,
            "engine": self.backend,
            "table": table,
            "row_count": total,
            "column_count": len(cols),
            "columns": cols,
            "column_types": types,
            "null_ratio": null_ratios,
            "max_null_ratio": max(null_ratios.values()) if null_ratios else 0.0,
            "distinct_rows": distinct,
            "dup_ratio": dup_ratio,
            "numeric_ranges": ranges,
        }

    def gate_quality(
        self,
        rows: Sequence[Dict[str, Any]],
        thresholds: Optional[Dict[str, Any]] = None,
        table: str = "t",
        ranges: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Dict[str, Any]:
        """真门禁：row_count>0 / 空值率 / 重复率 / 越界数，全部容差 0 判定。"""
        th = dict(DEFAULT_QUALITY)
        th.update(thresholds or {})
        profile = self.profile_table(rows, table=table)
        checks: List[Dict[str, Any]] = []

        def ck(ok: bool, msg: str, dim: str, sev: str = "HIGH", **ev) -> Dict[str, Any]:
            d = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else sev}
            d.update(ev)
            return d

        total = profile["row_count"]
        checks.append(ck(total >= int(th["min_row_count"]),
                         f"row_count={total} >= {th['min_row_count']}（SQL COUNT(*) 实测）",
                         "row_count", "BLOCKER", actual=total))
        for col, ratio in profile["null_ratio"].items():
            max_null = float(th["max_null_ratio"])
            checks.append(ck(ratio <= max_null,
                             f"{col} 空值率 {ratio} <= {max_null}（SQL 聚合实测）",
                             "null_ratio", "BLOCKER", column=col, actual=ratio))
        max_dup = float(th["max_dup_ratio"])
        checks.append(ck(profile["dup_ratio"] <= max_dup,
                         f"重复率 {profile['dup_ratio']} <= {max_dup}（DISTINCT 实测）",
                         "dup_ratio", "BLOCKER", actual=profile["dup_ratio"]))

        out_of_range_total = 0
        if ranges:
            con = self._connect()
            try:
                self._load_table(con, table, rows)
                for col, bound in ranges.items():
                    if col not in profile["columns"]:
                        continue
                    lo = bound.get("min")
                    hi = bound.get("max")
                    conds, params = [], []
                    if lo is not None:
                        conds.append(f"{_quote_ident(col)} < ?")
                        params.append(lo)
                    if hi is not None:
                        conds.append(f"{_quote_ident(col)} > ?")
                        params.append(hi)
                    if not conds:
                        continue
                    n = int(con.execute(
                        f"SELECT COUNT(*) FROM {_quote_ident(table)} WHERE {' OR '.join(conds)}",
                        params,
                    ).fetchone()[0])
                    out_of_range_total += n
                    checks.append(ck(n == 0, f"{col} 越界行数={n}（SQL WHERE 实测）",
                                     "range", "BLOCKER", column=col, actual=n))
            finally:
                con.close()

        ok = all(x["ok"] for x in checks)
        return {
            "ok": ok,
            "engine": self.backend,
            "table": table,
            "grade": "PASS" if ok else "FAIL",
            "checks": checks,
            "profile": profile,
            "out_of_range_rows": out_of_range_total,
            "thresholds": th,
        }

    # ------------------------------------------------------------------ #
    # 增量守恒（容差 0）
    # ------------------------------------------------------------------ #
    def incremental_conservation(
        self,
        base_rows: Sequence[Dict[str, Any]],
        incoming_rows: Sequence[Dict[str, Any]],
        key: str = "id",
    ) -> Dict[str, Any]:
        """真实增量合并 + 守恒等式：target = base + inserted（updated 原位替换）。"""
        if not base_rows:
            return {"ok": False, "conserved": False,
                    "reason": "基线为空，无法验证增量守恒"}
        cols = self._columns(base_rows) or self._columns(incoming_rows)
        if key not in cols:
            return {"ok": False, "conserved": False, "reason": f"基线缺主键列 {key}"}

        con = self._connect()
        try:
            base_types = self._load_table(con, "base", base_rows)
            cols = list(base_types.keys())

            # 目标表：同构列 + 主键约束
            ddl = ", ".join(f"{_quote_ident(c)} {base_types[c]}" for c in cols)
            con.execute(f"CREATE TABLE target ({ddl}, PRIMARY KEY ({_quote_ident(key)}))")
            con.execute("INSERT INTO target SELECT * FROM base")

            base_count = int(con.execute("SELECT COUNT(*) FROM target").fetchone()[0])
            incoming_cols = [c for c in cols if c in self._columns(incoming_rows)]
            new_keys = [r.get(key) for r in incoming_rows]
            if base_count and new_keys:
                placeholders = ", ".join(["?"] * len(new_keys))
                updated = int(con.execute(
                    f"SELECT COUNT(*) FROM target WHERE {_quote_ident(key)} IN ({placeholders})",
                    list(new_keys),
                ).fetchone()[0])
            else:
                updated = 0
            inserted = len(incoming_rows) - updated

            if incoming_rows:
                placeholders = ", ".join(["?"] * len(cols))
                upsert = (
                    f"INSERT OR REPLACE INTO target VALUES ({placeholders})"
                )
                payload = []
                for r in incoming_rows:
                    payload.append(tuple(
                        _coerce(r.get(c), base_types[c]) if c in incoming_cols else None
                        for c in cols
                    ))
                con.executemany(upsert, payload)

            target_count = int(con.execute("SELECT COUNT(*) FROM target").fetchone()[0])
            null_keys = int(con.execute(
                f"SELECT COUNT(*) FROM target WHERE {_quote_ident(key)} IS NULL"
            ).fetchone()[0])
        finally:
            con.close()

        expected = base_count + inserted
        conserved = (target_count == expected) and null_keys == 0
        return {
            "ok": conserved,
            "conserved": conserved,
            "engine": self.backend,
            "key": key,
            "base_count": base_count,
            "incoming_count": len(incoming_rows),
            "updated_count": updated,
            "inserted_count": inserted,
            "target_count": target_count,
            "expected_count": expected,
            "delta": target_count - expected,
            "null_keys": null_keys,
            "checks": [
                {"ok": conserved, "dim": "conservation",
                 "msg": f"target({target_count}) == base({base_count}) + inserted({inserted})",
                 "sev": "OK" if conserved else "BLOCKER"},
                {"ok": null_keys == 0, "dim": "primary_key",
                 "msg": f"主键空值行数={null_keys}", "sev": "OK" if null_keys == 0 else "BLOCKER"},
            ],
        }

    # ------------------------------------------------------------------ #
    # 健康探针
    # ------------------------------------------------------------------ #
    def probe_health(self) -> Dict[str, Any]:
        """真实往返探针：建表→插值→聚合→关闭，全部走引擎，不做假返回。"""
        t0 = time.time()
        try:
            out = self.run_sql(
                {"probe": [{"id": 1, "v": 10}, {"id": 2, "v": 32}, {"id": 3, "v": 8}]},
                "SELECT COUNT(*) AS n, SUM(v) AS total FROM probe",
            )
            n, total = out["rows"][0]
            ok = int(n) == 3 and int(total) == 50
            return {
                "status": "HEALTHY" if ok else "DEGRADED",
                "engine": self.backend,
                "version": self.version,
                "probe_rows": int(n),
                "probe_sum": int(total),
                "probe_ms": int((time.time() - t0) * 1000),
                "roundtrip": ok,
            }
        except Exception as exc:  # pragma: no cover - 仅在引擎损坏时触发
            return {"status": "DEGRADED", "engine": self.backend,
                    "version": self.version, "error": str(exc),
                    "probe_ms": int((time.time() - t0) * 1000), "roundtrip": False}


# --------------------------------------------------------------------------- #
# CLI：python -m engines.runtime_engine --probe --out workspace/rounds/L01.json
# --------------------------------------------------------------------------- #
def _write_json(path: str, data: Any) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L01 真实 SQL 执行沙箱")
    ap.add_argument("--probe", action="store_true", help="执行引擎往返健康探针")
    ap.add_argument("--input", default="", help="rows JSON（list 或 {rows:[...]}）")
    ap.add_argument("--sql", default="", help="在装载后的 t 表上执行的真实 SQL")
    ap.add_argument("--gate", action="store_true", help="对输入 rows 跑质量门禁")
    ap.add_argument("--out", default="", help="结果 JSON 输出路径")
    args = ap.parse_args(argv)

    engine = DataEngRuntimeEngine()
    out: Dict[str, Any] = {"ok": True, "engine": engine.backend, "version": engine.version}
    if args.probe:
        health = engine.probe_health()
        out["probe"] = health
        out["ok"] = health["status"] == "HEALTHY"
    if args.input:
        with open(args.input, encoding="utf-8-sig") as f:
            payload = json.load(f)
        rows = payload.get("rows") if isinstance(payload, dict) else payload
        rows = [r for r in (rows or []) if isinstance(r, dict)]
        out["row_count"] = len(rows)
        if args.gate:
            out["gate"] = engine.gate_quality(rows)
            out["ok"] = out["ok"] and out["gate"]["ok"]
        if args.sql:
            out["query"] = engine.run_sql({"t": rows}, args.sql)
    _write_json(args.out, out)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": out["ok"], "engine": out["engine"], "out": args.out,
         "probe_status": out.get("probe", {}).get("status"),
         "gate_grade": out.get("gate", {}).get("grade")}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
