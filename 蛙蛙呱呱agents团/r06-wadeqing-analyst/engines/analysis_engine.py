# -*- coding: utf-8 -*-
"""L01 工具实体层 (Real Analytical Tool & Engine Layer)
对标开源: DuckDB (Stars > 20k) / DuckDB-Wasm / Polars / Pandas Native Operators
功能:
1. 真实嵌入式 SQL 分析沙箱 (DuckDB In-Memory)：直接注册记录/CSV 并执行 SQL，非 Mock；
2. 确定性货币分位四舍五入 (ROUND_HALF_UP) 与零容差守恒勾稽 (Total = Sum(Parts))；
3. 多引擎注册中心：能力清单、健康探测、延迟采样与自动降级 (DuckDB -> Native)。
"""
from __future__ import annotations

import decimal
import math
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AnalyticalQueryResult:
    ok: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    rows_processed: int = 0


def _round_money(value: Any) -> float:
    """货币分位四舍五入，规避 IEEE 754 浮点累加误差。"""
    return float(decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"),
                                                      rounding=decimal.ROUND_HALF_UP))


class DuckDBSQLSandbox:
    """真实嵌入式 SQL 分析沙箱，对标 DuckDB / DuckDB-Wasm 的本地列式执行。"""

    engine_id = "duckdb_embedded"

    def __init__(self) -> None:
        self.available = False
        self._conn = None
        self._tables: List[str] = []
        self._last_probe_ms: float = 0.0
        try:
            import duckdb  # 延迟导入，缺库时平滑降级
            self._duckdb = duckdb
            self._conn = duckdb.connect(database=":memory:")
            self.available = True
        except Exception:
            self._duckdb = None

    # ------------------------------------------------------------------ #
    # 数据装载
    # ------------------------------------------------------------------ #
    def register_records(self, table: str, rows: List[Dict[str, Any]]) -> int:
        """把结构化记录注册为真实可查询表。"""
        if not self.available:
            raise RuntimeError("DuckDB engine unavailable")
        if not rows:
            raise ValueError("register_records requires non-empty rows")
        import pyarrow as pa
        self._conn.register(table, pa.Table.from_pylist(rows))
        if table not in self._tables:
            self._tables.append(table)
        return len(rows)

    def register_csv(self, table: str, path: str) -> int:
        """直接注册 CSV 文件为真实数据表 (DuckDB read_csv_auto)。"""
        if not self.available:
            raise RuntimeError("DuckDB engine unavailable")
        self._conn.execute(
            f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM read_csv_auto(?)',
            [path],
        )
        if table not in self._tables:
            self._tables.append(table)
        count = self._conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        return int(count)

    # ------------------------------------------------------------------ #
    # SQL 执行
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Optional[List[Any]] = None) -> AnalyticalQueryResult:
        t0 = time.perf_counter()
        if not self.available:
            return AnalyticalQueryResult(ok=False, data={}, error="DuckDB engine unavailable")
        try:
            cur = self._conn.execute(sql, params or [])
            columns = [d[0] for d in (cur.description or [])]
            rows = cur.fetchall()
            data_rows = [dict(zip(columns, row)) for row in rows]
            return AnalyticalQueryResult(
                ok=True,
                data={"columns": columns, "rows": data_rows, "row_count": len(data_rows)},
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 3),
                rows_processed=len(data_rows),
            )
        except Exception as exc:
            return AnalyticalQueryResult(
                ok=False,
                data={},
                error=str(exc),
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

    def aggregate(self, table: str, metric: str, dimension: Optional[str] = None) -> AnalyticalQueryResult:
        """真实分组聚合：SUM/AVG/COUNT 全下推到列式引擎。"""
        if dimension:
            sql = (f'SELECT "{dimension}" AS dim, SUM("{metric}") AS metric_sum, '
                   f'AVG("{metric}") AS metric_avg, COUNT(*) AS rows '
                   f'FROM "{table}" GROUP BY 1 ORDER BY 2 DESC')
        else:
            sql = (f'SELECT SUM("{metric}") AS metric_sum, AVG("{metric}") AS metric_avg, '
                   f'COUNT(*) AS rows FROM "{table}"')
        return self.execute(sql)

    def is_healthy(self) -> bool:
        if not self.available:
            return False
        t0 = time.perf_counter()
        res = self.execute("SELECT 42 AS answer, 6 * 7 AS product")
        self._last_probe_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        if not res.ok or not res.data.get("rows"):
            return False
        row = res.data["rows"][0]
        return int(row.get("answer", 0)) == 42 and int(row.get("product", 0)) == 42


class NativeAnalysisEngine:
    """真实纯原生的轻量嵌入式分析引擎，提供高精度确定性计算，杜绝 Mock。"""

    engine_id = "native_in_memory"

    def __init__(self, engine_id: str = "native_in_memory"):
        self.engine_id = engine_id
        self._operators: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._register_default_operators()

    def _register_default_operators(self) -> None:
        self._operators["aggregate_metrics"] = self._op_aggregate_metrics
        self._operators["hhi_concentration"] = self._op_hhi_concentration
        self._operators["growth_and_variance"] = self._op_growth_and_variance
        self._operators["rfm_segmentation"] = self._op_rfm_segmentation
        self._operators["attribution_decomposition"] = self._op_attribution_decomposition
        self._operators["money_round"] = self._op_money_round
        self._operators["conservation_check"] = self._op_conservation_check
        self._operators["dispersion_metrics"] = self._op_dispersion_metrics

    def capabilities(self) -> List[str]:
        return sorted(self._operators.keys())

    def is_healthy(self) -> bool:
        try:
            res = self.execute("hhi_concentration", {"shares": [50.0, 50.0]})
            return res.ok and math.isclose(res.data.get("hhi", 0), 5000.0, rel_tol=1e-3)
        except Exception:
            return False

    def execute(self, operator_name: str, payload: Dict[str, Any]) -> AnalyticalQueryResult:
        t0 = time.perf_counter()
        if operator_name not in self._operators:
            return AnalyticalQueryResult(
                ok=False,
                data={},
                error=f"Unsupported analytical operator: {operator_name}",
                execution_time_ms=(time.perf_counter() - t0) * 1000.0,
            )

        try:
            out = self._operators[operator_name](payload)
            cost = (time.perf_counter() - t0) * 1000.0
            rows = payload.get("rows_count") or len(payload.get("values", [])) or len(payload.get("shares", []))
            return AnalyticalQueryResult(
                ok=True,
                data=out,
                execution_time_ms=round(cost, 3),
                rows_processed=rows,
            )
        except Exception as exc:
            return AnalyticalQueryResult(
                ok=False,
                data={},
                error=str(exc),
                execution_time_ms=(time.perf_counter() - t0) * 1000.0,
            )

    def _op_aggregate_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        values = [float(v) for v in payload.get("values", []) if v is not None]
        if not values:
            return {"count": 0, "sum": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
        total = sum(values)
        n = len(values)
        mean_val = total / n
        med_val = statistics.median(values)
        stdev = statistics.stdev(values) if n > 1 else 0.0
        return {
            "count": n,
            "sum": round(total, 4),
            "mean": round(mean_val, 4),
            "median": round(med_val, 4),
            "stdev": round(stdev, 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    def _op_hhi_concentration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        shares = [float(s) for s in payload.get("shares", [])]
        if not shares:
            return {"hhi": 0.0, "grade": "none", "normalized": False}
        total = sum(shares)
        if total <= 0:
            return {"hhi": 0.0, "grade": "invalid", "normalized": False}

        # 归一化为百分比
        norm_shares = [(s / total) * 100.0 for s in shares]
        hhi = sum(s ** 2 for s in norm_shares)
        if hhi > 2500.0:
            grade = "highly_concentrated"
        elif hhi >= 1500.0:
            grade = "moderately_concentrated"
        else:
            grade = "unconcentrated_competitive"
        return {
            "hhi": round(hhi, 2),
            "grade": grade,
            "normalized": True,
            "components_count": len(shares),
        }

    def _op_growth_and_variance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        baseline = float(payload.get("baseline", 0.0))
        current = float(payload.get("current", 0.0))
        delta = current - baseline
        pct_change = (delta / baseline) if baseline != 0.0 else 0.0
        return {
            "baseline": baseline,
            "current": current,
            "delta": round(delta, 4),
            "pct_change": round(pct_change, 4),
            "pct_change_str": f"{pct_change * 100.0:+.2f}%",
            "baseline_zero_guarded": baseline == 0.0,
        }

    def _op_rfm_segmentation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # r, f, m 三维阈值打分
        r_days = float(payload.get("recency_days", 0))
        f_freq = int(payload.get("frequency", 0))
        m_amt = float(payload.get("monetary", 0.0))
        # 极简打分模型：R 越小越好，F 越大越好，M 越大越好
        r_score = 5 if r_days <= 7 else (4 if r_days <= 30 else (3 if r_days <= 90 else (2 if r_days <= 180 else 1)))
        f_score = 5 if f_freq >= 10 else (4 if f_freq >= 5 else (3 if f_freq >= 3 else (2 if f_freq >= 1 else 1)))
        m_score = 5 if m_amt >= 1000 else (4 if m_amt >= 500 else (3 if m_amt >= 200 else (2 if m_amt >= 50 else 1)))
        total_score = r_score * 100 + f_score * 10 + m_score
        segment = "重要价值客户" if (r_score >= 4 and f_score >= 4 and m_score >= 4) else (
            "重要挽留客户" if (r_score <= 2 and f_score >= 3) else (
                "重要发展客户" if (r_score >= 3 and m_score >= 3) else "一般价值客户"
            )
        )
        return {
            "r_score": r_score,
            "f_score": f_score,
            "m_score": m_score,
            "rfm_code": total_score,
            "segment": segment,
        }

    def _op_attribution_decomposition(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 因素分解：如 GMV = UV * CVR * ATV (客单价)
        uv0 = float(payload.get("uv_baseline", 1.0))
        uv1 = float(payload.get("uv_current", 1.0))
        cvr0 = float(payload.get("cvr_baseline", 0.01))
        cvr1 = float(payload.get("cvr_current", 0.01))
        atv0 = float(payload.get("atv_baseline", 10.0))
        atv1 = float(payload.get("atv_current", 10.0))

        y0 = uv0 * cvr0 * atv0
        y1 = uv1 * cvr1 * atv1
        total_diff = y1 - y0

        # Shapley-like 近似分解
        eff_uv = (uv1 - uv0) * ((cvr0 * atv0 + cvr1 * atv1) / 2.0)
        eff_cvr = (cvr1 - cvr0) * ((uv0 * atv0 + uv1 * atv1) / 2.0)
        eff_atv = (atv1 - atv0) * ((uv0 * cvr0 + uv1 * cvr1) / 2.0)
        sum_eff = eff_uv + eff_cvr + eff_atv
        scale = (total_diff / sum_eff) if sum_eff != 0 else 1.0

        contributions = {
            "uv_contribution": round(eff_uv * scale, 2),
            "cvr_contribution": round(eff_cvr * scale, 2),
            "atv_contribution": round(eff_atv * scale, 2),
        }
        explained = sum(contributions.values())
        return {
            "baseline_value": round(y0, 2),
            "current_value": round(y1, 2),
            "delta_total": round(total_diff, 2),
            "contributions": contributions,
            "attribution_verified": abs(explained - round(total_diff, 2)) <= 0.02,
        }

    def _op_money_round(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """确定性分位四舍五入，输出与浮点裸加法的差值漂移。"""
        amounts = [float(a) for a in payload.get("amounts", []) if a is not None]
        rounded = [_round_money(a) for a in amounts]
        naive_total = sum(amounts)
        cent_total = _round_money(sum(rounded))
        return {
            "rounded": rounded,
            "count": len(rounded),
            "naive_total": round(naive_total, 10),
            "cent_total": cent_total,
            "float_drift": round(naive_total - cent_total, 10),
            "cent_safe": abs(naive_total - cent_total) < 0.005,
        }

    def _op_conservation_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """零容差勾稽：Total 必须等于 Parts 之和（默认容差 0.001）。"""
        parts = [float(p) for p in payload.get("parts", [])]
        total = float(payload.get("total", 0.0))
        tol = float(payload.get("tolerance", 0.001))
        parts_sum = _round_money(sum(parts))
        diff = round(total - parts_sum, 6)
        return {
            "parts_sum": parts_sum,
            "total": _round_money(total),
            "difference": diff,
            "tolerance": tol,
            "balanced": abs(diff) <= tol,
        }

    def _op_dispersion_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """离散度与分位数（P50/P90/P99），用于分布度量。"""
        values = sorted(float(v) for v in payload.get("values", []) if v is not None)
        if not values:
            return {"count": 0, "p50": 0.0, "p90": 0.0, "p99": 0.0, "cv": 0.0}

        def _pct(q: float) -> float:
            if len(values) == 1:
                return values[0]
            pos = (len(values) - 1) * q
            lo, hi = math.floor(pos), math.ceil(pos)
            return values[lo] + (values[hi] - values[lo]) * (pos - lo)

        mean_val = sum(values) / len(values)
        cv = (statistics.pstdev(values) / mean_val) if mean_val else 0.0
        return {
            "count": len(values),
            "p50": round(_pct(0.50), 4),
            "p90": round(_pct(0.90), 4),
            "p99": round(_pct(0.99), 4),
            "cv": round(cv, 4),
        }


class AnalysisEngineManager:
    """引擎管理器，提供多引擎注册、能力清单、健康探测与自动路由。"""

    def __init__(self):
        self.sql = DuckDBSQLSandbox()
        self._engines: Dict[str, Any] = {"native": NativeAnalysisEngine("native_in_memory")}
        if self.sql.available:
            self._engines["duckdb"] = self.sql

    def register_engine(self, name: str, engine: Any) -> None:
        self._engines[name] = engine

    def get_engine(self, name: str = "native") -> Optional[Any]:
        return self._engines.get(name)

    def get_sql_sandbox(self) -> DuckDBSQLSandbox:
        return self.sql

    def capabilities(self) -> Dict[str, List[str]]:
        caps: Dict[str, List[str]] = {}
        for name, eng in self._engines.items():
            if name == "duckdb":
                caps[name] = ["sql", "csv_scan", "columnar_aggregate"]
            else:
                caps[name] = eng.capabilities()
        return caps

    def run_sql(self, sql: str, params: Optional[List[Any]] = None) -> AnalyticalQueryResult:
        """真实 SQL 执行入口；DuckDB 不可用时明确报错而非伪造结果。"""
        if not self.sql.available:
            return AnalyticalQueryResult(ok=False, data={}, error="DuckDB engine unavailable")
        return self.sql.execute(sql, params)

    def has_sql_engine(self) -> bool:
        return bool(self.sql.available)

    def probe_all(self) -> Dict[str, Any]:
        results = {}
        all_ok = True
        for name, eng in self._engines.items():
            t0 = time.perf_counter()
            healthy = eng.is_healthy()
            latency = round((time.perf_counter() - t0) * 1000.0, 3)
            results[name] = {"healthy": healthy, "id": eng.engine_id, "latency_ms": latency}
            if not healthy:
                all_ok = False
        return {
            "all_healthy": all_ok,
            "engine_count": len(self._engines),
            "engines": results,
            "capabilities": self.capabilities(),
            "degraded": (not self.sql.available),
            "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
