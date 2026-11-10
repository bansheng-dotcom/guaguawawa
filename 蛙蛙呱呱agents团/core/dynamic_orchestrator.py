# core/dynamic_orchestrator.py
import uuid
import json
import os
from typing import List, Dict, Any

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLANS_DIR = os.path.join(_REPO, "workspace", "plans")

class MissionControl:
    '''
    动态任务规划与协作中枢 (Mission Control) MVP。
    解决旧版 R01 "只做转发" 的缺点。
    首脑 (R01) 必须在下发任务前，明确拆解出：
    1. 需要哪几个 Agent 参与。
    2. 它们之间的先后或并行关系。
    3. 明确每个 Agent 必须产出什么 (Expected Outcomes)。
    '''
    
    def __init__(self, user_intent: str):
        self.intent = user_intent
        self.plan_id = uuid.uuid4().hex[:8]
        self.team_roster = []
        self.execution_plan = []
        
    def analyze_and_plan(self) -> Dict[str, Any]:
        '''
        核心升级：R01 不再是简单的"抛球者"，而是"排兵布阵者"。
        模拟大模型基于意图生成的动态编排计划。
        '''
        print(f"\n[Mission Control] 正在拆解总目标: 『{self.intent}』")
        
        if "数据" in self.intent and "需求" in self.intent:
            self._plan_product_data_squad()
        else:
            self._plan_standard_squad()
            
        print(f"[Mission Control] 计划已生成，代号: {self.plan_id}")
        return self._export_plan()

    def _plan_product_data_squad(self):
        '''规划：产品+数据+评审 的作战编队'''
        self.team_roster = ["r07(产品)", "r06(数据)", "r04(评审)"]
        self.execution_plan = [
            {
                "step": 1,
                "type": "parallel",
                "agents": [
                    {
                        "role": "r07",
                        "action": "定义核心需求与指标",
                        "expected_output": ["prd_draft.md", "metrics_def.json"]
                    },
                    {
                        "role": "r06",
                        "action": "提取历史基线数据",
                        "expected_output": ["baseline_data.json"]
                    }
                ]
            },
            {
                "step": 2,
                "type": "sequential",
                "agents": [
                    {
                        "role": "r06",
                        "action": "基于 PRD 测算预期收益",
                        "expected_output": ["ROI_report.md"]
                    }
                ]
            },
            {
                "step": 3,
                "type": "gate",
                "agents": [
                    {
                        "role": "r04",
                        "action": "硬门禁复核",
                        "expected_output": ["pass_fail_record.json"]
                    }
                ]
            }
        ]

    def _plan_standard_squad(self):
        self.team_roster = ["r07(产品)", "r04(评审)"]
        self.execution_plan = [
            {"step": 1, "type": "sequential", "agents": [{"role": "r07", "action": "产出方案", "expected_output": ["solution.md"]}]},
            {"step": 2, "type": "gate", "agents": [{"role": "r04", "action": "审查", "expected_output": ["review.json"]}]}
        ]

    def _export_plan(self) -> Dict[str, Any]:
        plan = {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "team_required": self.team_roster,
            "workflow": self.execution_plan
        }
        os.makedirs(_PLANS_DIR, exist_ok=True)
        with open(os.path.join(_PLANS_DIR, f"{self.plan_id}.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        return plan

if __name__ == "__main__":
    mc = MissionControl("设计一个基于数据驱动的新需求")
    plan = mc.analyze_and_plan()
    import json
    print(json.dumps(plan, ensure_ascii=False, indent=2))
