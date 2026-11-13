# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - [L08] 局部差量层：RFC 6902 客户成功差量补丁与热修引擎。

对标开源标杆：
- RFC 6902 (JavaScript Object Notation (JSON) Patch)
- diff-match-patch 文本与树结构差量同步 (Stars > 8k)

核心职责：
1. 对比前后两份客户画像、健康参数或续约策略，生成 RFC 6902 标准 JSON Patch 补丁流；
2. 实现原子级差量热修应用 (Apply Patch)，避免全量重写破坏已有稳定配置；
3. 计算局部修改引起的分值增量 (Incremental Delta Scoring)。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple


class CsmDiffPatchEngine:
    """RFC 6902 客户成功差量补丁与无损增量热修引擎。"""

    def __init__(self):
        pass

    def create_patch(self, old_obj: Dict[str, Any], new_obj: Dict[str, Any], path_prefix: str = "") -> List[Dict[str, Any]]:
        """递归比较前后字典，生成 RFC 6902 标准 Patch 列表。"""
        patch: List[Dict[str, Any]] = []

        # 检查删除或修改
        for k, old_val in old_obj.items():
            current_path = f"{path_prefix}/{k}"
            if k not in new_obj:
                patch.append({"op": "remove", "path": current_path})
            else:
                new_val = new_obj[k]
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    patch.extend(self.create_patch(old_val, new_val, current_path))
                elif old_val != new_val:
                    patch.append({"op": "replace", "path": current_path, "value": copy.deepcopy(new_val)})

        # 检查新增
        for k, new_val in new_obj.items():
            current_path = f"{path_prefix}/{k}"
            if k not in old_obj:
                patch.append({"op": "add", "path": current_path, "value": copy.deepcopy(new_val)})

        return patch

    def apply_patch(self, target: Dict[str, Any], patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将 RFC 6902 补丁序列应用到目标字典上。"""
        result = copy.deepcopy(target)

        for op_item in patch:
            op = op_item.get("op")
            path = op_item.get("path", "").strip("/").split("/")
            if not path or path == [""]:
                continue

            curr = result
            for part in path[:-1]:
                if part not in curr or not isinstance(curr[part], dict):
                    curr[part] = {}
                curr = curr[part]

            leaf = path[-1]
            if op == "add" or op == "replace":
                curr[leaf] = copy.deepcopy(op_item.get("value"))
            elif op == "remove":
                if leaf in curr:
                    del curr[leaf]

        return result

    def calculate_health_delta(
        self, old_health: Dict[str, float], patch: List[Dict[str, Any]], weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """计算补丁对综合健康分造成的差量影响。"""
        new_health = self.apply_patch(old_health, patch)

        total_w = sum(weights.values()) or 100.0
        old_score = sum(old_health.get(k, 0.0) * (weights.get(k, 0.0) / total_w) for k in weights)
        new_score = sum(new_health.get(k, 0.0) * (weights.get(k, 0.0) / total_w) for k in weights)

        delta = round(new_score - old_score, 2)
        return {
            "old_score": round(old_score, 2),
            "new_score": round(new_score, 2),
            "delta": delta,
            "direction": "IMPROVED" if delta > 0 else ("DEGRADED" if delta < 0 else "UNCHANGED"),
        }
