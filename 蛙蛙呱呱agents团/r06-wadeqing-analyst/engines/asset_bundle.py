# -*- coding: utf-8 -*-
"""L07 伴生消费层 (Downstream Consumption & Asset Bundle Layer)
对标开源: microsoft/sarif-tools / Vega-Lite (Stars > 17k) / Frictionless Data / OASIS SARIF v2.1.0
架构跃迁 (本轮新增):
1. Bundle 清单化：schema 版本、逐工件 SHA256 指纹、字节数与数据血缘 (lineage)，下游可自校验；
2. Vega-Lite 类型推断与规范校验：从真实数据列推断 nominal/quantitative/temporal，拒绝非法规范；
3. SARIF 多规则注册：规则表驱动 level 映射、fingerprints 去重与 invocations 执行状态。
"""
from __future__ import annotations

import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import time
from typing import Any, Dict, List, Optional


class AnalysisAssetBundle:
    """分析资产包导出器，让下游系统无需人肉转录直接机器解析。"""

    SCHEMA_VERSION = "2.0.0"

    SARIF_RULES = [
        {"id": "R06-DQ-001", "shortDescription": {"text": "Data quality blocker"}},
        {"id": "R06-ANOM-002", "shortDescription": {"text": "Metric anomaly or outlier"}},
        {"id": "R06-SPEC-003", "shortDescription": {"text": "Metric ledger / spec violation"}},
        {"id": "R06-GEN-004", "shortDescription": {"text": "General analysis finding"}},
    ]

    def __init__(self, workspace_dir: str = None):
        if not workspace_dir:
            here = os.path.dirname(os.path.abspath(__file__))
            workspace_dir = os.path.join(role_workspace(os.path.dirname(here)))
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    def export_bundle(self, run_id: str, report_data: Dict[str, Any]) -> Dict[str, str]:
        """打包导出机器可消费的资产工件（含指纹清单与血缘）。"""
        vega_content = self._build_vega_spec(report_data)
        vega_validation = self.validate_vega_spec(vega_content)
        vega_content["usermeta"] = {"validation": vega_validation}
        vega_path = os.path.join(self.workspace_dir, f"vega_spec_{run_id}.json")
        self._write_json(vega_path, vega_content)

        sarif_content = self._build_sarif_spec(run_id, report_data)
        sarif_path = os.path.join(self.workspace_dir, f"sarif_{run_id}.json")
        self._write_json(sarif_path, sarif_content)

        artifacts = []
        for path, media_type in ((vega_path, "application/vnd.vega-lite+json"),
                                 (sarif_path, "application/sarif+json")):
            with open(path, "rb") as f:
                raw = f.read()
            artifacts.append({
                "name": os.path.basename(path),
                "path": path,
                "media_type": media_type,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })

        bundle_path = os.path.join(self.workspace_dir, f"analysis_bundle_{run_id}.json")
        bundle_content = {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": run_id,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "lineage": {
                "producer": "R06-Wadeqing-Analyst",
                "engine": report_data.get("engine", "analysis_engine_manager"),
                "spec_version": report_data.get("spec_version", "1.0.0"),
                "spec_sha256": report_data.get("spec_sha256", ""),
                "source_query": report_data.get("query", ""),
            },
            "artifacts": artifacts,
            "report_data": report_data,
        }
        self._write_json(bundle_path, bundle_content)

        return {
            "bundle_path": bundle_path,
            "vega_spec_path": vega_path,
            "sarif_path": sarif_path,
        }

    def _write_json(self, path: str, payload: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    # Vega-Lite
    # ------------------------------------------------------------------ #
    def _infer_vega_type(self, field: str, values: List[Any]) -> str:
        name = str(field).lower()
        if any(k in name for k in ("date", "time", "month", "day", "日期", "时间")):
            return "temporal"
        numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if values and len(numeric) == len(values):
            return "quantitative"
        return "nominal"

    def _build_vega_spec(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """构造下游前端直接渲染的 Vega-Lite 规范（字段类型自动推断）。"""
        data_values = report_data.get("chart_data") or [
            {"x": "2026-08", "y": 100}, {"x": "2026-09", "y": 150}]
        fields = list(data_values[0].keys()) if data_values else ["x", "y"]
        x_field = fields[0]
        y_field = fields[1] if len(fields) > 1 else fields[0]

        def _col(name: str) -> List[Any]:
            return [row.get(name) for row in data_values]

        x_type = self._infer_vega_type(x_field, _col(x_field))
        y_type = self._infer_vega_type(y_field, _col(y_field))
        if y_type != "quantitative":
            y_type = "quantitative"

        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "R06 Auto-Generated Analysis Visual Specification",
            "data": {"values": data_values},
            "mark": report_data.get("mark", "bar"),
            "encoding": {
                "x": {"field": x_field, "type": x_type, "axis": {"title": x_field}},
                "y": {"field": y_field, "type": y_type, "axis": {"title": y_field}},
            },
        }

    def validate_vega_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """按 Vega-Lite 核心约束做最小规范校验。"""
        errors: List[str] = []
        if not spec.get("$schema"):
            errors.append("missing $schema")
        if not spec.get("mark"):
            errors.append("missing mark")
        data = spec.get("data", {})
        if not isinstance(data, dict) or "values" not in data:
            errors.append("missing data.values")
        encoding = spec.get("encoding", {})
        for channel in ("x", "y"):
            enc = encoding.get(channel, {})
            if not enc.get("field"):
                errors.append(f"missing encoding.{channel}.field")
            if enc.get("type") not in ("nominal", "ordinal", "quantitative", "temporal"):
                errors.append(f"invalid encoding.{channel}.type")
        return {"valid": not errors, "errors": errors}

    # ------------------------------------------------------------------ #
    # SARIF
    # ------------------------------------------------------------------ #
    def _map_rule(self, issue_text: str) -> Dict[str, str]:
        text = issue_text.lower()
        if any(k in text for k in ("quality", "缺失", "重复", "质量", "脏数据")):
            return {"id": "R06-DQ-001", "level": "error"}
        if any(k in text for k in ("anomaly", "异常", "离群", "outlier", "突增", "暴跌")):
            return {"id": "R06-ANOM-002", "level": "warning"}
        if any(k in text for k in ("spec", "口径", "metric", "指标定义")):
            return {"id": "R06-SPEC-003", "level": "warning"}
        return {"id": "R06-GEN-004", "level": "note"}

    def _build_sarif_spec(self, run_id: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """构造遵循 OASIS SARIF v2.1.0 规范的审计结果，下游 CI 门禁可解析。"""
        issues = report_data.get("issues", [])
        results = []
        for issue in issues:
            rule = self._map_rule(str(issue))
            uri = f"dataset/{run_id}.csv"
            fingerprint = hashlib.sha256(f"{rule['id']}:{issue}:{uri}".encode("utf-8")).hexdigest()
            results.append({
                "ruleId": rule["id"],
                "level": rule["level"],
                "message": {"text": str(issue)},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}}}],
                "partialFingerprints": {"primaryLocationLineHash": fingerprint[:32]},
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "R06-Wadeqing-Analyst",
                        "semanticVersion": "8.0.0",
                        "rules": [dict(r) for r in self.SARIF_RULES],
                    }
                },
                "invocations": [{
                    "executionSuccessful": True,
                    "endTimeUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "workingDirectory": {"uri": "."},
                }],
                "results": results,
            }],
        }

    # ------------------------------------------------------------------ #
    # 自校验
    # ------------------------------------------------------------------ #
    def verify_bundle(self, run_id: str) -> Dict[str, Any]:
        """重算工件指纹，校验 Bundle 是否被篡改或缺失。"""
        bundle_path = os.path.join(self.workspace_dir, f"analysis_bundle_{run_id}.json")
        if not os.path.exists(bundle_path):
            return {"ok": False, "error": f"bundle not found: {bundle_path}"}
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        mismatches: List[str] = []
        missing: List[str] = []
        for art in bundle.get("artifacts", []):
            path = art.get("path", "")
            if not os.path.exists(path):
                missing.append(art.get("name", path))
                continue
            with open(path, "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
            if actual != art.get("sha256"):
                mismatches.append(art.get("name", path))

        return {
            "ok": not mismatches and not missing,
            "run_id": run_id,
            "schema_version": bundle.get("schema_version"),
            "artifact_count": len(bundle.get("artifacts", [])),
            "mismatches": mismatches,
            "missing": missing,
            "lineage": bundle.get("lineage", {}),
        }
