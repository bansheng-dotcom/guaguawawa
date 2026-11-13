# -*- coding: utf-8 -*-
"""engines/intent_compiler.py - [L02] 意图解构层：人事运营 5 阶段 Kahn DAG 拓扑编译器。

对标开源标杆：
- DSPy 签名式自然语言意图编译 (Signature / Teleprompter)
- Ray DAG / Airflow Kahn 拓扑执行序与工时评估器 (Stars > 20k)

核心职责：
1. 将复杂自然语言人事需求解构为 5 阶段标准 Kahn 拓扑 DAG：
   - S1_SOURCING: HC需求审批与职位发布
   - S2_SCREENING_INTERVIEW: 简历初筛与面试流转
   - S3_OFFER_CONTRACT: Offer发放与劳动合同签约前置校验
   - S4_ONBOARD_ATTENDANCE: 入职建档、考勤班次与排班初始
   - S5_PAYROLL_ENROLLMENT: 薪酬制度定级与社保公积金建账
2. 提取人事核心实体（职位角色、HC招聘人数、紧急度、薪酬预算/月薪、是否需劳动合同签约等）；
3. 计算节点依赖、拓扑序检测（确保无环 Kahn Topological Sort）与工时预算评估（输出 hours 与 days）。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


class HRIntentCompiler:
    """人事复合意图解构与 Kahn DAG 拓扑编译器。"""

    # 5 阶段标准人事交付 DAG 骨架
    STANDARD_STAGES = [
        {
            "id": "S1_SOURCING",
            "name": "HC需求审批与职位发布",
            "base_hours": 2.0,
            "depends_on": [],
            "deliverable": "JobOpening & SourcingChannels",
        },
        {
            "id": "S2_SCREENING_INTERVIEW",
            "name": "简历初筛与面试流转",
            "base_hours": 4.0,
            "depends_on": ["S1_SOURCING"],
            "deliverable": "InterviewScores & Shortlist",
        },
        {
            "id": "S3_OFFER_CONTRACT",
            "name": "Offer发放与劳动合同签约前置校验",
            "base_hours": 3.0,
            "depends_on": ["S2_SCREENING_INTERVIEW"],
            "deliverable": "JobOffer & LaborContractDraft",
        },
        {
            "id": "S4_ONBOARD_ATTENDANCE",
            "name": "入职建档、考勤班次与排班初始",
            "base_hours": 2.5,
            "depends_on": ["S3_OFFER_CONTRACT"],
            "deliverable": "EmployeeProfile & AttendanceShift",
        },
        {
            "id": "S5_PAYROLL_ENROLLMENT",
            "name": "薪酬制度定级与社保公积金建账",
            "base_hours": 2.5,
            "depends_on": ["S4_ONBOARD_ATTENDANCE"],
            "deliverable": "PayrollInputSlip & SocialSecurityLedger",
        },
    ]

    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # 1. 实体抽取
    # -------------------------------------------------------------------------
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """从自然语言文本中提取招聘职位、人数、紧急度、薪酬预算、合同与入职标志。"""
        # 1.1 人数提取 (例如: 2名, 3人, 1位, 5个HC)
        count = 1
        count_match = re.search(r"(\d+)\s*(?:名|位|人|个|hc|HC)", text, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        else:
            chinese_nums = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            for ch, val in chinese_nums.items():
                if f"{ch}名" in text or f"{ch}位" in text or f"{ch}人" in text:
                    count = val
                    break

        # 1.2 薪酬预算提取 (例如: 25k, 30000元, 20-30k, 50万年薪)
        salary_budget = 0.0
        k_match = re.search(r"(\d+(?:\.\d+)?)\s*[kK]", text)
        if k_match:
            salary_budget = float(k_match.group(1)) * 1000.0
        else:
            wan_match = re.search(r"(\d+(?:\.\d+)?)\s*万", text)
            if wan_match:
                salary_budget = float(wan_match.group(1)) * 10000.0
            else:
                yuan_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块|rmb|cny)", text, re.IGNORECASE)
                if yuan_match:
                    salary_budget = float(yuan_match.group(1))

        # 1.3 紧急度判定
        is_urgent = any(kw in text for kw in ("急", "紧急", "立即", "抢跑", "加急", "快速", "尽快", "下周前"))

        # 1.4 职位角色识别
        roles = []
        role_candidates = [
            "前端工程师", "后端工程师", "全栈工程师", "算法工程师", "测试工程师",
            "产品经理", "UI设计师", "运营专家", "架构师", "HRBP", "财务经理", "商务总监"
        ]
        for rc in role_candidates:
            if rc in text:
                roles.append(rc)
        if not roles:
            # 常见英文技术词
            eng_match = re.search(r"(前端|后端|全栈|算法|开发|设计|产品|运营|人事|财务|sales|dev|qa|pm)", text, re.IGNORECASE)
            if eng_match:
                roles.append(eng_match.group(1))
            else:
                roles.append("通用岗位")

        # 1.5 流程分支识别
        need_contract = any(kw in text for kw in ("合同", "签约", "劳务", "劳动合同", "签署"))
        need_attendance = any(kw in text for kw in ("考勤", "打卡", "排班", "班次", "出勤"))
        need_payroll = any(kw in text for kw in ("薪酬", "工资", "社保", "公积金", "五险一金", "定薪", "薪资"))

        return {
            "target_roles": roles,
            "headcount": count,
            "salary_budget": salary_budget,
            "is_urgent": is_urgent,
            "need_contract": need_contract,
            "need_attendance": need_attendance,
            "need_payroll": need_payroll,
            "raw_text": text,
        }

    # -------------------------------------------------------------------------
    # 2. 意图编译为 DAG 节点
    # -------------------------------------------------------------------------
    def compile_intent(self, text: str) -> List[Dict[str, Any]]:
        """将非结构化自然语言需求编译为包含 5 阶段的标准 Kahn 拓扑 DAG。"""
        entities = self.extract_entities(text)
        is_urgent = entities["is_urgent"]
        urgency_multiplier = 0.8 if is_urgent else 1.0  # 加急工时压缩比

        stages: List[Dict[str, Any]] = []
        for s in self.STANDARD_STAGES:
            stage_node = dict(s)
            est_hours = round(stage_node["base_hours"] * urgency_multiplier * (1.0 + 0.15 * max(0, entities["headcount"] - 1)), 2)
            stage_node["estimated_hours"] = est_hours
            stage_node["estimated_days"] = round(est_hours / 8.0, 2)
            stage_node["status"] = "PENDING"
            stage_node["assigned_agent"] = "R16 蛙人事"
            stage_node["target_roles"] = entities["target_roles"]
            stage_node["headcount"] = entities["headcount"]
            stage_node["salary_budget"] = entities["salary_budget"]
            stages.append(stage_node)

        return stages

    # -------------------------------------------------------------------------
    # 3. Kahn 拓扑排序与依赖工时评估
    # -------------------------------------------------------------------------
    def kahn_topological_sort(self, stages: List[Dict[str, Any]]) -> List[str]:
        """使用 Kahn 算法进行拓扑排序并检测环依赖。

        若存在环状死锁，抛出 ValueError("检测到环依赖，无法生成拓扑序")。
        """
        in_degree: Dict[str, int] = {s["id"]: 0 for s in stages}
        adjacency: Dict[str, List[str]] = {s["id"]: [] for s in stages}

        for s in stages:
            sid = s["id"]
            deps = s.get("depends_on", [])
            for dep in deps:
                if dep in adjacency:
                    adjacency[dep].append(sid)
                    in_degree[sid] += 1

        zero_in_degree = [sid for sid, deg in in_degree.items() if deg == 0]
        topo_order: List[str] = []

        while zero_in_degree:
            curr = zero_in_degree.pop(0)
            topo_order.append(curr)

            for neighbor in adjacency.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    zero_in_degree.append(neighbor)

        if len(topo_order) != len(stages):
            raise ValueError(f"检测到环依赖或未解析节点！总节点={len(stages)}，可解析={len(topo_order)}")

        return topo_order

    def evaluate_budget_and_schedule(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估总工时与人天预算，并计算关键路径。"""
        topo_order = self.kahn_topological_sort(stages)
        stage_map = {s["id"]: s for s in stages}

        total_hours = sum(s.get("estimated_hours", s.get("base_hours", 0.0)) for s in stages)
        total_days = round(total_hours / 8.0, 2)

        # 关键路径计算 (最长耗时路径)
        earliest_finish: Dict[str, float] = {}
        for sid in topo_order:
            s = stage_map[sid]
            h = s.get("estimated_hours", s.get("base_hours", 0.0))
            deps = s.get("depends_on", [])
            if not deps:
                earliest_finish[sid] = h
            else:
                max_prev = max(earliest_finish.get(d, 0.0) for d in deps)
                earliest_finish[sid] = round(max_prev + h, 2)

        critical_path_hours = max(earliest_finish.values()) if earliest_finish else 0.0

        return {
            "topological_sequence": topo_order,
            "total_estimated_hours": round(total_hours, 2),
            "total_estimated_days": total_days,
            "critical_path_hours": critical_path_hours,
            "stages_count": len(stages),
            "is_dag_valid": True,
        }
