# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 增量局部微调与差量 Patch 编辑器 (Executive Patch Editor)。

对标 GitHub 开源标杆:
- RFC 6902 (JSON Patch) / IOPaint (23k+ stars) / krita-ai-diffusion
- 针对复杂决策卡或治理策略，支持基于自然语言指令实施局部差量修改，100% 保持未变更字段结构。
"""
from __future__ import annotations
import copy
import re
from typing import Any, Dict, List, Tuple

class ExecutivePatchEditor:
    """CEO 增量差量微调器。"""

    @classmethod
    def apply_patch(cls, original_card: Dict[str, Any], patch_instruction: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """依据自然语言或差量指令修改决策卡，保持其他结构不破损。"""
        patched_card = copy.deepcopy(original_card)
        operations = []

        # 指令 1：修改责任人 / DRI
        owner_match = re.search(r"(?:责任人|owner|由|交由)\s*(?:改为|换成|指派给)?\s*([a-zA-Z0-9_-]+)", patch_instruction, re.IGNORECASE)
        if owner_match:
            new_owner = owner_match.group(1).lower()
            old_owner = patched_card.get("owner", "r01")
            patched_card["owner"] = new_owner
            operations.append({"op": "replace", "path": "/owner", "from": old_owner, "value": new_owner})

        # 指令 2：追加或更新杀死标准
        if "杀死标准" in patch_instruction or "kill" in patch_instruction.lower():
            kc_list = patched_card.setdefault("kill_criteria", [])
            new_rule = "增量补丁：连续7天业务漏斗转化下滑 >20% 强制回退"
            kc_list.append(new_rule)
            operations.append({"op": "add", "path": "/kill_criteria/-", "value": new_rule})

        # 指令 3：调整冷却天数
        freeze_match = re.search(r"冷却(?:期|天数)?\s*(?:改为|调整为)?\s*(\d+)\s*天?", patch_instruction)
        if freeze_match:
            new_days = int(freeze_match.group(1))
            old_days = patched_card.get("freeze_days", 30)
            patched_card["freeze_days"] = new_days
            operations.append({"op": "replace", "path": "/freeze_days", "from": old_days, "value": new_days})

        # 指令 4：调整可逆性与回滚
        if "改为不可逆" in patch_instruction:
            patched_card["reversibility"] = "不可逆"
            patched_card["rollback_cost_months"] = 6
            operations.append({"op": "replace", "path": "/reversibility", "value": "不可逆"})
        elif "改为可逆" in patch_instruction:
            patched_card["reversibility"] = "可逆"
            patched_card["rollback_cost_months"] = 1
            operations.append({"op": "replace", "path": "/reversibility", "value": "可逆"})

        return patched_card, operations
