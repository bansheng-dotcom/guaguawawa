# -*- coding: utf-8 -*-
"""L07 伴生消费层 —— 让下游 CI / BI / 编译器无需人肉转录即可消费。

病灶（体检结论）：升级前 R18 的产物只有人类可读的 result.json + Markdown，
下游 CI 无法解析门禁结论（没有标准 SARIF），BI 无法直接渲染（没有 Vega-Lite
规范），前端/编排器无法装配管道（没有血缘 AST）——每一项都要人类肉眼读一遍再
二次录入，工业流水线在这里断链。

对标标杆（Stars > 1k）：
- OASIS SARIF v2.1.0 + `semgrep/semgrep`（> 17k）：CI 可解析的静态分析结果；
- `vega/vega-lite`（> 4k）：声明式图表规范，前端零代码渲染；
- `dbt-labs/dbt`（> 14k）：manifest.json 作为下游消费的管道 AST。
（注：`microsoft/sarif-tools` 仅 160★，未达 1k 门槛，只可作 CLI 消费方式参考，不作标杆。）

本引擎落地：
1. `dataeng_bundle_<run>.json`：全量结构化交付包（schema_version + 门禁 + 指标 + 工件）；
2. `dataeng_audit_<run>.sarif.json`：严格 SARIF v2.1.0（ruleId/level/message/locations）；
3. `dataeng_chart_<run>.vega.json`：Vega-Lite v5 图表规范（门禁通过情况）；
4. `dataeng_lineage_<run>.ast.json`：管道/血缘 AST（节点 + 依赖边），供编译器装配。
"""
from __future__ import annotations

import json
import os
from core.workspace import role_workspace  # noqa: E402

import time
from typing import Any, Dict, List, Optional

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"
BUNDLE_SCHEMA_VERSION = "1.0.0"
TOOL_NAME = "R18-Washucang-DataEng"
TOOL_VERSION = "13.0.0"


