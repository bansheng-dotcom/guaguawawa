# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - [L07] 伴生消费层：下游机器可消费资产包与 SARIF/Vega 规范导出引擎。

对标开源标杆：
- OASIS SARIF v2.1.0 (Static Analysis Results Interchange Format)
- Vega-Lite 声明式可视化图表规范 (Stars > 12k)

核心职责：
1. 伴生导出 downstream CRM/工单系统直接消费的结构化资产包 `csm_bundle.json`；
2. 导出符合国际标准 OASIS SARIF v2.1.0 规范的客户成功质检审计报告 `csm_audit.sarif.json`；
3. 导出前端可直接无缝渲染的 Vega-Lite 四维健康图表元数据 `csm_health_chart.vega.json`。
"""
from __future__ import annotations

import datetime
import json
import os
from core.workspace import role_workspace  # noqa: E402

from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_BUNDLE_DIR = os.path.join(role_workspace(_PARENT), "bundles")


class CsmAssetBundle:
    """客户成功伴生资产包导出与标准化格式转换引擎。"""

    def __init__(self, export_dir: str = DEFAULT_BUNDLE_DIR):
        self.export_dir = export_dir

    def generate_sarif(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成符合 OASIS SARIF v2.1.0 标准的静态审计报告。"""
        results = []
        rules = [
            {
                "id": "CSM001",
                "name": "FirstResponseSlaBreached",
                "shortDescription": {"text": "全渠道客服首响超时 (GATE-01)"},
                "defaultConfiguration": {"level": "warning"},
            },
            {
                "id": "CSM002",
                "name": "TicketReopenRateExceeded",
                "shortDescription": {"text": "工单重开率超出警戒线 0.15 (GATE-03)"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "CSM003",
                "name": "RenewalDualGateFailed",
                "shortDescription": {"text": "续约双门槛不达标 (GATE-06)"},
                "defaultConfiguration": {"level": "error"},
            },
        ]

        for issue in issues:
            results.append({
                "ruleId": issue.get("rule_id", "CSM003"),
                "level": issue.get("level", "error"),
                "message": {"text": issue.get("message", "客户健康门禁未通过")},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.get("target", "client_profile")},
                        "region": {"startLine": 1},
                    }
                }],
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "CSM-Health-Auditor",
                        "semanticVersion": "11.0.0",
                        "rules": rules,
                    }
                },
                "results": results,
            }],
        }

    def generate_vega_spec(self, health_data: Dict[str, float]) -> Dict[str, Any]:
        """生成 Vega-Lite 四维健康雷达/柱状图规格配置。"""
        data_values = [
            {"dimension": "使用度 (Usage)", "score": health_data.get("usage", 80.0)},
            {"dimension": "系统质量 (Quality)", "score": health_data.get("quality", 85.0)},
            {"dimension": "客情关系 (Relationship)", "score": health_data.get("relationship", 75.0)},
            {"dimension": "商业健康 (Commercial)", "score": health_data.get("commercial", 70.0)},
        ]
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "客户四维健康度评分分布",
            "data": {"values": data_values},
            "mark": {"type": "bar", "cornerRadius": 4},
            "encoding": {
                "x": {"field": "dimension", "type": "nominal", "axis": {"title": "健康维度"}},
                "y": {"field": "score", "type": "quantitative", "scale": {"domain": [0, 100]}, "axis": {"title": "得分"}},
                "color": {
                    "field": "score",
                    "type": "quantitative",
                    "scale": {"scheme": "greens"},
                    "legend": None,
                },
            },
        }

    def export_bundle(
        self, run_id: str, client_data: Dict[str, Any], issues: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """批量导出伴生资产包。"""
        target_dir = os.path.join(self.export_dir, run_id)
        os.makedirs(target_dir, exist_ok=True)

        bundle_path = os.path.join(target_dir, "csm_bundle.json")
        sarif_path = os.path.join(target_dir, "csm_audit.sarif.json")
        vega_path = os.path.join(target_dir, "csm_health_chart.vega.json")

        bundle_payload = {
            "run_id": run_id,
            "exported_at": datetime.datetime.now().isoformat(),
            "agent": "r13-wakecheng-csm",
            "client_data": client_data,
            "manifest_version": "v11.0",
        }

        sarif_payload = self.generate_sarif(issues or [])
        health_breakdown = client_data.get("health_breakdown", {"usage": 80, "quality": 85, "relationship": 75, "commercial": 70})
        vega_payload = self.generate_vega_spec(health_breakdown)

        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_payload, f, ensure_ascii=False, indent=2)

        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif_payload, f, ensure_ascii=False, indent=2)

        with open(vega_path, "w", encoding="utf-8") as f:
            json.dump(vega_payload, f, ensure_ascii=False, indent=2)

        return {
            "status": "success",
            "run_id": run_id,
            "export_dir": target_dir,
            "bundle_path": bundle_path,
            "sarif_path": sarif_path,
            "vega_path": vega_path,
            "files": ["csm_bundle.json", "csm_audit.sarif.json", "csm_health_chart.vega.json"],
        }
