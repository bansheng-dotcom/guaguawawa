# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - R10 视觉设计官 · L08 局部差量重绘与补丁层 (Diff Patch Engine).

对标 RFC 6902 (JSON Patch) 与 IOPaint (Stars > 23k)：
1. 属性级差量补丁：对设计规格字典、图层树进行 RFC 6902 差量 Patch 计算与无损局部应用；
2. 图像级语义遮罩局部重绘：联动 InpaintEditEngine，通过语义遮罩保护未变更像素，仅对局部（如背景、主体、边框）进行无损改稿。
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

from engines.inpaint import InpaintEditEngine


class VisualDiffPatchEngine:
    """L08 视觉规格与图像差量补丁引擎。"""

    def create_patch(self, src: Dict[str, Any], dst: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """计算两份设计规格之间的 RFC 6902 JSON Patch 差量补丁。"""
        patch: List[Dict[str, Any]] = []

        # 检查修改与删除
        for k, v in src.items():
            curr_path = f"{path}/{k}"
            if k not in dst:
                patch.append({"op": "remove", "path": curr_path})
            elif isinstance(v, dict) and isinstance(dst[k], dict):
                patch.extend(self.create_patch(v, dst[k], curr_path))
            elif v != dst[k]:
                patch.append({"op": "replace", "path": curr_path, "value": dst[k]})

        # 检查新增
        for k, v in dst.items():
            curr_path = f"{path}/{k}"
            if k not in src:
                patch.append({"op": "add", "path": curr_path, "value": v})

        return patch

    def apply_patch(self, doc: Dict[str, Any], patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用 RFC 6902 补丁到目标设计规格上。"""
        result = copy.deepcopy(doc)

        for op in patch:
            path_parts = [p for p in op.get("path", "").split("/") if p]
            if not path_parts:
                continue

            # 遍历到父级
            curr = result
            for p in path_parts[:-1]:
                if p not in curr or not isinstance(curr[p], dict):
                    curr[p] = {}
                curr = curr[p]

            last_key = path_parts[-1]
            operation = op.get("op")

            if operation in ["add", "replace"]:
                curr[last_key] = op.get("value")
            elif operation == "remove":
                if last_key in curr:
                    del curr[last_key]

        return result

    def incremental_edit_image(
        self,
        image_path: str,
        instruction: str,
        output_dir: str,
        target_region: str = "background",
        preferred_engine: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行语义级局部遮罩图像增量重绘。"""
        return InpaintEditEngine.edit_image(
            image_path=image_path,
            instruction=instruction,
            output_dir=output_dir,
            target_region=target_region,
            preferred_engine=preferred_engine
        )
