#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 主动链路巡检脚本 (daily_check.py)
import json
import os
import random
import subprocess
import time
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENT = os.path.dirname(_HERE)
_WORKSPACE = os.path.dirname(os.path.dirname(_AGENT)) # 指向 D:\一人公司
CONFIG_PATH = os.path.join(_AGENT, "configs", "data_sources.json")
AGENT_PY = os.path.join(_AGENT, "agent.py")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def fetch_metric(source):
    print(f"[{datetime.now().isoformat()}] 正在从 {source['type']} 拉取数据...")
    time.sleep(1)
    return 0.33, 0.40  # 模拟数据异动

def run_diagnosis(case_id):
    print(f"[{datetime.now().isoformat()}] [触发 SOP] 开始执行诊断案例: {case_id}")
    env = os.environ.copy()
    env['PYTHONPATH'] = _WORKSPACE 
    env['PYTHONIOENCODING'] = 'utf-8' # 强制子进程输出 utf-8
    
    cmd = ["python", AGENT_PY, "diagnose", "--case", case_id]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_AGENT, env=env, encoding='utf-8')
    
    if result.returncode == 0:
        print(f"诊断成功，输出结果:\n{result.stdout.strip()}")
    else:
        print(f"诊断失败:\n{result.stderr.strip()}")

def main():
    print("=== 开始 R06 核心指标主动巡检 ===")
    config = load_config()
    threshold = config.get("monitoring", {}).get("anomaly_threshold", 0.05)
    
    for src_name, src_config in config.get("sources", {}).items():
        if src_name == "ods_orders":
            current, base = fetch_metric(src_config)
            diff = abs(current - base) / base
            print(f"指标 [整体转化率] | 当前: {current:.2%} | 基线: {base:.2%} | 波动幅度: {diff:.2%}")
            if diff > threshold:
                print(f"!!! 警告: 波动幅度 {diff:.2%} 超过阈值 {threshold:.2%} !!!")
                run_diagnosis("funnel_diagnosis")

if __name__ == "__main__":
    main()
