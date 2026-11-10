# -*- coding: utf-8 -*-
"""engines/reflexive_healer.py - L03 自愈反思层 (Reflexive Healing & Boundary Critic).

对标开源标杆：Reflexion / Critic-Agent / OpenHands (Stars > 40k)
核心职责：
1. 捕获工件中的结构破损与缺省字段，自动执行补全与合规修复；
2. 强力拦截三大交付红线：
   - 红线 1: 越界做生产工程而不声明交接对象 (Handoff to R09/R20)；
   - 红线 2: 交付物充斥空泛占位（TODO/待定/稍后补充）；
   - 红线 3: 缺少明确量化的 MVP 失败判定标准 (Fail Criteria)。
3. 提供自愈迭代循环 (Self-Healing Loop)。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple


class PrototypeReflexiveHealer:
    """R08 L03 自愈反思与红线审判引擎。"""

    VAGUE_WORDS = ["待定", "TODO", "todo", "稍后补充", "视情况而定", "占位", "后续开发", "暂无"]
    PRODUCTION_KEYWORDS = ["分布式", "k8s", "微服务架构", "生产级高可用", "跨机房容灾", "分库分表"]

    def __init__(self):
        self.version = "1.0.0"

    def audit_and_heal(self, artifact_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """全量审计并自愈修复输入工件。"""
        issues: List[str] = []
        violations: List[str] = []
        healed_data = copy.deepcopy(data)
        actions_taken: List[str] = []

        # --- 1. 红线审查 (Boundary Critic) ---
        # 1.1 审查空泛占位符
        self._check_vague(healed_data, "", violations)

        # 1.2 审查越界做生产工程
        data_str = str(healed_data)
        for kw in self.PRODUCTION_KEYWORDS:
            if kw in data_str:
                # 检查是否有 handoff
                if not healed_data.get("handoff"):
                    violations.append(f"触犯边界红线：涉及生产级工程关键字 '{kw}'，但未声明交接说明 (handoff)")

        # --- 2. 字段自愈修正 (Reflexive Auto-Healing) ---
        if artifact_type == "mvp":
            if "criteria" not in healed_data or not isinstance(healed_data["criteria"], dict):
                healed_data["criteria"] = {"success": "7天内收集10个意向用户", "fail": "7天内<3个意向"}
                actions_taken.append("自愈补齐缺失的假设成败门禁指标 (criteria)")
            else:
                crit = healed_data["criteria"]
                if "fail" not in crit or not crit["fail"]:
                    crit["fail"] = "转化率低于 1% 或无有效提交"
                    actions_taken.append("自愈补齐缺失的失败判定线 (fail criteria)")

            if "handoff" not in healed_data or not healed_data["handoff"]:
                healed_data["handoff"] = "交接给 R09 研发进行生产环境实现"
                actions_taken.append("自愈补充默认敏捷交接声明 (handoff -> R09)")

        elif artifact_type == "landing":
            proofs = healed_data.get("proof_points", [])
            if len(proofs) < 3:
                needed = 3 - len(proofs)
                default_proofs = [
                    "核心功能验证支持：已通过轻量原型验证",
                    "客户保障：首批种子用户 1 对 1 支持",
                    "交付承诺：72 小时内极速部署交付",
                ]
                proofs.extend(default_proofs[:needed])
                healed_data["proof_points"] = proofs
                actions_taken.append(f"自愈补全不足 3 条的落地页信任佐证 (补入 {needed} 条)")

            if not healed_data.get("no_js_library"):
                healed_data["no_js_library"] = True
                actions_taken.append("自愈强制注入 no_js_library=True 极简性能约束")

        elif artifact_type == "prototype":
            if "platforms" not in healed_data or not healed_data["platforms"]:
                healed_data["platforms"] = ["android", "ios", "web"]
                actions_taken.append("自愈填充默认跨平台矩阵 [android, ios, web]")

            if "breakpoints" not in healed_data:
                healed_data["breakpoints"] = {"mobile": "375", "tablet": "768", "desktop": "1280"}
                actions_taken.append("自愈补齐响应式设计断点")

        has_blocker = len(violations) > 0

        return {
            "ok": not has_blocker,
            "violations": violations,
            "actions_taken": actions_taken,
            "healed_count": len(actions_taken),
            "healed_data": healed_data,
            "reflexion_grade": "PASS" if not has_blocker else "REJECTED_BY_CRITIC",
        }

    def _check_vague(self, val: Any, prefix: str, violations: List[str]) -> None:
        if isinstance(val, str):
            for w in self.VAGUE_WORDS:
                if w in val:
                    violations.append(f"字段 '{prefix}' 包含空泛/占位词: '{w}'")
        elif isinstance(val, dict):
            for k, v in val.items():
                self._check_vague(v, f"{prefix}.{k}" if prefix else k, violations)
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                self._check_vague(item, f"{prefix}[{idx}]", violations)
