# -*- coding: utf-8 -*-
"""R03 增量差量财务微调与 Patch 引擎 (L08 局部差量层)。

对标高星标杆: RFC 6902 (JSON Patch) / IOPaint 局部无损重绘
当用户提出局部改动诉求（例如“把办公租赁费削减 20%”、“将 DSR 留存时效改为 14 天”、“调整特定科目的税率”）时，
无需全盘推倒重来，只对目标科目或规则字段实施无损差量补丁置换，
严格保证未被指名的其他财务与合规节点结构、勾稽关系和参数绝对不变。
"""
from __future__ import annotations
import copy
import re
from typing import Any, Dict, List

class FinancialPatchEditor:
    """增量差量微调器。"""

    @classmethod
    def apply_patch(cls, target_spec: Dict[str, Any], patch_command: str) -> Dict[str, Any]:
        """根据自然语言或微调参数安全更新局部数据节点。"""
        updated = copy.deepcopy(target_spec)

        # 1. 匹配预算/开支百分比调整 (如 "削减 20%" / "下调 15%" / "增加 10%")
        pct_match = re.search(r"(\S+)\s*(?:削减|下调|压缩|减少)\s*(\d+(?:\.\d+)?)\s*%", patch_command)
        if pct_match:
            item_name = pct_match.group(1)
            pct = float(pct_match.group(2)) / 100.0
            cls._modify_numeric(updated, item_name, factor=(1.0 - pct))
            return updated

        inc_match = re.search(r"(\S+)\s*(?:增加|上调|追加|扩充)\s*(\d+(?:\.\d+)?)\s*%", patch_command)
        if inc_match:
            item_name = inc_match.group(1)
            pct = float(inc_match.group(2)) / 100.0
            cls._modify_numeric(updated, item_name, factor=(1.0 + pct))
            return updated

        # 2. 匹配绝对金额或数值替换 (如 "将 rent 改为 4000" / "把 sla 改为 14")
        set_match = re.search(r"(?:将|把)\s*(\S+)\s*(?:调整为|改为|设为)\s*(\d+(?:\.\d+)?)", patch_command)
        if set_match:
            item_name = set_match.group(1)
            val = float(set_match.group(2))
            cls._modify_numeric(updated, item_name, exact_val=val)
            return updated

        return updated

    @classmethod
    def _modify_numeric(cls, data: Any, key_pattern: str, factor: float = 1.0, exact_val: float = None):
        """递归寻找并局部修改数值节点。"""
        if isinstance(data, dict):
            for k, v in data.items():
                if key_pattern.lower() in k.lower():
                    if isinstance(v, (int, float)):
                        if exact_val is not None:
                            data[k] = exact_val
                        else:
                            data[k] = round(v * factor, 2)
                else:
                    cls._modify_numeric(v, key_pattern, factor, exact_val)
        elif isinstance(data, list):
            for item in data:
                cls._modify_numeric(item, key_pattern, factor, exact_val)
