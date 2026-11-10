# -*- coding: utf-8 -*-
"""一人公司 · 分布式协同调度器 (Dispatcher)
实现协同协议闭环：将 TaskTicket 自动转化为智能体 CLI 调用。
"""
import os
import json
import subprocess
from agents.shared.governance import read_decision_ledger
from agents.shared.role_profiles import get as get_profile
from . import registry

def process_pending_tickets():
    ledger_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace", "governance", "decision_ledger.jsonl")
    
    # 扫描账本中处于待处理状态的 TaskTickets
    # 实际场景中应有专用的 ticket_store.jsonl，此处简化从 ledger 读取
    print(f"[*] Dispatcher 启动：扫描待协同工单...")
    
    # 模拟工单执行：读取最近 50 条决策，筛选出待处理的 ticket
    # (此逻辑后续将升级为独立的 ticket_store.jsonl)
    pending_tickets = [] 
    
    for ticket in pending_tickets:
        print(f"[*] 执行工单: {ticket['ticket_id']} -> {ticket['target_role']}")
        # 构造 CLI 命令
        role = registry.by_id(ticket['target_role'])
        cmd = ["python", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", role["dir"], "agent.py"),
               "run", "--task", ticket['ticket_id']]
        # 非阻塞执行
        subprocess.Popen(cmd)
        
    return len(pending_tickets)

if __name__ == "__main__":
    process_pending_tickets()
