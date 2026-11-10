# -*- coding: utf-8 -*-
"""L08 局部差量层：RFC 6902 JSON Patch 与战略假设差量微调器。

对标标杆:
- RFC 6902 (JSON Patch) / Sanster/IOPaint (23k⭐) / diff-match-patch (3k⭐)
支持针对战略假设的局部参数差量调整（如单改客单价、微调渗透率），
绝不推倒全量重写，确保未修改参数与证据树绝对稳定。
"""
from __future__ import annotations
import copy
from typing import Any, Dict, List, Tuple


class ResearchPatchEditor:
    """战略假设局部差量微调器。"""

    def apply_patch(self, base_doc: Dict[str, Any], patch_operations: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
        """执行 RFC 6902 风格的差量补丁操作。

        每个操作形如: {"op": "replace"|"add"|"remove", "path": "/pricing/unit_price", "value": 1500}
        """
        doc = copy.deepcopy(base_doc)
        applied = []

        for op in patch_operations:
            action = op.get("op")
            path = op.get("path", "")
            val = op.get("value")

            parts = [p for p in path.strip("/").split("/") if p]
            if not parts:
                continue

            curr = doc
            for p in parts[:-1]:
                if p not in curr or not isinstance(curr[p], dict):
                    curr[p] = {}
                curr = curr[p]

            last_key = parts[-1]
            if action in ("replace", "add"):
                curr[last_key] = val
                applied.append(f"{action.upper()} {path} -> {val}")
            elif action == "remove":
                if last_key in curr:
                    del curr[last_key]
                    applied.append(f"REMOVE {path}")

        return doc, applied

    def patch_by_instruction(self, base_doc: Dict[str, Any], instruction: str) -> Tuple[Dict[str, Any], List[str]]:
        """根据自然语言差量指令解析并应用微调。"""
        import re
        ops = []
        # 例如: "把客单价改成 1500"
        m_price = re.search(r"(?:客单价|单价|price).*?(\d+(?:\.\d+)?)", instruction)
        if m_price:
            ops.append({"op": "replace", "path": "/pricing/unit_price", "value": float(m_price.group(1))})

        # 例如: "把获客份额改成 0.12"
        m_share = re.search(r"(?:份额|渗透率|share).*?([\d\.]+)", instruction)
        if m_share:
            ops.append({"op": "replace", "path": "/sizing/obtainable_share", "value": float(m_share.group(1))})

        if not ops:
            return base_doc, ["无识别到的差量调整项"]

        return self.apply_patch(base_doc, ops)
