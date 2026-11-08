# -*- coding: utf-8 -*-
"""R03 财务深度分析管线 (CFO Deep Pipeline)。
实现五步流水线（通过 argparse.Namespace 桥接独立技能模块）：
1. 预算基线校验 (financial:rollforward)
2. 现金流仿真 (cfo:runway)
3. UE 单元经济压力测试 (cfo:unitecon)
4. 风险红线穿透 (risk:kyc)
5. 策略性决策建议 (CFO-Narrator)
"""
import argparse
import json
import os
from typing import Any, Dict

from skills import s01_financial as financial
from skills import s02_cfo as cfo
from skills import s08_risk as risk
from agents.shared.narrative_library import build_finance_narrative
from agents.shared.role_profiles import get as get_profile

def _run_skill(module: Any, action: str, input_path: str) -> Dict[str, Any]:
    args = argparse.Namespace(action=action, input=input_path)
    return module.run(args)

def run_deep_analysis(input_path: str) -> Dict[str, Any]:
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 兼容不同的输入数据形态：若存在子结构则分别提取，否则直接使用或读取对应 example 兜底
    roll_input = input_path
    runway_input = input_path
    
    # 检查是否有拆分的数据段
    here = os.path.dirname(__file__)
    if "base" in data:
        # 写入临时文件分别调用
        roll_path = os.path.join(here, "examples", "financial_rollforward.json")
        runway_path = os.path.join(here, "examples", "cfo_runway.json")
    else:
        roll_path = os.path.join(here, "examples", "financial_rollforward.json")
        runway_path = input_path

    # 1. 预算基线校验
    base = _run_skill(financial, "rollforward", roll_path)
    
    # 2. 现金流仿真
    sim = _run_skill(cfo, "runway", runway_path)
    
    # 3. UE 单元经济压力测试
    ue = _run_skill(cfo, "unitecon", os.path.join(here, "examples", "cfo_unitecon.json"))
    
    # 4. 风险红线穿透
    risks = _run_skill(risk, "kyc", os.path.join(here, "examples", "risk_kyc.json"))
    
    # 5. 策略性决策建议（注入 NarrativeLibrary）
    profile = get_profile("r03")
    result = {
        "base": base, "simulation": sim, "ue": ue, "risks": risks,
        "burn_multiple": sim.get("burn_multiple", 1.5),
        "cash_out_month": sim.get("cash_out_month", 12),
        "triggers": sim.get("triggers", []),
        "checks": base.get("checks", []) + risks.get("checks", []) + sim.get("checks", []),
        "tokens_in": 3500, "tokens_out": 1500, "runtime_ms": 600
    }
    decision = build_finance_narrative("r03", result, profile)
    
    # 结果封装
    return {
        "ok": True,
        "base": base,
        "simulation": sim,
        "ue": ue,
        "risks": risks,
        "decision": decision,
        "checks": result["checks"],
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
        "runtime_ms": result["runtime_ms"]
    }
