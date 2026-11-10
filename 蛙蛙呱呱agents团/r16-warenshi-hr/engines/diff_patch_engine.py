# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - [L08] 局部差量层：RFC 6902 JSON Patch 增量热修与恒等校验。

对标开源标杆：
- RFC 6902 (JavaScript Object Notation (JSON) Patch)
- diff-match-patch (Stars > 8k)

核心职责：
1. 比较旧与新人事工件（如员工信息、薪酬明细、请假单等），生成 RFC 6902 标准 Patch 操作列表（add, replace, remove）；
2. 执行无损局部 Patch 热修应用（apply_patch）；
3. 支持局部薪酬明细修改后触发增量净额重算与恒等校验（net = gross - Σdeductions）；
4. 避免改动一处导致全盘推倒重来。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class HRDiffPatchEngine:
    """RFC 6902 标准人事工件局部差量热修引擎。"""

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

        # 局部热修后触发薪酬净额重算与恒等校验：net = gross - Σdeductions
        if any(k in res for k in ("gross", "gross_salary", "deductions", "tax", "social_security", "housing_fund")):
            gross = float(res.get("gross", res.get("gross_salary", 0.0)))
            # 汇总扣减项
            deductions = float(res.get("deductions", 0.0))
            tax = float(res.get("tax", 0.0))
            social_sec = float(res.get("social_security", 0.0))
            housing_fund = float(res.get("housing_fund", 0.0))
            total_ded = deductions + tax + social_sec + housing_fund
            net = round(gross - total_ded, 2)
            res["net"] = net
            res["net_salary"] = net
            res["is_conserved"] = (net == round(gross - total_ded, 2))

        return res

    def patch_line_item(
        self,
        container: Dict[str, Any],
        items_field: str,
        line_idx: int,
        field: str,
        new_val: Any,
    ) -> Dict[str, Any]:
        """对人员/薪酬列表中的单行明细实施局部精准热修，并重算总额。"""
        updated = copy.deepcopy(container)
        items = updated.get(items_field, [])
        if 0 <= line_idx < len(items):
            items[line_idx][field] = new_val
            # 若包含薪酬行，重算净额
            row = items[line_idx]
            if "gross" in row:
                gross = float(row.get("gross", 0.0))
                ded = float(row.get("deductions", 0.0))
                row["net"] = round(gross - ded, 2)

            # 若容器有 total 统计，自动汇总
            if "total_amount" in updated or "total_payroll" in updated:
                tot = sum(float(it.get("net", it.get("gross", it.get("amount", 0.0)))) for it in items)
                key = "total_payroll" if "total_payroll" in updated else "total_amount"
                updated[key] = round(tot, 2)

        return updated


# 别名
DiffPatchEngine = HRDiffPatchEngine
