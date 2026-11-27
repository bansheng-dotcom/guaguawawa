# -*- coding: utf-8 -*-
"""第 4 段 Testing：测试金字塔 + 契约测试 + E2E。

硬约束：
  - 金字塔不是倒三角：单元 ≥ 集成 ≥ 契约 ≥ E2E，且都不为 0；
  - 每个 API 端点至少一条契约测试；
  - E2E 的 covers 必须与 feature 的验收 ID 一一覆盖（场景=acceptance）；
  - 主路径 / 边界 / 失败态三类覆盖都要有；
  - 不允许 skip 制造假通过。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    tests = brief.get("tests") or {}
    endpoints = (brief.get("api") or {}).get("endpoints") or []
    acceptance_ids = [a.get("id") for a in (brief.get("feature") or {}).get("acceptance") or []]
    e2e = [{"id": e.get("id", ""), "scenario": e.get("scenario", ""),
            "steps": e.get("steps") or [], "expected": e.get("expected", ""),
            "covers": e.get("covers") or []}
           for e in tests.get("e2e") or []]
    scenarios = sorted({c for e in e2e for c in e.get("covers") or []})
    contract = [{"id": t.get("id", ""), "endpoint": t.get("endpoint", ""),
                 "schema": t.get("schema", "")}
                for t in tests.get("contract_tests") or []]
    art: Dict[str, Any] = {
        "artifact": "testing",
        "stage": "testing",
        "project": brief.get("project", ""),
        "pyramid": tests.get("pyramid") or {},
        "suites": tests.get("suites") or {},
        "contract_tests": contract,
        "e2e": e2e,
        "scenario_ids": scenarios,
        "acceptance_ids": sorted(i for i in acceptance_ids if i),
        "endpoint_keys": [f"{e.get('method')} {e.get('path')}" for e in endpoints],
        "coverage": tests.get("coverage") or {},
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """测试门禁：金字塔、契约、E2E、验收映射、三类覆盖、无 skip。"""
    py = art.get("pyramid") or {}
    unit, integ = int(py.get("unit", 0)), int(py.get("integration", 0))
    contract_n, e2e_n = int(py.get("contract", 0)), int(py.get("e2e", 0))
    contract = art.get("contract_tests") or []
    e2e = art.get("e2e") or []
    endpoint_keys = set(art.get("endpoint_keys") or [])
    covered_endpoints = {t.get("endpoint") for t in contract}
    cov = art.get("coverage") or {}
    checks = [
        ck(unit > 0 and unit >= integ >= contract_n >= e2e_n and e2e_n > 0,
           "金字塔：单元≥集成≥契约≥E2E 且均>0", "testing:pyramid", "CRITICAL"),
        ck(endpoint_keys <= covered_endpoints and len(contract) >= len(endpoint_keys),
           "每个 API 端点至少一条契约测试", "testing:contract", "CRITICAL"),
        ck(len(e2e) >= 1 and all(nonempty_str(e.get("scenario")) and
                                 len(e.get("steps") or []) >= 2 for e in e2e),
           "E2E 场景含 ≥2 步操作", "testing:e2e", "CRITICAL"),
        ck(set(art.get("scenario_ids") or []) == set(art.get("acceptance_ids") or []) and
           bool(art.get("acceptance_ids")),
           "E2E 覆盖场景与验收 ID 一一对应", "testing:acceptance_mapping", "CRITICAL"),
        ck(all(cov.get(k) for k in ("main", "boundary", "failure")),
           "主路径/边界/失败态三类覆盖", "testing:coverage", "CRITICAL"),
        ck(int((art.get("suites") or {}).get("skipped", 0)) == 0,
           "不允许 skip 制造假通过", "testing:no_skipped", "CRITICAL"),
    ]
    return gate(checks, "testing")


def render(art: Dict[str, Any]) -> str:
    py = art.get("pyramid") or {}
    ct_rows = [[t.get("id"), t.get("endpoint"), t.get("schema")]
               for t in art.get("contract_tests") or []]
    e2_rows = [[e.get("id"), e.get("scenario"), "、".join(e.get("covers") or []),
                e.get("expected")] for e in art.get("e2e") or []]
    summary = (f"金字塔：单元 {py.get('unit')} / 集成 {py.get('integration')} / "
               f"契约 {py.get('contract')} / E2E {py.get('e2e')}；"
               f"覆盖：主路径={art.get('coverage', {}).get('main')}、"
               f"边界={art.get('coverage', {}).get('boundary')}、"
               f"失败态={art.get('coverage', {}).get('failure')}。")
    tables = [
        "## 契约测试", "", md_table(["ID", "端点", "Schema"], ct_rows),
        "", "## E2E 场景", "", md_table(["ID", "场景", "覆盖验收", "预期"], e2_rows),
    ]
    return render_stage(art, summary, tables)
