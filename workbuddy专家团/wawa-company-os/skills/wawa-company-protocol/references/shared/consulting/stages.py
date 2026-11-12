# -*- coding: utf-8 -*-
"""咨询 8 阶段定义：阶段、角色、必填产物、双门禁。"""
from __future__ import annotations

STAGES = [
    {
        "id": 1, "name": "定义问题", "owner": "r01", "participants": ["r05"],
        "artifacts": ["decision", "decision_maker", "success_metric", "scope_out"],
        "reviewer": "r01",
        "gate": "partner 确认问题定义",
    },
    {
        "id": 2, "name": "逻辑地图", "owner": "r05", "participants": ["r01", "r06"],
        "artifacts": ["branches", "critical_branch"],
        "reviewer": "r01",
        "gate": "分支 MECE、每条有假设、标出 critical branch",
    },
    {
        "id": 3, "name": "80/20 聚焦", "owner": "r01", "participants": ["r05"],
        "artifacts": ["focus", "excluded_reasons"],
        "reviewer": "r01",
        "gate": "聚焦 ≤3 支、写明其余为什么不做",
    },
    {
        "id": 4, "name": "分析计划", "owner": "r05", "participants": ["r06", "r03"],
        "artifacts": ["workstreams"],
        "reviewer": "r01",
        "gate": "每条工作流有数据源/方法/负责人/降级",
    },
    {
        "id": 5, "name": "执行分析", "owner": "r06", "participants": ["r03", "r15"],
        "artifacts": ["findings", "conflicts", "gaps"],
        "reviewer": "r04",
        "gate": "发现四件套、冲突单列、缺口可补",
    },
    {
        "id": 6, "name": "整合答案", "owner": "r05", "participants": ["r01"],
        "artifacts": ["messages"],
        "reviewer": "r01",
        "gate": "1—3 条信息、机制 + 竞争解释",
    },
    {
        "id": 7, "name": "形成建议", "owner": "r01", "participants": ["r03", "r02"],
        "artifacts": ["options", "recommendation"],
        "reviewer": "r03",
        "gate": "≥3 选项、经济性/风险/KPI/回滚",
    },
    {
        "id": 8, "name": "打包交付", "owner": "r05", "participants": ["r04"],
        "artifacts": ["deliverables", "value_tracking"],
        "reviewer": "r04",
        "gate": "摘要/正文/附录/价值追踪齐全",
    },
]

STAGE_BY_ID = {s["id"]: s for s in STAGES}


def next_stage(current: int) -> int:
    return min(8, current + 1)


def stage_name(i: int) -> str:
    return STAGE_BY_ID.get(i, {}).get("name", f"阶段{i}")
