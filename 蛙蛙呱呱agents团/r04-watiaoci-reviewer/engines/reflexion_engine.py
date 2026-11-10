# -*- coding: utf-8 -*-
"""L03 自愈反思层：闭环反思自愈与红线阻断引擎。
对标开源项目：Reflexion (Stars > 5.5k), OpenHands (Stars > 38k)。
解决病灶：审查输入若字段缺失、别名不一致或判据缺状态时直接抛出异常崩溃；缺少对“评审自己/替他人拍板”等核心红线的强阻断与自愈。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple


class ReflexionSelfHealingEngine:
    """闭环反思自愈与红线卫士。"""

    # 字段别名映射字典（自愈常见变体）
    FIELD_ALIASES = {
        "id": ["item_id", "task_id", "rule_id", "key", "name"],
        "status": ["state", "verdict", "result", "judge"],
        "source": ["origin", "src", "file", "location", "path"],
        "content": ["text", "desc", "description", "body", "claim"],
        "severity": ["level", "priority", "importance", "grade"],
    }

    # 红线阻断规则（绝对禁止的行为）
    RED_LINES = [
        ("self_review_forbidden", ["评审自己", "自身代码审查", "self-approval", "r04自评"], "绝对红线：R04禁止对自身代码或产物出具放行判据"),
        ("auto_fix_forbidden", ["替人修改", "自动改代码", "auto_patch", "fix_source"], "绝对红线：R04只记录挑刺，严禁代替被审方直接修改源代码"),
        ("bypass_gate_forbidden", ["跳过门禁", "强制放行", "bypass_gate", "ignore_all_fail"], "绝对红线：严禁无视失败硬门禁强制放行"),
    ]

    @classmethod
    def audit_and_heal_payload(cls, raw_payload: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Dict[str, Any], List[str], List[str]]:
        """执行体检、红线检测及自愈修复。
        返回：(ok, healed_payload, reflections, redline_violations)
        """
        payload = copy.deepcopy(raw_payload)
        reflections: List[str] = []
        violations: List[str] = []

        # 1. 红线穿透审查
        raw_str = str(payload).lower()
        for red_id, triggers, reason in cls.RED_LINES:
            for trig in triggers:
                if trig in raw_str:
                    violations.append(f"[{red_id}] {reason}")
                    break

        if violations:
            # 触碰红线直接拒绝
            return False, payload, reflections, violations

        # 2. 字段自愈与反思
        for req in required_fields:
            if req not in payload or payload[req] is None or payload[req] == "":
                # 尝试从别名中寻找自愈候选
                healed = False
                aliases = cls.FIELD_ALIASES.get(req, [])
                for alias in aliases:
                    if alias in payload and payload[alias] not in (None, ""):
                        payload[req] = payload[alias]
                        reflections.append(f"自愈映射: 字段 '{req}' 缺失，已成功从别名字段 '{alias}' 提取自愈值。")
                        healed = True
                        break
                if not healed:
                    # 提供默认安全兜底
                    if req == "status":
                        payload[req] = "UNKNOWN"
                        reflections.append("自愈补齐: 状态字段 'status' 缺失，已安全回退为 'UNKNOWN'。")
                    elif req == "items":
                        payload[req] = []
                        reflections.append("自愈补齐: 列表字段 'items' 缺失，已安全初始化为空列表 []。")
                    elif req == "severity":
                        payload[req] = "medium"
                        reflections.append("自愈补齐: 严重性 'severity' 缺失，默认兜底为 'medium'。")

        return True, payload, reflections, violations
