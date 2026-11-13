# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - [L07] 伴生消费层：下游机器可消费资产包与 SARIF/Vega 规范导出引擎。

对标开源标杆：
- OASIS SARIF v2.1.0 (Static Analysis Results Interchange Format)
- Vega-Lite 声明式可视化图表规范 (Stars > 12k)

核心职责：
1. 伴生导出下游 ERP/对账/财务系统直接消费的结构化资产包 `commerce_bundle.json`；
2. 导出符合国际标准 OASIS SARIF v2.1.0 规范的交易与履约审计报告 `commerce_audit.sarif.json`；
3. 导出前端与 BI 可直接渲染的 Vega-Lite 收入流水图表元数据 `commerce_chart.vega.json`。
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


class CommerceAssetBundle:
    """交易伴生资产包导出与标准化格式转换引擎。"""

    def __init__(self, export_dir: str = DEFAULT_BUNDLE_DIR):
        self.export_dir = export_dir

    def generate_sarif(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成符合 OASIS SARIF v2.1.0 标准的静态质检审计报告。"""
        results = []
        rules = [
            {
                "id": "COMM001",
                "name": "IdempotencyMissing",
                "shortDescription": {"text": "缺失交易幂等键 (GATE-01)"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "COMM002",
                "name": "BalanceImbalance",
                "shortDescription": {"text": "财务勾稽平衡破损 (GATE-02)"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "COMM003",
                "name": "RefundRatioExceeded",
                "shortDescription": {"text": "退款比例超过上限 (GATE-06)"},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "COMM004",
                "name": "NegativeUsageDetected",
                "shortDescription": {"text": "计量用量出现非法负数 (GATE-07)"},
                "defaultConfiguration": {"level": "error"},
            },
        ]

        for issue in issues:
            results.append({
                "ruleId": issue.get("rule_id", "COMM002"),
                "level": issue.get("level", "error"),
                "message": {"text": issue.get("message", "交易门禁检查未通过")},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.get("target", "order_payload")},
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
                        "name": "R14-Commerce-Audit",
                        "semanticVersion": "12.0.0",
                        "informationUri": "https://github.com/wawa-guagua/r14-wajiaoyi-commerce",
                        "rules": rules,
                    }
                },
                "results": results,
            }],
        }

    def generate_vega_spec(self, series: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """生成 Vega-Lite 交易流水与结算漏斗图表规范。"""
        data = series or [
            {"stage": "创建订单", "amount": 100000.0},
            {"stage": "合同签署", "amount": 95000.0},
            {"stage": "发起支付", "amount": 92000.0},
            {"stage": "支付成功", "amount": 90000.0},
            {"stage": "履约交付", "amount": 89500.0},
        ]
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "R14 交易与履约结算漏斗图",
            "data": {"values": data},
            "mark": {"type": "bar", "cornerRadius": 4, "color": "#0d9488"},
            "encoding": {
                "x": {"field": "stage", "type": "nominal", "title": "交易履约环节", "sort": None},
                "y": {"field": "amount", "type": "quantitative", "title": "累计交易流水 (CNY)"},
                "tooltip": [
                    {"field": "stage", "type": "nominal"},
                    {"field": "amount", "type": "quantitative"},
                ],
            },
        }

    def export_bundle(
        self,
        run_id: str,
        order_meta: Dict[str, Any],
        audit_issues: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """导出全套标准化伴生资产包并落盘。"""
        os.makedirs(self.export_dir, exist_ok=True)
        now_iso = datetime.datetime.now().isoformat()

        bundle_payload = {
            "run_id": run_id,
            "agent": "r14-wajiaoyi-commerce",
            "exported_at": now_iso,
            "order_meta": order_meta,
            "status": "COMPLETED",
        }
        sarif_payload = self.generate_sarif(audit_issues or [])
        vega_payload = self.generate_vega_spec()

        bundle_path = os.path.join(self.export_dir, f"{run_id}_commerce_bundle.json")
        sarif_path = os.path.join(self.export_dir, f"{run_id}_commerce_audit.sarif.json")
        vega_path = os.path.join(self.export_dir, f"{run_id}_commerce_chart.vega.json")

        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_payload, f, ensure_ascii=False, indent=2)

        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif_payload, f, ensure_ascii=False, indent=2)

        with open(vega_path, "w", encoding="utf-8") as f:
            json.dump(vega_payload, f, ensure_ascii=False, indent=2)

        return {
            "bundle": bundle_path,
            "sarif": sarif_path,
            "vega": vega_path,
        }
