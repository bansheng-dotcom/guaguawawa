# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - [L07] 伴生消费层：下游机器消费资产包与 SARIF/Vega-Lite 伴随导出。

对标开源标杆：
- OASIS SARIF v2.1.0 (Static Analysis Results Interchange Format 国际工业标准)
- Vega-Lite 声明式可视化图表规范 (Stars > 11k)
- MES/WMS 下游系统自动化消费标准资产包 (Asset Bundle)

核心职责：
1. 伴生导出结构化 erp_bundle.json（包含物料清单、库存台账、预计量守恒与审计状态）；
2. 伴生导出符合 OASIS SARIF v2.1.0 国际标准的静态审查报告 erp_audit.sarif.json；
3. 伴生导出前端与看板可直接渲染的 Vega-Lite 柱状/折线图配置 erp_inventory_chart.vega.json；
4. 物理落盘至 workspace/bundles/<run_id>/，供下游系统无感接入。
"""
from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(_HERE, "workspace")
BUNDLE_DIR = os.path.join(_WS, "bundles")


class ERPAssetBundle:
    """ERP 与供应链伴生资产包编译器与 SARIF/Vega 导出器。"""

    def __init__(self, output_root: str = BUNDLE_DIR):
        self.output_root = output_root

    def export_sarif(self, run_id: str, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建 OASIS SARIF v2.1.0 标准审计报告。"""
        results = []
        for v in violations:
            results.append({
                "ruleId": v.get("gate", "GATE-UNKNOWN"),
                "level": "error" if v.get("severity") == "CRITICAL" else "warning",
                "message": {"text": v.get("msg", "供应链门禁合规性审查告警")},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": v.get("file", "ERP_SPEC.md")},
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
                        "name": "R15-SupplyChain-Auditor",
                        "semanticVersion": "12.0.0",
                        "informationUri": "https://github.com/wawa-guagua/r15-wagongying-erp",
                        "rules": [
                            {"id": "GATE-01", "shortDescription": {"text": "预计量守恒门禁"}},
                            {"id": "GATE-02", "shortDescription": {"text": "负库存刚性拦截门禁"}},
                            {"id": "GATE-03", "shortDescription": {"text": "采购超收容差门禁"}},
                            {"id": "GATE-04", "shortDescription": {"text": "BOM配方有效性门禁"}},
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

    def export_vega_chart(self, item_code: str, actual: float, ordered: float, planned: float, reserved: float, projected: float) -> Dict[str, Any]:
        """生成 Vega-Lite 声明式图表规范。"""
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": f"物料 {item_code} 库存四维预计量守恒图谱",
            "description": "actual + ordered + planned - reserved = projected_available",
            "data": {
                "values": [
                    {"category": "现存在库 (Actual)", "quantity": actual, "type": "asset"},
                    {"category": "采购在途 (Ordered)", "quantity": ordered, "type": "inflow"},
                    {"category": "生产计划 (Planned)", "quantity": planned, "type": "inflow"},
                    {"category": "销售锁定 (Reserved)", "quantity": -reserved, "type": "outflow"},
                    {"category": "预计可用 (Projected)", "quantity": projected, "type": "net_available"},
                ]
            },
            "mark": "bar",
            "encoding": {
                "x": {"field": "category", "type": "nominal", "axis": {"labelAngle": 0}},
                "y": {"field": "quantity", "type": "quantitative"},
                "color": {"field": "type", "type": "nominal"},
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
            "item_code": "ITEM_ERP_001",
            "actual_qty": 500.0,
            "ordered_qty": 200.0,
            "planned_qty": 100.0,
            "reserved_qty": 150.0,
            "projected_available": 650.0,
            "is_conserved": True,
        }

        # 1. 伴生导出 erp_bundle.json
        bundle_path = os.path.join(target_dir, "erp_bundle.json")
        bundle_content = {
            "schema_version": "v12.0",
            "run_id": run_id,
            "exported_at": datetime.datetime.now().isoformat(),
            "role": "r15-wagongying-erp",
            "payload": data,
        }
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_content, f, ensure_ascii=False, indent=2)

        # 2. 伴生导出 erp_audit.sarif.json
        sarif_path = os.path.join(target_dir, "erp_audit.sarif.json")
        sarif_doc = self.export_sarif(run_id, violations or [])
        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif_doc, f, ensure_ascii=False, indent=2)

        # 3. 伴生导出 erp_inventory_chart.vega.json
        vega_path = os.path.join(target_dir, "erp_inventory_chart.vega.json")
        vega_doc = self.export_vega_chart(
            item_code=data.get("item_code", "ITEM_DEMO"),
            actual=float(data.get("actual_qty", 500)),
            ordered=float(data.get("ordered_qty", 200)),
            planned=float(data.get("planned_qty", 100)),
            reserved=float(data.get("reserved_qty", 150)),
            projected=float(data.get("projected_available", 650)),
        )
        with open(vega_path, "w", encoding="utf-8") as f:
            json.dump(vega_doc, f, ensure_ascii=False, indent=2)

        return {
            "bundle_file": bundle_path,
            "sarif_file": sarif_path,
            "vega_file": vega_path,
            "dir": target_dir,
        }
