# -*- coding: utf-8 -*-
"""R02 十轮全量渐进式演进验收测试套件 (Evolution Verification Suite)。

验证 R01~R10 十个能力阶梯的架构升级点及物理工件落地。
"""
from __future__ import annotations
import json
import os
import sys

# 导入各演进轮次引擎模块
from engines.manager import EngineManager
from engines.prompter import OperationsPrompter
from engines.critic import CriticEvaluator, AutoHealLoop
from engines.ledger import OperationsLedgerParser
from engines.slop_guard import SlopGuard
from engines.explorer import MultiPlanExplorer
from engines.asset_bundle import OperationsAssetBundle
from engines.patch_editor import IncrementalPatchEditor
from engines.memory import SessionMemoryPool
from engines.telemetry import WatchdogCircuitBreaker, ProductionTelemetry

def test_evolution_10_rounds():
    print("=== 开始执行 R02 蛙排布十轮自升级演进严格验收 ===")

    # R01: 外置手脚物理接管
    mgr = EngineManager()
    probe_res = mgr.probe_all()
    assert probe_res["status"] == "ok"
    assert "native" in probe_res["engines"]
    print("  [PASS] R01: 引擎探针与调度接管驱动验证通过")

    # R02: 动态大脑意图解构
    decomp = OperationsPrompter.decompose_intent("请为双11排期，预计总共需15人天，包含关键路径与冲刺日历")
    assert decomp["detected_skill"] == "schedule"
    assert 15.0 in decomp["extracted_mandays"]
    print("  [PASS] R02: 动态业务意图解析与 Prompter 编译器验证通过")

    # R03: 多模态自愈闭环
    heal_res = AutoHealLoop.run_with_heal(
        lambda ctx: {"skill": "capacity", "action": "delegate", "ok": True, "packages": [{"owner": ctx.get("force_owner", "")}]}
    )
    assert heal_res["verdict"] == "PASS"
    assert heal_res["heal_attempts"] == 2
    print("  [PASS] R03: Critic 评审与 Auto-Heal 反思自愈回路验证通过")

    # R04: 规范账本约束
    ledger = OperationsLedgerParser("OPERATIONS_SPEC.md")
    rules = ledger.load_rules()
    assert rules.get("max_task_hours") == 8.0
    print("  [PASS] R04: OPERATIONS_SPEC.md 规范账本与解析引擎验证通过")

    # R05: 去劣精修反伪影
    audit = SlopGuard.audit_text("我们需要相关人员尽快推进，高度重视此项工作。")
    assert not audit["is_clean"]
    polished = SlopGuard.polish("相关人员尽快推进")
    assert "明确排期节点" in polished
    print("  [PASS] R05: SlopGuard 去劣质感与空话精修过滤器验证通过")

    # R06: 多向并行探索
    explored = MultiPlanExplorer.explore_three_plans("双11大促运营", 12)
    assert len(explored["plans"]) == 3
    assert "对比看板" in explored["dashboard_markdown"]
    print("  [PASS] R06: 策略多向裂变探索与对比看板生成器验证通过")

    # R07: 伴生资产交付
    bundle_res = OperationsAssetBundle.bundle("TASK-TEST-001", {"total_cost": 4.0, "item_count": 5}, "./artifacts_test")
    assert os.path.exists(bundle_res["spec_file"])
    print("  [PASS] R07: 结构化伴生规格包 operations_spec.json 导出验证通过")

    # R08: 局部无损微调
    original = {"tasks": [{"name": "A", "estimated_cost": 2.0}, {"name": "B", "estimated_cost": 0.5}]}
    patched = IncrementalPatchEditor.apply_patch(original, "压缩工时")
    assert patched["tasks"][0]["estimated_cost"] == 1.6
    assert patched["tasks"][1]["estimated_cost"] == 0.5
    print("  [PASS] R08: 局部无损增量差量微调器验证通过")

    # R09: 会话状态记忆
    mem = SessionMemoryPool("test_session_state.json")
    mem.save_state("last_plan_id", "PLAN-2026-X")
    assert mem.get_latest("last_plan_id") == "PLAN-2026-X"
    print("  [PASS] R09: 跨轮会话状态池与记忆回滚机制验证通过")

    # R10: 工业容灾编排
    wd = WatchdogCircuitBreaker(timeout_seconds=2.0)
    exec_res = wd.execute_guarded(lambda x: x * 2, 21)
    assert exec_res["ok"] and exec_res["result"] == 42
    telem = ProductionTelemetry("test_telemetry.jsonl")
    telem.record_span("trace-001", "wbs_compute", {"n": 5}, True, 12.5)
    assert os.path.exists("test_telemetry.jsonl")
    print("  [PASS] R10: 工业级 Watchdog 熔断保护与全链路遥测日志验证通过")

    print("\n[SUCCESS] R02 蛙排布十轮自升级演进全部验证通过！")

if __name__ == "__main__":
    test_evolution_10_rounds()
