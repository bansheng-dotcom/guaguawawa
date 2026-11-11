# -*- coding: utf-8 -*-
"""L07 伴生消费层 —— 上下游机器可消费的模型工程资产包 (Bundle / SARIF / Vega)。

SOP v13.0 L07 体检病灶（R19 真实断点）：
    1. 产物只有人类可读的 Markdown/JSON，CI、模型注册库、看板引擎必须
       人肉二次录入，无法机器消费；
    2. 没有标准审计格式：发布证据散落在 checks[] 里，R04/R20 无法直接用
       静态分析工具聚合（缺 OASIS SARIF v2.1.0）；
    3. 图表只有文字描述，前端图表引擎拿不到可渲染的 Vega-Lite 规格。

对标开源标杆（Stars > 1k）：
    * microsoft/sarif-tools (>1k) + OASIS SARIF v2.1.0 —— 标准审计结果格式
    * vega/vega-lite (>4k) —— 声明式图表规格
    * mlflow/mlflow (>20k) —— 模型工件 manifest 与指纹

落地的最低 3 项架构升级：
    1. `ml_bundle_<run>.json`：工件清单 + 每工件 SHA256 + 血缘 AST；
    2. `ml_audit_<run>.sarif.json`：合规 SARIF 2.1.0（tool/rules/results/invocations/artifacts）；
    3. `ml_eval_chart_<run>.vega.json`：Vega-Lite v5 指标柱状图规格。

用法：
    python -m engines.asset_bundle --run-id L07 --out-dir workspace/bundles \
        --out workspace/rounds/L07_bundle.json
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:  # 包内 / 脚本双模式
    from .runtime_engine import R19RuntimeEngine
except ImportError:  # pragma: no cover
    from runtime_engine import R19RuntimeEngine  # type: ignore


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _merkle_root(hashes: List[str]) -> str:
    """确定性两两拼接 Merkle 根（已排序，奇数节点自复制）。"""
    level = sorted(h for h in hashes if h)
    if not level:
        return ""
    while len(level) > 1:
        nxt: List[str] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(_sha256_bytes((left + right).encode("utf-8")))
        level = nxt
    return level[0]


class R19AssetBundle:
    """模型工程资产包编译器：bundle + SARIF + Vega-Lite。"""

    ENGINE = "R19AssetBundle"
    LAYER = "L07"
    SCHEMA = "r19.ml_bundle.v1"
    CAPABILITIES = [
        "Bundle 工件清单 + 逐文件 SHA256 指纹 + 阶段血缘 (lineage AST)",
        "OASIS SARIF v2.1.0 审计结果 (tool/rules/results/invocations/artifacts)",
        "Vega-Lite v5 指标图表规格，供前端图表引擎直接渲染",
        "[C2] SARIF baselineState/suppressions + 规则 help/helpUri/tags",
        "[C2] JUnit XML 导出 (CI 直接消费) 与 Merkle 内容寻址根",
        "[C2] Bundle schema 自校验 (必填字段/血缘完整性)",
    ]

    def __init__(self, out_dir: Optional[str] = None):
        self.out_dir = out_dir or os.path.join(role_workspace(_ROLE), "bundles")
        self.runtime = R19RuntimeEngine()

    # ------------------------------------------------------------------ #
    def _demo_payload(self) -> Dict[str, Any]:
        records = [
            {"expected": "pass", "predicted": "pass"},
            {"expected": "pass", "predicted": "pass"},
            {"expected": "fail", "predicted": "fail"},
            {"expected": "fail", "predicted": "pass"},
        ]
        metrics = self.runtime.compute_classification_metrics(records)
        lat = self.runtime.compute_latency_percentiles([120, 150, 180, 220, 400])
        return {"records": records, "metrics": metrics, "latency": lat,
                "checks": [
                    {"gate": "GATE-01", "ok": True, "msg": "指标可复算"},
                    {"gate": "GATE-02", "ok": True, "msg": "证据链完整"},
                    {"gate": "GATE-03", "ok": True, "msg": "回归门禁齐备"},
                ]}

    # ------------------------------------------------------------------ #
    def build(self, run_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or self._demo_payload()
        run_id = str(run_id or "run")
        metrics = payload.get("metrics") or {}
        latency = payload.get("latency") or {}
        checks = payload.get("checks") or [
            {"gate": "GATE-01", "ok": bool(metrics), "msg": "指标可复算"},
        ]
        now = datetime.datetime.now().isoformat(timespec="seconds")

        # 1) bundle
        bundle = {
            "schema": self.SCHEMA,
            "run_id": run_id,
            "role": "R19 蛙智模 · 模型工程与 AI 评估官",
            "generated_at": now,
            "metrics": metrics,
            "latency": latency,
            "gate_summary": {
                "total": len(checks),
                "passed": sum(1 for c in checks if c.get("ok")),
                "verdict": "PASS" if all(c.get("ok") for c in checks) else "FAIL",
            },
            "lineage": {
                "nodes": ["audit", "track", "evaluate", "regression", "decide"],
                "edges": [["audit", "track"], ["track", "evaluate"],
                          ["track", "regression"], ["evaluate", "decide"],
                          ["regression", "decide"]],
                "artifact_type": "model_engineering",
            },
        }

        # 2) SARIF 2.1.0
        rules: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        for c in checks:
            rid = f"R19-{c.get('gate', 'GATE-00')}"
            if rid not in [r["id"] for r in rules]:
                rules.append({"id": rid, "name": c.get("gate", "gate"),
                              "shortDescription": {"text": "R19 模型工程发布门禁"},
                              "fullDescription": {"text": "R19 蛙智模 8 维发布门禁之一，"
                                                          "用于模型工程交付前的硬性合规裁决"},
                              "help": {"text": "修复方式：补齐证据链并重跑回归门禁。",
                                       "markdown": "见 `ML_SPEC.md` 门禁矩阵"},
                              "helpUri": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/",
                              "properties": {"tags": ["model-engineering", "r19", "gate"]},
                              "defaultConfiguration": {"level": "error"}})
            fp = _sha256_bytes(f"{run_id}:{rid}:{c.get('msg', '')}".encode("utf-8"))[:16]
            baseline = (payload.get("baseline_fingerprints") or {})
            result = {
                "ruleId": rid,
                "level": "note" if c.get("ok") else "error",
                "message": {"text": str(c.get("msg", ""))},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": "ml_bundle.json"}}}],
                "partialFingerprints": {"r19Gate/v1": fp},
                "baselineState": ("unchanged" if baseline.get(rid) == fp else "new"),
                "properties": {"gate": c.get("gate", ""), "ok": bool(c.get("ok"))},
            }
            if c.get("suppressed"):
                result["suppressions"] = [{"kind": "external",
                                           "justification": str(c.get("suppressed_reason",
                                                                      "已人工复核豁免"))}]
            results.append(result)
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": "R19-ML-Auditor", "version": "13.0",
                                    "informationUri": "https://github.com/mlflow/mlflow",
                                    "rules": rules}},
                "invocations": [{"executionSuccessful": all(c.get("ok") for c in checks),
                                 "endTimeUtc": now + "Z"}],
                "results": results,
                "properties": {"run_id": run_id, "role": "r19"},
            }],
        }

        # 3) Vega-Lite v5
        values = [{"metric": "accuracy", "value": metrics.get("accuracy", 0.0)},
                  {"metric": "precision", "value": metrics.get("precision", 0.0)},
                  {"metric": "recall", "value": metrics.get("recall", 0.0)},
                  {"metric": "f1", "value": metrics.get("f1", 0.0)}]
        vega = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": f"R19 模型评估指标 · {run_id}",
            "description": "由 R19 AssetBundle 生成，供前端图表引擎直接渲染",
            "data": {"values": values},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {"field": "metric", "type": "nominal", "title": "指标"},
                "y": {"field": "value", "type": "quantitative", "title": "取值",
                      "scale": {"domain": [0, 1]}},
                "color": {"field": "metric", "type": "nominal"},
            },
        }

        # 4) JUnit XML（CI 直接消费）
        from xml.sax.saxutils import escape as _xml_escape
        failed = [c for c in checks if not c.get("ok")]
        junit_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                       f'<testsuite name="R19-ML-Gates" tests="{len(checks)}" '
                       f'failures="{len(failed)}" errors="0" skipped="0" '
                       f'timestamp="{now}">']
        for c in checks:
            gate_name = _xml_escape(str(c.get("gate", "GATE-00")))
            junit_lines.append(f'  <testcase classname="R19.gates.{_xml_escape(run_id)}" '
                               f'name="{gate_name}">')
            if not c.get("ok"):
                junit_lines.append(f'    <failure message="{_xml_escape(str(c.get("msg", "门禁未通过")))}"/>')
            junit_lines.append('  </testcase>')
        junit_lines.append('</testsuite>')
        junit_text = "\n".join(junit_lines)

        # 5) 落盘 + 指纹
        os.makedirs(self.out_dir, exist_ok=True)
        paths = {
            "bundle_file": os.path.join(self.out_dir, f"ml_bundle_{run_id}.json"),
            "sarif_file": os.path.join(self.out_dir, f"ml_audit_{run_id}.sarif.json"),
            "vega_file": os.path.join(self.out_dir, f"ml_eval_chart_{run_id}.vega.json"),
            "junit_file": os.path.join(self.out_dir, f"ml_junit_{run_id}.xml"),
        }
        for key, obj in (("bundle_file", bundle), ("sarif_file", sarif), ("vega_file", vega)):
            with open(paths[key], "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
        with open(paths["junit_file"], "w", encoding="utf-8") as f:
            f.write(junit_text)

        files = {os.path.basename(p): {"sha256": _sha256_file(p),
                                       "bytes": os.path.getsize(p)}
                 for p in paths.values()}
        bundle["artifacts"] = [{"name": k, **v} for k, v in files.items()]
        bundle["junit"] = {"tests": len(checks), "failures": len(failed)}
        # Merkle 内容寻址根（排除 bundle 自身，避免自引用不动点）
        merkle = _merkle_root([v["sha256"] for k, v in files.items()
                               if k != os.path.basename(paths["bundle_file"])])
        bundle["merkle"] = {"root": merkle, "algorithm": "sha256-pairwise",
                            "leaves": len(files) - 1}
        required = ("schema", "run_id", "role", "metrics", "gate_summary",
                    "lineage", "artifacts")
        missing = [k for k in required if not bundle.get(k)]
        lineage = bundle.get("lineage") or {}
        lineage_ok = bool(lineage.get("nodes")) and bool(lineage.get("edges"))
        bundle["schema_check"] = {"ok": not missing and lineage_ok,
                                  "missing": missing,
                                  "lineage_ok": lineage_ok,
                                  "required": list(required)}
        with open(paths["bundle_file"], "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
        files[os.path.basename(paths["bundle_file"])] = {
            "sha256": _sha256_file(paths["bundle_file"]),
            "bytes": os.path.getsize(paths["bundle_file"])}

        return {"ok": True, "engine": self.ENGINE, "layer": self.LAYER,
                "run_id": run_id, "paths": paths, "files": files,
                "bundle": bundle, "sarif": sarif, "vega": vega,
                "junit": junit_text, "merkle_root": merkle,
                "schema_check": bundle["schema_check"],
                "capabilities": list(self.CAPABILITIES), "timestamp": now}

    def compile_and_save(self, run_id: str,
                         payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        built = self.build(run_id, payload)
        return {"ok": True, "bundle_file": built["paths"]["bundle_file"],
                "sarif_file": built["paths"]["sarif_file"],
                "vega_file": built["paths"]["vega_file"],
                "files": built["files"], "run_id": run_id}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L07 资产包与 SARIF/Vega 导出")
    ap.add_argument("--run-id", default="L07")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--out", default=None, help="汇总探针输出")
    args = ap.parse_args(argv)

    eng = R19AssetBundle(args.out_dir)
    built = eng.build(args.run_id)
    summary = {"ok": built["ok"], "run_id": built["run_id"],
               "files": built["files"], "paths": built["paths"],
               "sarif_version": built["sarif"]["version"],
               "vega_schema": built["vega"]["$schema"]}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": built["ok"], "run_id": built["run_id"],
                      "files": list(built["files"]), "sarif": built["sarif"]["version"],
                      "out": args.out}, ensure_ascii=False))
    return 0 if built["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
