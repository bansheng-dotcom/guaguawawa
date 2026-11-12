# -*- coding: utf-8 -*-
"""一人公司 · 人在回路决策座舱 (HIL Cockpit)
"""
import os
import json
from typing import Any, Dict, List

from .workspace import default_root

COCKPIT_DIR = os.path.join(default_root(), "cockpit")

def list_pending_approvals() -> List[Dict[str, Any]]:
    """列出所有待创始人签字的 EVOLUTION_PROPOSAL 或重大决策。"""
    os.makedirs(COCKPIT_DIR, exist_ok=True)
    # 逻辑：扫描所有 RXX/workspace/deep_report/*.json 查看是否有 evolution_proposal
    return []

def approve_decision(proposal_id: str):
    """人工审批通过，自动回写配置。"""
    print(f"[*] 创始人已签发决策: {proposal_id}")
    # 这里集成配置回写逻辑
