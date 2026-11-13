# -*- coding: utf-8 -*-
"""engines/scenario_matrix.py - L06 横向决策层 (Comparative Scenario Matrix Layer).

对标开源标杆：Stylescapes / Scenario Planning (Stars > 5k)
核心职责：
1. 拒绝一刀切的单一原型交付，自动裂变三维横向决策看板：
   - 【轻量 MVP 版 (极速验证)】：纯单页/单文件，0依赖，开发工时 0.5天，目标验证核心转化率；
   - 【标准组件版 (商业基准)】：规范化组件封装，支持多断点响应式，工时 1.5天，兼顾美观与拓展；
   - 【生产就绪版 (全功能)】：含完备路由、设计系统、状态管理、A11y 与单元测试，工时 3.0天；
2. 输出包含成本、周期、ROI、风险等级与决策推荐的权衡矩阵 (Trade-off Matrix)。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class ScenarioMatrix:
    """R08 L06 横向交付方案裂变与权衡矩阵引擎。"""

    def __init__(self):
        self.version = "1.0.0"

    def generate_matrix(self, project_name: str, primary_goal: str = "验证核心价值") -> Dict[str, Any]:
        """裂变输出三套差异化交付方案及决策对比矩阵。"""
        scenarios = [
            {
                "id": "lean_mvp",
                "name": "极简切片版 (Lean MVP)",
                "archetype": "极速验证",
                "stack": "Single-file HTML + Tailwind CDN",
                "estimated_hours": 4.0,
                "complexity": "LOW",
                "advantages": ["今天即可上线验证", "零构建工具链开销", "核心转化路径一目了然"],
                "disadvantages": ["缺乏多状态深度交互", "不适合作为长期生产底座"],
                "best_for": "预算有限、抢占时间窗口、仅需验证邮箱收集或意向度",
            },
            {
                "id": "standard_component",
                "name": "标准架构版 (Standard Component)",
                "archetype": "商业基准 (推荐)",
                "stack": "Vite + HTML/Vue + Modular CSS + Formspree",
                "estimated_hours": 12.0,
                "complexity": "MEDIUM",
                "advantages": ["模块化组件清晰", "设计 Token 统一", "平滑交接 R09 研发"],
                "disadvantages": ["需要轻量打包步骤", "开发耗时约 1.5 人天"],
                "best_for": "确定性功能迭代、需要展示给种子投资人或付费客户的商业闭环",
            },
            {
                "id": "production_ready",
                "name": "全功能旗舰版 (Production Ready)",
                "archetype": "严苛就绪",
                "stack": "React / Flutter + Tailwind + State Store + Playwright E2E",
                "estimated_hours": 24.0,
                "complexity": "HIGH",
                "advantages": ["极致跨端体验", "完备自动化测试门禁", "直接支持海量并发扩展"],
                "disadvantages": ["试错成本高", "周期长达 3 人天以上"],
                "best_for": "核心商业壁垒产品、已有明确市场 PMF 的大规模推广",
            },
        ]

        tradeoff_matrix = {
            "dimensions": ["开发工时(h)", "交付速度", "可维护性", "试错成本", "推荐指数"],
            "lean_mvp": [4.0, "极高 (当天)", "中等", "极低", "⭐⭐⭐⭐ (验证期推荐)"],
            "standard_component": [12.0, "高 (1.5天)", "高", "中等", "⭐⭐⭐⭐⭐ (主力推荐)"],
            "production_ready": [24.0, "中等 (3天)", "极高", "高", "⭐⭐⭐ (成长期适用)"],
        }

        return {
            "ok": True,
            "project_name": project_name,
            "primary_goal": primary_goal,
            "recommended_scenario": "standard_component",
            "scenarios": scenarios,
            "tradeoff_matrix": tradeoff_matrix,
            "decision_rule": "若处于第 0~1 个月验证期，强烈建议采纳【极简切片版】或【标准架构版】，严禁在未获PMF前直接上马全功能旗舰版。",
        }
