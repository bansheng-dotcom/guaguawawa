# -*- coding: utf-8 -*-
"""R03 伴生资产交付与机器可消费规格包 (L07 伴生消费层)。

对标高星标杆: Onlook / Design-to-Code (AST 转换)
在输出人类可读的深度分析报告 (Markdown/HTML) 时，同时伴生导出标准化的机器 JSON 资产，
供前端图表引擎 (Vega/ECharts) 或下游业务系统 (ERP/CRM) 无缝调用。
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict

class FinancialAssetBundle:
    """财务合规伴生资产交付包生成器。"""

    @classmethod
    def bundle(cls, out_dir: str, spec_name: str, data: Dict[str, Any]) -> Dict[str, str]:
        """将数据资产导出为 JSON 规格包及其他辅助格式。"""
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # 1. 导出主规格文件 (Financial AST)
        ast_path = os.path.join(out_dir, f"{spec_name}.json")
        with open(ast_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 2. 导出标准的 Vega-Lite 配置 (图表描述符)
        vega_path = os.path.join(out_dir, f"{spec_name}_chart.json")
        vega_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "CFO 财务自动图表",
            "data": {"values": data.get("chart_data", [])},
            "mark": "bar",
            "encoding": {
                "x": {"field": "label", "type": "nominal"},
                "y": {"field": "value", "type": "quantitative"}
            }
        }
        with open(vega_path, "w", encoding="utf-8") as f:
            json.dump(vega_spec, f, indent=2, ensure_ascii=False)

        return {"ast": ast_path, "vega": vega_path}
