# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - L08 局部差量层 (RFC 6902 Growth Differential Patch).

对标标杆: RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)
核心功能:
1. 生成策略/实验参数快照之间的 RFC 6902 标准 JSON Patch 差量补丁序列
2. 策略参数条目级差量热修无损置换，避免策略全量回滚或重生成
3. 支持策略切片增量微调与关键指标（如预算、目标出价、K-Factor 假设）差量重算
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class GrowthDiffPatchEngine:
    """增长运营策略与参数 RFC 6902 局部差量补丁与热修引擎。"""

    def create_patch(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """依据 RFC 6902 规范生成标准 JSON Patch 差量操作序列。"""
        patches: List[Dict[str, Any]] = []

        # 检查修改与新增
        for k, v in new_state.items():
            if k not in old_state:
                patches.append({"op": "add", "path": f"/{k}", "value": v})
            elif old_state[k] != v:
                patches.append({
                    "op": "replace",
                    "path": f"/{k}",
                    "value": v,
                    "prev_value": old_state[k],
                })

        # 检查删除
        for k in old_state:
            if k not in new_state:
                patches.append({"op": "remove", "path": f"/{k}"})

        return patches

    def apply_patch(self, target: Dict[str, Any], patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将 JSON Patch 规范补丁应用到目标策略对象上，完成无损置换。"""
        res = copy.deepcopy(target)
        for p in patches:
            op = p.get("op")
            path = p.get("path", "").lstrip("/")
            if not path:
                continue

            # 支持浅层与单级嵌套路径解析 (如 /budget/daily)
            parts = path.split("/")
            if len(parts) == 1:
                key = parts[0]
                if op in ("add", "replace"):
                    res[key] = p.get("value")
                elif op == "remove" and key in res:
                    del res[key]
            elif len(parts) == 2:
                parent, child = parts[0], parts[1]
                if op in ("add", "replace"):
                    if parent not in res or not isinstance(res[parent], dict):
                        res[parent] = {}
                    res[parent][child] = p.get("value")
                elif op == "remove" and parent in res and isinstance(res[parent], dict) and child in res[parent]:
                    del res[parent][child]

        return res

    def patch_strategy_item(self, full_strategy: Dict[str, Any], key_path: str, new_value: Any) -> Dict[str, Any]:
        """条目级差量热修无损置换：直接热修指定策略项，保持其余参数不变。"""
        patch = [{"op": "replace", "path": f"/{key_path}", "value": new_value}]
        return self.apply_patch(full_strategy, patch)

    def recalculate_differential(
        self,
        base_budget: float,
        target_cac: float,
        updated_budget: float,
        updated_cac: float,
    ) -> Dict[str, Any]:
        """差量重算：参数热修后，增量计算目标获客规模、预算差额与 ROI 弹性变化。"""
        base_acquisitions = int(base_budget / target_cac) if target_cac > 0 else 0
        new_acquisitions = int(updated_budget / updated_cac) if updated_cac > 0 else 0
        delta_acquisitions = new_acquisitions - base_acquisitions
        delta_budget = round(updated_budget - base_budget, 2)

        return {
            "base_acquisitions": base_acquisitions,
            "new_acquisitions": new_acquisitions,
            "delta_acquisitions": delta_acquisitions,
            "delta_budget": delta_budget,
            "differential_applied": True,
        }