class DataEngAssetBundle:
    """L07 伴生资产包导出器。"""

    def __init__(self, workspace_dir: Optional[str] = None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(os.path.dirname(here)))

    # ------------------------------------------------------------------ #
    # 构造
    # ------------------------------------------------------------------ #
    @staticmethod
    def _gates(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        gates = payload.get("gates") or []
        if gates and isinstance(gates[0], str):
            gates = [{"id": f"G{i + 1}", "name": g, "ok": True}
                     for i, g in enumerate(gates)]
        return [g for g in gates if isinstance(g, dict)]

    def build_bundle(self, run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        gates = self._gates(payload)
        return {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "kind": "dataeng_delivery_bundle",
            "run_id": run_id,
            "exported_at": payload.get("exported_at") or time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime()),
            "producer": {"role": "r18", "name": "蛙数仓", "tool": TOOL_NAME,
                         "version": TOOL_VERSION},
            "pipeline": payload.get("pipeline") or {},
            "spec": payload.get("spec") or {"source": "DATAENG_SPEC.md"},
            "gates": gates,
            "metrics": payload.get("metrics") or {},
            "checks": payload.get("checks") or [],
            "delivery_dag": payload.get("delivery_dag") or {},
            "scenarios": payload.get("scenarios") or [],
            "artifacts": payload.get("artifacts") or [],
        }

    def build_sarif(self, run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        gates = self._gates(payload)
        rules = [{"id": g.get("id", "G?"),
                  "name": g.get("name", ""),
                  "shortDescription": {"text": g.get("criteria", g.get("name", ""))},
                  "defaultConfiguration": {"level": "error"}}
                 for g in gates]
        results = []
        uri = payload.get("artifact_uri", "workspace/pipeline")
        for g in gates:
            if g.get("ok") is False:
                results.append({
                    "ruleId": g.get("id", "G?"),
                    "level": "error" if g.get("blocking", True) else "warning",
                    "message": {"text": g.get("message") or f"{g.get('name', '门禁')} 未通过"},
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": uri},
                        "region": {"startLine": 1}}}],
                })
        return {
            "$schema": SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": TOOL_NAME, "semanticVersion": TOOL_VERSION,
                                    "rules": rules}},
                "invocations": [{"executionSuccessful": not any(
                    r["level"] == "error" for r in results),
                    "properties": {"runId": run_id}}],
                "results": results,
            }],
        }

    def build_vega(self, run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        gates = self._gates(dict(payload or {}))
        values = [{"gate": g.get("name") or g.get("id", ""),
                   "status": 1 if g.get("ok") else 0,
                   "label": "PASS" if g.get("ok") else "FAIL"} for g in gates]
        if not values:
            values = [{"gate": "no_gate", "status": 0, "label": "N/A"}]
        return {
            "$schema": VEGA_SCHEMA,
            "description": f"R18 8 维发布门禁通过情况 · {run_id}",
            "data": {"values": values},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {"field": "gate", "type": "nominal", "axis": {"title": "门禁"}},
                "y": {"field": "status", "type": "quantitative", "axis": {"title": "通过=1/未过=0"}},
                "color": {"field": "label", "type": "nominal"},
            },
        }

    def build_ast(self, run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        dag = payload.get("delivery_dag") or {}
        nodes = dag.get("nodes") or [
            {"id": n, "title": n} for n in (dag.get("topological_order") or [])
        ]
        edges = dag.get("edges") or []
        return {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "kind": "dataeng_pipeline_ast",
            "run_id": run_id,
            "nodes": [{"id": n.get("id"), "stage": n.get("stage"),
                       "title": n.get("title"), "owner": n.get("owner")} for n in nodes],
            "edges": [{"from": e.get("from"), "to": e.get("to"),
                       "reason": e.get("reason", "")} for e in edges],
            "entry": (dag.get("topological_order") or [None])[0],
            "exit": (dag.get("topological_order") or [None])[-1],
        }

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    def export(self, run_id: str, payload: Optional[Dict[str, Any]] = None,
               out_dir: Optional[str] = None) -> Dict[str, Any]:
        target = out_dir or os.path.join(self.workspace_dir, "bundles")
        os.makedirs(target, exist_ok=True)
        bundle = self.build_bundle(run_id, payload)
        sarif = self.build_sarif(run_id, payload)
        vega = self.build_vega(run_id, payload)
        ast = self.build_ast(run_id, payload)
        paths = {
            "bundle": os.path.join(target, f"dataeng_bundle_{run_id}.json"),
            "sarif": os.path.join(target, f"dataeng_audit_{run_id}.sarif.json"),
            "vega": os.path.join(target, f"dataeng_chart_{run_id}.vega.json"),
            "ast": os.path.join(target, f"dataeng_lineage_{run_id}.ast.json"),
        }
        for key, obj in (("bundle", bundle), ("sarif", sarif),
                         ("vega", vega), ("ast", ast)):
            with open(paths[key], "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
        return {"ok": True, "run_id": run_id, **paths,
                "sarif_results": len(sarif["runs"][0]["results"]),
                "gate_count": len(bundle["gates"])}

    # ------------------------------------------------------------------ #
    # 自校验（下游消费前先自证合规）
    # ------------------------------------------------------------------ #
    def validate_export(self, exported: Dict[str, Any]) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def ck(ok: bool, msg: str, dim: str) -> None:
            checks.append({"ok": bool(ok), "msg": msg, "dim": dim,
                           "sev": "OK" if ok else "BLOCKER"})

        for key in ("bundle", "sarif", "vega", "ast"):
            path = exported.get(key, "")
            ck(bool(path) and os.path.exists(path), f"{key} 工件落盘", f"l07.{key}")
        if os.path.exists(exported.get("bundle", "")):
            with open(exported["bundle"], encoding="utf-8") as f:
                bundle = json.load(f)
            ck(bundle.get("schema_version") == BUNDLE_SCHEMA_VERSION,
               f"bundle schema_version={bundle.get('schema_version')}", "l07.bundle_schema")
            ck(len(bundle.get("gates", [])) > 0, "bundle 含门禁结果", "l07.bundle_gates")
        if os.path.exists(exported.get("sarif", "")):
            with open(exported["sarif"], encoding="utf-8") as f:
                sarif = json.load(f)
            ck(sarif.get("version") == "2.1.0", "SARIF version=2.1.0", "l07.sarif_version")
            runs = sarif.get("runs") or [{}]
            ck(bool(runs[0].get("tool", {}).get("driver", {}).get("name")),
               "SARIF tool.driver.name 非空", "l07.sarif_tool")
            ck(isinstance(runs[0].get("results"), list), "SARIF results 为数组",
               "l07.sarif_results")
        if os.path.exists(exported.get("vega", "")):
            with open(exported["vega"], encoding="utf-8") as f:
                vega = json.load(f)
            ck(vega.get("$schema") == VEGA_SCHEMA, "Vega-Lite v5 schema", "l07.vega_schema")
            ck(bool((vega.get("data") or {}).get("values")), "Vega 数据非空", "l07.vega_data")
        if os.path.exists(exported.get("ast", "")):
            with open(exported["ast"], encoding="utf-8") as f:
                ast = json.load(f)
            ck(bool(ast.get("nodes")), "AST 含节点", "l07.ast_nodes")
            ck(ast.get("kind") == "dataeng_pipeline_ast", "AST kind 正确", "l07.ast_kind")
        ok = all(x["ok"] for x in checks)
        return {"ok": ok, "grade": "PASS" if ok else "FAIL", "checks": checks}


# --------------------------------------------------------------------------- #
# CLI：python -m engines.asset_bundle --run-id L07 --out-dir ... --out ...
# --------------------------------------------------------------------------- #
def _demo_payload() -> Dict[str, Any]:
    from engines import DataEngIntentCompiler, DataEngSpecLedger
    spec = DataEngSpecLedger().load_spec()
    dag = DataEngIntentCompiler().compile_intent(
        "把 orders 和 dwd_orders 最近30天增量做成看板，2小时内要新鲜")
    gates = []
    for i, g in enumerate(spec["gates"]):
        gates.append({**g, "ok": i != 3,
                      "message": "" if i != 3 else "空值率 0.12 > 0.10（实测）"})
    return {
        "pipeline": {"skill": "quality", "action": "check",
                     "intent": "把 orders 和 dwd_orders 最近30天增量做成看板"},
        "spec": {"version": spec["version"], "dri": spec["dri"]},
        "gates": gates,
        "metrics": {code: {"target": m["target"], "tolerance": m["tolerance"]}
                    for code, m in spec["metrics"].items()},
        "checks": [{"ok": g["ok"], "msg": g["name"], "dim": g["id"]} for g in gates],
        "delivery_dag": dag,
        "artifact_uri": "workspace/rounds/L02_dag.json",
    }


def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L07 伴生消费资产包")
    ap.add_argument("--run-id", default="demo")
    ap.add_argument("--out-dir", default="workspace/bundles")
    ap.add_argument("--payload", default="", help="可选 payload JSON")
    ap.add_argument("--out", default="", help="导出清单 JSON")
    args = ap.parse_args(argv)

    payload = _demo_payload()
    if args.payload:
        with open(args.payload, encoding="utf-8") as f:
            payload = json.load(f)
    bundle = DataEngAssetBundle()
    exported = bundle.export(args.run_id, payload, out_dir=args.out_dir)
    validation = bundle.validate_export(exported)
    out = {"ok": bool(exported["ok"] and validation["ok"]),
           "run_id": args.run_id, "exported": exported,
           "validation": validation}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": out["ok"], "run_id": args.run_id,
         "sarif_results": exported["sarif_results"],
         "files": [exported["bundle"], exported["sarif"], exported["vega"], exported["ast"]],
         "validation": validation["grade"]}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
