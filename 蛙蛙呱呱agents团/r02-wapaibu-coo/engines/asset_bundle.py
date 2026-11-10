# -*- coding: utf-8 -*-
"""R02 结构化伴生资产规格包与端口输出打通 (轮次 7 落地)。

对标高星标杆: onlook / Figma-Context-MCP (Design-to-Code Asset Bundle)
在交付工件时，伴随结构化 AST / WBS 节点规格包 (operations_spec.json)，供下游研发/数据智能体直接消费。
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List

class OperationsAssetBundle:
    """伴生结构化规格包生成器。"""

    @classmethod
    def bundle(cls, task_id: str, plan_data: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
        os.makedirs(out_dir, exist_ok=True)
        spec = {
            "spec_version": "2.0.0",
            "task_id": task_id,
            "generator": "r02-wapaibu-coo",
            "schema_type": "operations_schedule_ast",
            "metadata": {
                "total_cost": plan_data.get("total_cost", 0.0),
                "item_count": plan_data.get("item_count", 0),
                "critical_path": plan_data.get("critpath", [])
            },
            "nodes": plan_data.get("tasks", plan_data.get("work_breakdown", []))
        }

        spec_file = os.path.join(out_dir, "operations_spec.json")
        with open(spec_file, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)

        return {
            "spec_file": spec_file,
            "spec_json": spec
        }
