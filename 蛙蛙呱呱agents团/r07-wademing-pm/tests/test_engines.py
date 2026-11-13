# -*- coding: utf-8 -*-
"""tests/test_engines.py - L01-L03 演进元模型核心引擎测试套件。"""
import pytest
from engines import PMRuntimeEngine, IntentDAGCompiler, PMReflexiveHealer


def test_pm_runtime_engine_health_probe():
    rt = PMRuntimeEngine()
    probe = rt.probe_health()
    assert probe["status"] == "healthy"
    assert probe["rice_calculator_healthy"] is True
    assert probe["opportunity_calculator_healthy"] is True
    assert probe["ast_audit_healthy"] is True


def test_pm_runtime_engine_calculations():
    rt = PMRuntimeEngine()
    
    # 1. RICE
    items = [
        {"name": "FeatureA", "reach": 100, "impact": 2.0, "confidence": 0.8, "effort": 2.0},
        {"name": "FeatureB", "reach": 50, "impact": 3.0, "confidence": 0.9, "effort": 1.0},
    ]
    res = rt.score_priorities("rice", items)
    ranked = res["ranked_items"]
    assert len(ranked) == 2
    assert ranked[0]["name"] == "FeatureB"
    assert ranked[0]["score"] == 135.0
    assert ranked[1]["name"] == "FeatureA"
    assert ranked[1]["score"] == 80.0

    # 2. Opportunity Score
    opp_items = [
        {"name": "Opp1", "importance": 8.0, "satisfaction": 4.0},
        {"name": "Opp2", "importance": 9.0, "satisfaction": 8.0},
    ]
    opp_res = rt.score_priorities("opportunity", opp_items)
    opp_ranked = opp_res["ranked_items"]
    assert opp_ranked[0]["name"] == "Opp1"
    assert opp_ranked[0]["score"] == 12.0  # 8 + (8-4) = 12
    assert opp_ranked[1]["name"] == "Opp2"
    assert opp_ranked[1]["score"] == 10.0  # 9 + (9-8) = 10


def test_intent_dag_compiler():
    compiler = IntentDAGCompiler()
    res = compiler.decompile_intent("提升企业客户协作效率，完成JTBD调研与PRD故事拆解，制定RICE优先级与里程碑路线图")
    assert res["ok"] is True
    dag = res["dag"]
    assert dag["is_dag"] is True
    assert len(dag["topological_order"]) == 5
    assert dag["topological_order"] == [
        "node_01_discovery",
        "node_02_ost",
        "node_03_prd",
        "node_04_priority",
        "node_05_roadmap",
    ]
    assert dag["total_estimated_hours"] > 0


def test_pm_reflexive_healer():
    healer = PMReflexiveHealer()
    dirty_data = {
        "title": "测试违规需求",
        "executive_summary": "由我拍板决定必须在下周上线，无需审批立即执行。底层采用Redis分布式锁与Go重写实现",
        "metrics": {
            "north_star": "总注册用户数",
        },
        "acceptance_criteria": [],
    }

    # 审计红线
    violations = healer.audit_redlines(dirty_data)
    assert len(violations) >= 3
    assert any("拍板决策" in v for v in violations)
    assert any("越界技术实现" in v for v in violations)
    assert any("虚荣指标" in v for v in violations)

    # 自动自愈修复
    healed = healer.audit_and_heal("prd", dirty_data)
    assert healed["is_healed"] is True
    assert len(healed["actions_taken"]) >= 4
    assert len(healed["healed_data"]["acceptance_criteria"]) >= 2
    assert len(healed["healed_data"]["assumptions"]) >= 3
    assert "telemetry" in healed["healed_data"]
    # 虚荣指标已被修正为真实留存指标
    assert "留存" in healed["healed_data"]["metrics"]["north_star"]
