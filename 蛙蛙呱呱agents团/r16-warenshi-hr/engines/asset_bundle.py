# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - [L07] 伴生消费层：下游机器消费资产包与 SARIF/Vega-Lite 伴随导出。

对标开源标杆：
- OASIS SARIF v2.1.0 (Static Analysis Results Interchange Format 国际工业标准)
- Vega-Lite 声明式可视化图表规范 (Stars > 11k)
- Downstream ERP/HCM integration

核心职责：
1. 伴生导出结构化 hr_bundle.json（包含花名册、组织架构、考勤、薪酬准备、门禁审计结果）；
2. 伴生导出符合 OASIS SARIF v2.1.0 国际标准的静态质检审查报告 hr_audit.sarif.json；
3. 伴生导出前端与管理看板可直接渲染的 Vega-Lite 声明式图表元数据 hr_chart.vega.json；
4. 物理落盘至 workspace/bundles/<run_id>/。
"""
from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(_HERE, "workspace")
BUNDLE_DIR = os.path.join(_WS, "bundles")


class HRAssetBundle:
    """HR 伴生资产包编译器与 SARIF/Vega 导出器。"""

    def __init__(self, output_root: str = BUNDLE_DIR):
        self.output_root = output_root

    def export_sarif(self, run_id: str, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建 OASIS SARIF v2.1.0 标准审计报告。"""
        results = []
        for v in violations:
            results.append({
                "ruleId": v.get("gate", "GATE-UNKNOWN"),
                "level": "error" if v.get("severity") == "CRITICAL" else "warning",
                "message": {"text": v.get("msg", "人事合规性审查告警")},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": v.get("file", "HR_SPEC.md")},
                        "region": {"startLine": v.get("line", 1)},
                    }
                }],
            })

        sarif_doc = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "R16-HR-Auditor",
                        "semanticVersion": "13.0.0",
                        "rules": [
                            {"id": "GATE-HR-01", "shortDescription": {"text": "薪酬总额校验"}},
                        ],
                    }
                },
                "invocations": [{
                    "executionSuccessful": len(results) == 0,
                    "endTimeUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }],
                "results": results,
            }],
        }
        return sarif_doc

    def export_vega_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Vega-Lite 声明式图表规范。"""
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "HR 数据可视化看板",
            "description": "薪酬或招聘漏斗可视化",
            "data": {
                "values": data.get("chart_values", [])
            },
            "mark": "bar",
            "encoding": {
                "x": {"field": "category", "type": "nominal", "axis": {"labelAngle": 0}},
                "y": {"field": "quantity", "type": "quantitative"},
            },
        }

    def compile_and_save(
        self,
        run_id: str,
        artifact_data: Optional[Dict[str, Any]] = None,
        violations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """伴随导出全套资产包 (Bundle JSON, SARIF JSON, Vega JSON) 并物理落盘。"""
        target_dir = os.path.join(self.output_root, run_id)
        os.makedirs(target_dir, exist_ok=True)

        data = artifact_data or {
            "run_id": run_id,
            "summary": "HR 数据导出",
        }

        # 1. 伴生导出 hr_bundle.json
        bundle_path = os.path.join(target_dir, "hr_bundle.json")
        bundle_content = {
            "schema_version": "v13.0",
            "run_id": run_id,
            "exported_at": datetime.datetime.now().isoformat(),
            "role": "r16-warenshi-hr",
            "payload": data,
        }
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_content, f, ensure_ascii=False, indent=2)

        # 2. 伴生导出 hr_audit.sarif.json
        sarif_path = os.path.join(target_dir, "hr_audit.sarif.json")
        sarif_doc = self.export_sarif(run_id, violations or [])
        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif_doc, f, ensure_ascii=False, indent=2)

        # 3. 伴生导出 hr_chart.vega.json
        vega_path = os.path.join(target_dir, "hr_chart.vega.json")
        vega_doc = self.export_vega_chart(data)
        with open(vega_path, "w", encoding="utf-8") as f:
            json.dump(vega_doc, f, ensure_ascii=False, indent=2)

        return {
            "bundle_file": bundle_path,
            "sarif_file": sarif_path,
            "vega_file": vega_path,
            "dir": target_dir,
        }
