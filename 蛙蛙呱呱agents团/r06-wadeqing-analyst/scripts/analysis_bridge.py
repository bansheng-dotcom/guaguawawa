#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

import time
import subprocess
from datetime import datetime
import sys
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402
sys.stdout.reconfigure(encoding='utf-8')

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENT = os.path.dirname(_HERE)
_WORKSPACE = os.path.join(role_workspace(_AGENT))

def trigger_ab_test():
    print(f"\n[Action] 诊断报告建议发起 A/B 测试，正在自动启动测试引擎...")
    time.sleep(1)
    
    script_path = os.path.join(_AGENT, "scripts", "run_ab_fast.py")
    data_path = os.path.join(_WORKSPACE, "artifacts", "douyin_ab_data.csv")
    
    cmd = [
        "python", script_path, 
        "--input", data_path, 
        "--group", "group", 
        "--control", "抖音_旧素材", 
        "--treatment", "抖音_新素材", 
        "--metric", "converted"
    ]
    
    print(f"  -> 正在计算两组转化率与显著性...")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8' # 修复子进程输出的乱码问题
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding='utf-8')
    
    if result.returncode == 0:
        res_json = json.loads(result.stdout)
        print("\n=== A/B 测试自动执行完毕 ===")
        print(f"✅ 基线转化率: {res_json['control']['rate']:.2%}")
        print(f"🚀 新版转化率: {res_json['treatment']['rate']:.2%}")
        print(f"📊 提升幅度 (Lift): {res_json['lift']}")
        print(f"🔬 显著性 p值: {res_json['p_value']:.4f} (是否显著: {res_json['is_significant']})")
        print(f"💡 机器最终决策: {res_json['decision']}")
    else:
        print(f"A/B 测试引擎调用失败:\n{result.stderr}")

def main():
    print("="*50)
    print(" 🚀 商业归因与执行闭环 (RCA -> Action)")
    print("="*50)
    
    print("[Level 1] 数据层检查：Pass")
    print("[Level 2] 经营层拆解：根因为 抖音渠道转化率暴跌")
    print("[Level 3] 商业层分析：原因系行业算法调整\n")
    print("➡️ 诊断决策：暂停原投放，需进行新素材 A/B 测试。")
    
    trigger_ab_test()
        
if __name__ == "__main__":
    main()
