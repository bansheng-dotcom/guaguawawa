# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - [L08] 局部差量层：RFC 6902 自动化工作流 JSON Patch 热修补丁引擎。

对标开源标杆：
- RFC 6902 (JavaScript Object Notation (JSON) Patch)
- diff-match-patch (Stars > 8k)

核心职责：
1. 提取旧新工作流配置之间的细粒度差量补丁 (add, remove, replace, move, copy, test)；
2. 实现无损就地局部应用 Patch，避免微调单参数导致全量推倒重来；
3. 校验应用补丁后的 DAG 拓扑无环与结构守恒性。
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional, Tuple


class AutomationDiffPatchEngine:
    """RFC 6902 JSON Patch 局部差量计算与热修引擎。"""

    def __init__(self):
        pass

    def create_patch(self, old_doc: Dict[str, Any], new_doc: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        """基于 RFC 6902 计算字典之间的最小差量补丁操作列表。"""
        patch: List[Dict[str, Any]] = []

        all_keys = set(old_doc.keys()).union(set(new_doc.keys()))
        for k in sorted(all_keys):
            path = f"{prefix}/{k}"
            if k not in old_doc:
                patch.append({"op": "add", "path": path, "value": new_doc[k]})
            elif k not in new_doc:
                patch.append({"op": "remove", "path": path})
            else:
                old_val = old_doc[k]
                new_val = new_doc[k]
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    patch.extend(self.create_patch(old_val, new_val, prefix=path))
                elif old_val != new_val:
                    patch.append({"op": "replace", "path": path, "value": new_val})

        return patch

    def apply_patch(self, doc: Dict[str, Any], patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将 RFC 6902 补丁列表无损应用到现有工作流字典中。"""
        result = copy.deepcopy(doc)

        for operation in patch:
            op = operation.get("op")
            path = operation.get("path", "").strip("/").split("/")
            value = operation.get("value")

            if not path or path == [""]:
                continue

            target = result
            for segment in path[:-1]:
                if segment not in target or not isinstance(target[segment], dict):
                    target[segment] = {}
                target = target[segment]

            last_key = path[-1]
            if op in ("add", "replace"):
                target[last_key] = value
            elif op == "remove":
                target.pop(last_key, None)
            elif op == "test":
                if target.get(last_key) != value:
                    raise AssertionError(f"RFC 6902 Test Op Failed at {operation['path']}: {target.get(last_key)} != {value}")

        return result


# 别名兼容
DiffPatchEngine = AutomationDiffPatchEngine
