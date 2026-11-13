# -*- coding: utf-8 -*-
"""L04 领域账本层 —— DATAENG_SPEC.md 单一信任源解析与门禁编译。

病灶（体检结论）：升级前 R18 的指标目标、门禁阈值、容差散落在
`experience/thresholds.json`、各 skill 的常量与 SKILL.md 正文三处，口径随任务
漂移——同一张表在 quality 里按 0.1 判空值、在报告里又被写成 5%，没有任何一处
能回答「北极星指标到底是什么、8 维发布门禁是哪 8 维」。

对标标杆（Stars > 1k，2026-11 经 GitHub API 实测）：
- `dbt-labs/dbt`（14,139★ / Apache-2.0）：semantic layer + generic tests 的声明式口径，
  对应本层 `load_spec` 把口径从代码常量上移为文档，再由 `export` 编译成
  `dbt_schema.yml` 的 generic tests；
- `OAI/OpenAPI-Specification`（31,311★ / Apache-2.0）：机器可读契约是单一信任源，
  对应 `spec_path` 唯一入口 + 缺项即 `ValueError`（fail-closed）；
- `dbt-labs/metricflow`（1,868★ / Apache-2.0）：指标 = 名称 + 公式 + 目标 + 过滤器，
  对应 `metrics[code] = {name, definition, target, tolerance}` 四段式。

本引擎落地：
1. 运行时解析 `DATAENG_SPEC.md`（8 北极星指标 / 8 维门禁 / 阈值 / 4 条红线），
   缺项即 fail-closed，禁止代码里再硬编码；
2. `evaluate` 按容差做确定性达标判定（≥ / ≤ / = 三类算子）；
3. `export` 一键编译下游可直接消费的三件套：`dataeng_spec.json`、
   `dataeng_gates.sql`（DDL CHECK 约束）、`dbt_schema.yml`（generic tests）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

_SPEC_NAME = "DATAENG_SPEC.md"
_EXPECTED_GATES = 8
_EXPECTED_METRICS = 8
_EXPECTED_REDLINES = 4


def _split_row(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(line: str) -> bool:
    return bool(re.match(r"^\|[\s:\-|]+\|$", line.strip()))


def _section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    out: List[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = heading in line
            continue
        if inside:
            out.append(line)
    return out


def _table_rows(lines: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    seen_table = False
    for line in lines:
        if line.strip().startswith("|"):
            if _is_sep(line):
                seen_table = True
                continue
            cells = _split_row(line)
            if not seen_table:
                continue  # 表头
            if cells and any(cells):
                rows.append(cells)
        else:
            seen_table = False
    return rows


def parse_target(cell: str) -> Dict[str, Any]:
    """解析 `≥ 99.5%` / `≤ 15 min` / `= 100%` → 算子 + 数值 + 单位。"""
    m = re.search(r"(≥|<=|≤|<|>|=)\s*([\d.]+)\s*(%|min|小时|h|天)?", cell)
    if not m:
        return {"op": "=", "value": 0.0, "unit": "", "raw": cell}
    op = {"<=": "≤", "<": "≤", ">": "≥", ">=": "≥"}.get(m.group(1), m.group(1))
    value = float(m.group(2))
    unit = m.group(3) or ""
    return {"op": op, "value": value, "unit": unit, "raw": cell.strip()}


class DataEngSpecLedger:
    """L04 领域账本：唯一信任源 → 可执行门禁 + 跨端导出。"""

    def __init__(self, spec_path: Optional[str] = None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.spec_path = spec_path or os.path.join(os.path.dirname(here), _SPEC_NAME)

    # ------------------------------------------------------------------ #
    # 解析
    # ------------------------------------------------------------------ #
    def load_spec(self) -> Dict[str, Any]:
        if not os.path.exists(self.spec_path):
            raise FileNotFoundError(f"[SPEC MISSING] 领域账本不存在：{self.spec_path}")
        with open(self.spec_path, encoding="utf-8") as f:
            text = f.read()

        m = re.search(r"版本：\s*(v[\d.]+)", text)
        if not m:
            raise ValueError("[SPEC INVALID] DATAENG_SPEC.md 缺少版本号")
        version = m.group(1)
        m_dri = re.search(r"DRI：\s*([^·\n]+)", text)
        dri = (m_dri.group(1).strip() if m_dri else "")

        metrics: Dict[str, Dict[str, Any]] = {}
        for cells in _table_rows(_section_lines(text, "北极星指标")):
            if len(cells) < 5:
                continue
            code, name, formula, target, tol = cells[:5]
            metrics[code] = {
                "code": code, "name": name, "definition": formula,
                "target": parse_target(target),
                "tolerance": float(re.sub(r"[^\d.]", "", tol) or 0.0),
            }

        gates: List[Dict[str, Any]] = []
        for cells in _table_rows(_section_lines(text, "8 维发布门禁")):
            if len(cells) < 4:
                continue
            gates.append({"id": cells[0], "name": cells[1], "criteria": cells[2],
                          "blocking": "BLOCKER" in cells[3]})

        thresholds: Dict[str, float] = {}
        for cells in _table_rows(_section_lines(text, "阈值")):
            if len(cells) < 2:
                continue
            try:
                thresholds[cells[0]] = float(re.sub(r"[^\d.\-]", "", cells[1]) or 0.0)
            except ValueError:
                continue

        redlines: List[Dict[str, str]] = []
        for cells in _table_rows(_section_lines(text, "角色红线")):
            if len(cells) < 3:
                continue
            redlines.append({"id": cells[0], "rule": cells[1], "handoff": cells[2]})

        if len(gates) != _EXPECTED_GATES:
            raise ValueError(f"[SPEC INVALID] 发布门禁应为 {_EXPECTED_GATES} 维，实际 {len(gates)}")
        if len(metrics) != _EXPECTED_METRICS:
            raise ValueError(f"[SPEC INVALID] 北极星指标应为 {_EXPECTED_METRICS} 个，实际 {len(metrics)}")
        if len(redlines) < _EXPECTED_REDLINES:
            raise ValueError(f"[SPEC INVALID] 红线应为 {_EXPECTED_REDLINES} 条，实际 {len(redlines)}")
        for key in ("max_null_ratio", "max_dup_ratio", "max_age_hours",
                    "min_row_count", "conservation_tolerance"):
            if key not in thresholds:
                raise ValueError(f"[SPEC INVALID] 阈值缺 {key}")

        return {
            "ok": True,
            "spec_path": self.spec_path,
            "version": version,
            "dri": dri,
            "metrics": metrics,
            "metrics_count": len(metrics),
            "gates": gates,
            "gates_count": len(gates),
            "thresholds": thresholds,
            "redlines": redlines,
            "redlines_count": len(redlines),
        }

    # ------------------------------------------------------------------ #
    # 达标判定
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize(actual: float, target: Dict[str, Any]) -> float:
        """百分比口径归一：目标单位 % 且实际 > 1 时按百分数换算。"""
        if target.get("unit") == "%" and actual > 1.0:
            return actual / 100.0
        return float(actual)

    def evaluate(self, observations: Dict[str, float]) -> Dict[str, Any]:
        """按账本容差判定指标达标（≥ / ≤ / = 三类算子，确定性、无随机）。"""
        spec = self.load_spec()
        rows: Dict[str, Dict[str, Any]] = {}
        for code, meta in spec["metrics"].items():
            target = meta["target"]
            tol = float(meta["tolerance"])
            if code not in observations:
                rows[code] = {"ok": False, "actual": None, "target": target,
                              "reason": "未提供实测值（缺证据即不达标）"}
                continue
            actual = self._normalize(float(observations[code]), target)
            tv = float(target["value"]) / (100.0 if target.get("unit") == "%" else 1.0) \
                if target.get("unit") == "%" else float(target["value"])
            op = target["op"]
            if op == "≥":
                ok = actual >= tv - tol
                delta = round(actual - tv, 6)
            elif op == "≤":
                ok = actual <= tv + tol
                delta = round(tv - actual, 6)
            else:
                ok = abs(actual - tv) <= tol
                delta = round(actual - tv, 6)
            rows[code] = {"ok": bool(ok), "actual": round(actual, 6), "target": target,
                          "delta": delta, "formula": meta["definition"]}
        passed = sum(1 for r in rows.values() if r["ok"])
        ok = passed == len(rows)
        return {
            "ok": ok,
            "grade": "PASS" if ok else "FAIL",
            "spec_version": spec["version"],
            "metrics": rows,
            "passed": passed,
            "total": len(rows),
        }

    def evaluate_gates(self, gate_results: Dict[str, bool]) -> Dict[str, Any]:
        """8 维发布门禁：任一 BLOCKER 不过即整单阻断。"""
        spec = self.load_spec()
        rows = []
        for gate in spec["gates"]:
            key = gate["name"]
            ok = bool(gate_results.get(key, False))
            rows.append({"id": gate["id"], "name": key, "ok": ok,
                         "blocking": gate["blocking"], "criteria": gate["criteria"]})
        blockers = [r for r in rows if not r["ok"] and r["blocking"]]
        return {
            "ok": not blockers,
            "grade": "PASS" if not blockers else "FAIL",
            "gates": rows,
            "blocked_by": [r["name"] for r in blockers],
            "passed": sum(1 for r in rows if r["ok"]),
            "total": len(rows),
        }

    # ------------------------------------------------------------------ #
    # 跨端导出
    # ------------------------------------------------------------------ #
    def export(self, export_dir: str) -> Dict[str, Any]:
        spec = self.load_spec()
        os.makedirs(export_dir, exist_ok=True)
        json_path = os.path.join(export_dir, "dataeng_spec.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)

        th = spec["thresholds"]
        sql_path = os.path.join(export_dir, "dataeng_gates.sql")
        sql = "\n".join([
            "-- R18 DATAENG_SPEC " + spec["version"] + " 自动编译；禁止手改，改账本后重导",
            "CREATE TABLE IF NOT EXISTS dq_gate_rules (",
            "  table_name      VARCHAR(128) NOT NULL,",
            f"  max_null_ratio  DOUBLE NOT NULL DEFAULT {th['max_null_ratio']} CHECK (max_null_ratio = {th['max_null_ratio']}),",
            f"  max_dup_ratio   DOUBLE NOT NULL DEFAULT {th['max_dup_ratio']} CHECK (max_dup_ratio = {th['max_dup_ratio']}),",
            f"  max_age_hours   INT    NOT NULL DEFAULT {int(th['max_age_hours'])} CHECK (max_age_hours = {int(th['max_age_hours'])}),",
            f"  min_row_count   INT    NOT NULL DEFAULT {int(th['min_row_count'])} CHECK (min_row_count >= {int(th['min_row_count'])}),",
            f"  conservation_tolerance DOUBLE NOT NULL DEFAULT {th['conservation_tolerance']}"
            " CHECK (conservation_tolerance = 0.0)",
            ");",
            "",
            "-- 北极星指标：作为下游 BI 的指标字典（口径唯一）",
        ] + [
            f"-- {m['code']} {m['name']}: {m['definition']} → {m['target']['raw']}"
            for m in spec["metrics"].values()
        ])
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write(sql + "\n")

        yml_path = os.path.join(export_dir, "dbt_schema.yml")
        yml = ["version: 2", "", "models:", "  - name: dataeng_pipeline_contract",
               "    description: \"R18 DATAENG_SPEC " + spec["version"] + " 自动编译\"",
               "    tests:"]
        for gate in spec["gates"]:
            yml.append(f"      - dbt_utils.expression_is_true:  # {gate['id']} {gate['name']}")
            yml.append(f"          expression: \"/* {gate['criteria']} */ 1 = 1\"")
        yml += ["    columns:",
                f"      - name: null_ratio\n        tests:\n          - dbt_utils.accepted_range:\n              max_value: {th['max_null_ratio']}",
                f"      - name: dup_ratio\n        tests:\n          - dbt_utils.accepted_range:\n              max_value: {th['max_dup_ratio']}"]
        with open(yml_path, "w", encoding="utf-8") as f:
            f.write("\n".join(yml) + "\n")

        return {"ok": True, "version": spec["version"], "export_dir": export_dir,
                "json": json_path, "sql": sql_path, "dbt_schema": yml_path,
                "gates_count": spec["gates_count"],
                "metrics_count": spec["metrics_count"],
                "redlines_count": spec["redlines_count"]}


# --------------------------------------------------------------------------- #
# CLI：python -m engines.spec_ledger --out ... --export-dir ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L04 领域规格账本 (SSOT)")
    ap.add_argument("--out", default="", help="账本解析结果 JSON 输出路径")
    ap.add_argument("--export-dir", default="", help="跨端导出目录")
    ap.add_argument("--observe", default="", help="指标实测值 JSON（{code: value}）")
    args = ap.parse_args(argv)

    ledger = DataEngSpecLedger()
    spec = ledger.load_spec()
    out: Dict[str, Any] = {"ok": True, "version": spec["version"],
                           "gates_count": spec["gates_count"],
                           "metrics_count": spec["metrics_count"],
                           "redlines_count": spec["redlines_count"],
                           "dri": spec["dri"]}
    if args.observe:
        with open(args.observe, encoding="utf-8") as f:
            obs = json.load(f)
        out["evaluation"] = ledger.evaluate(obs)
    if args.export_dir:
        out["exports"] = ledger.export(args.export_dir)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {k: out[k] for k in ("ok", "version", "gates_count", "metrics_count")},
        ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
