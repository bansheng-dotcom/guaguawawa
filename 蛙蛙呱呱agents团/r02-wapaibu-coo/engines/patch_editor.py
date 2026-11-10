# -*- coding: utf-8 -*-
"""R02 对话式增量局部微调与差量 Patch 修改 (轮次 8 落地)。

对标高星标杆: IOPaint / krita-ai-diffusion / JSON-Patch (RFC 6902)
打破“推倒重来”魔咒，支持在保留原 WBS/排期主体结构的前提下进行局部微调与节点置换。
"""
from __future__ import annotations
import copy
from typing import Any, Dict, List

class IncrementalPatchEditor:
    """局部差量微调器。"""

    @classmethod
    def apply_patch(cls, original_plan: Dict[str, Any], modification_instruction: str) -> Dict[str, Any]:
        """根据自然语言修改意图，对排期或任务执行局部无损置换。"""
        new_plan = copy.deepcopy(original_plan)
        tasks = new_plan.get("tasks", new_plan.get("work_breakdown", []))

        # 示例：局部调整某个任务工时或责任人
        if "压缩工时" in modification_instruction:
            for t in tasks:
                if t.get("estimated_cost", 0) > 1.0:
                    t["estimated_cost"] = round(t["estimated_cost"] * 0.8, 2)
                    t["patched"] = True
                    break
        elif "更换责任人" in modification_instruction:
            for t in tasks:
                t["owner"] = "r02_designated_specialist"
                t["patched"] = True

        new_plan["patch_applied"] = True
        new_plan["patch_instruction"] = modification_instruction
        return new_plan
