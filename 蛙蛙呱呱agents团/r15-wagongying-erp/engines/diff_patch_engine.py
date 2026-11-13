# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - [L08] 局部差量层：RFC 6902 JSON Patch 增量热修与守恒重算。

对标开源标杆：
- RFC 6902 (JavaScript Object Notation (JSON) Patch)
- diff-match-patch 局部增量热修模式 (Stars > 8k)

核心职责：
1. 比较旧与新供应链工件，生成标准 RFC 6902 Patch 数组 (add, replace, remove)；
2. 执行无损局部 Patch 热修应用 (apply_patch)；
3. 微调局部数量或单价后，触发增量勾稽平衡与预计量守恒重算；
4. 杜绝因微调单行导致全量重算或历史未改动满意部分被冲掉。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class ERPDiffPatchEngine:
    """RFC 6902 标准供应链局部差量热修引擎。"""

    def __init__(self):
        pass

    def create_patch(self, old_doc: Dict[str, Any], new_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """计算两个字典间的 RFC 6902 补丁列表。"""
        patch_ops: List[Dict[str, Any]] = []

        # 检查 replace / add
        for key, new_val in new_doc.items():
            path = f"/{key}"
            if key not in old_doc:
                patch_ops.append({"op": "add", "path": path, "value": new_val})
            elif old_doc[key] != new_val:
                patch_ops.append({"op": "replace", "path": path, "value": new_val})

        # 检查 remove
        for key in old_doc:
            if key not in new_doc:
                patch_ops.append({"op": "remove", "path": f"/{key}"})

        return patch_ops

    def apply_patch(self, target_doc: Dict[str, Any], patch_ops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用 RFC 6902 补丁并无损更新目标对象。"""
        res = copy.deepcopy(target_doc)

        for op in patch_ops:
            op_type = op.get("op")
            raw_path = op.get("path", "")
            key = raw_path.lstrip("/")

            if op_type == "add" or op_type == "replace":
                res[key] = op.get("value")
            elif op_type == "remove":
                if key in res:
                    del res[key]

        # 局部热修后触发增量预计量守恒重算
        if any(k in res for k in ("actual_qty", "ordered_qty", "planned_qty", "reserved_qty")):
            actual = float(res.get("actual_qty", 0.0))
            ordered = float(res.get("ordered_qty", 0.0))
            planned = float(res.get("planned_qty", 0.0))
            reserved = float(res.get("reserved_qty", 0.0))
            res["projected_available"] = round(actual + ordered + planned - reserved, 4)

        return res

    def patch_line_item(
        self,
        order: Dict[str, Any],
        line_idx: int,
        field: str,
        new_val: Any,
    ) -> Dict[str, Any]:
        """对采购单/销售单的单行明细实施局部精准热修，并重算总额。"""
        updated = copy.deepcopy(order)
        items = updated.get("items", [])
        if 0 <= line_idx < len(items):
            items[line_idx][field] = new_val
            # 重新计算该行 line_total
            price = float(items[line_idx].get("price", items[line_idx].get("rate", 0.0)))
            qty = float(items[line_idx].get("quantity", items[line_idx].get("qty", 1.0)))
            items[line_idx]["amount"] = round(price * qty, 2)

            # 重新计算总额
            subtotal = sum(float(it.get("amount", float(it.get("price", 0.0)) * float(it.get("qty", 1.0)))) for it in items)
            updated["total_amount"] = round(subtotal, 2)
            updated["subtotal"] = round(subtotal, 2)

        return updated
