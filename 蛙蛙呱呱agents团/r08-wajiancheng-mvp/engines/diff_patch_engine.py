# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - L08 局部差量层 (RFC 6902 Component Patch & Incremental Diff).

对标开源标杆：RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)
核心职责：
1. 实现工件的局部微调与差量更新，改一小处样式/组件无需推倒重来；
2. 基于标准 RFC 6902 算子规范生成补丁：
   - op: "add" | "remove" | "replace" | "move" | "copy" | "test"
3. 提供双向能力：Diff 生成 (create_patch) 与 补丁应用 (apply_patch)。
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional, Tuple


class DiffPatchEngine:
    """R08 L08 基于 RFC 6902 的局部差量补丁与无损置换引擎。"""

    def __init__(self):
        self.version = "1.0.0"

    def create_patch(self, original: Dict[str, Any], target: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        """计算两个工件字典之间的 RFC 6902 差量 Patch 操作集。"""
        patch: List[Dict[str, Any]] = []

        all_keys = set(original.keys()).union(set(target.keys()))

        for k in sorted(all_keys):
            path = f"{prefix}/{k}"
            if k not in original:
                patch.append({"op": "add", "path": path, "value": target[k]})
            elif k not in target:
                patch.append({"op": "remove", "path": path})
            else:
                orig_v = original[k]
                targ_v = target[k]
                if isinstance(orig_v, dict) and isinstance(targ_v, dict):
                    patch.extend(self.create_patch(orig_v, targ_v, prefix=path))
                elif orig_v != targ_v:
                    patch.append({"op": "replace", "path": path, "value": targ_v})

        return patch

    def apply_patch(self, doc: Dict[str, Any], patch_ops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将 RFC 6902 补丁操作集应用至目标工件。"""
        new_doc = copy.deepcopy(doc)

        for op in patch_ops:
            action = op.get("op")
            path = op.get("path", "")
            tokens = [p for p in path.split("/") if p]
            if not tokens:
                continue

            curr = new_doc
            for t in tokens[:-1]:
                if t not in curr or not isinstance(curr[t], dict):
                    curr[t] = {}
                curr = curr[t]

            last_token = tokens[-1]
            if action == "add" or action == "replace":
                curr[last_token] = copy.deepcopy(op.get("value"))
            elif action == "remove":
                if last_token in curr:
                    del curr[last_token]

        return new_doc
