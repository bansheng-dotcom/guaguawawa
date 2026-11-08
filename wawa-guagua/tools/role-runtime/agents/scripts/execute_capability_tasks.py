#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量智能体能力域执行器 - 基于真实技能接口

为每个智能体的每个能力域生成定制化AI主题任务和数据集，
执行真实任务并收集产出。
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

AGENTS_ROOT = r"D:\一人公司\agents"
WORKSPACE_ROOT = os.path.join(AGENTS_ROOT, "workspace")
OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, "ai_capability_outputs")
PYTHON_EXE = sys.executable

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 基于真实技能接口的任务定义
CAPABILITY_TASKS = {
    "r01": {
        "name": "蛙全局",
        "title": "CEO 主理人 / 编排器",
        "tasks": [
            {
                "skill": "intent", "action": "brief", 
                "desc": "AI产品战略意图识别",
                "input": {
                    "problem": "是否投入500万开发企业级AI客服系统",
                    "options": [
                        {"label": "全面自研", "summary": "投入大但可控性强"},
                        {"label": "采购SaaS", "summary": "快速上线但定制性差"},
                        {"label": "混合模式", "summary": "核心自研+外围采购"}
                    ],
                    "assumptions": ["AI客服准确率可达85%", "市场规模年增长30%"],
                    "constraints": {"time": "6个月内", "budget": "500万"},
                    "success_criteria": [{"metric": "客户满意度", "threshold": ">=4.5"}],
                    "kill_criteria": [{"metric": "投诉率", "threshold": ">3%", "action": "暂停推广"}]
                }
            },
            {
                "skill": "intent", "action": "triage",
                "desc": "AI项目分级路由",
                "input": {"intent": "分析AI客服系统的用户行为数据趋势"}
            },
            {
                "skill": "decompose", "action": "taskcard",
                "desc": "AI项目跨部门拆解",
                "input": {
                    "title": "AI客服系统开发",
                    "goal": "构建企业级AI客服解决方案",
                    "deliverables": ["需求文档", "技术方案", "MVP产品"],
                    "constraints": {"timeline": "Q4", "budget": "500万"}
                }
            },
        ]
    },
    "r02": {
        "name": "蛙排布",
        "title": "COO 首席运营官",
        "tasks": [
            {
                "skill": "schedule", "action": "wbs",
                "desc": "AI项目WBS工作分解",
                "input": {
                    "work_breakdown": [
                        {"name": "需求分析", "kind": "analysis", "step": 1, "question": "用户需要什么", "details": "PRD文档", "estimated_cost": 2.0},
                        {"name": "技术选型", "kind": "design", "step": 2, "question": "用什么技术栈", "details": "技术方案", "estimated_cost": 1.5},
                        {"name": "MVP开发", "kind": "implementation", "step": 3, "question": "如何快速验证", "details": "可运行原型", "estimated_cost": 10.0},
                        {"name": "测试验收", "kind": "testing", "step": 4, "question": "是否满足需求", "details": "测试报告", "estimated_cost": 3.0}
                    ]
                }
            },
            {
                "skill": "capacity", "action": "check",
                "desc": "AI团队容量检查",
                "input": {
                    "team": {"developers": 5, "designers": 2, "qa": 2},
                    "workload": {"planned_hours": 800, "available_hours": 720}
                }
            },
        ]
    },
    "r03": {
        "name": "蛙守线",
        "title": "财务合规官 / 红线负责人",
        "tasks": [
            {
                "skill": "aigov", "action": "aiclassify",
                "desc": "AI系统风险分类",
                "input": {
                    "system": {
                        "practices": ["credit_scoring", "automated_decision"],
                        "conformity_assessment": True,
                        "human_oversight": True
                    }
                }
            },
            {
                "skill": "cfo", "action": "runway",
                "desc": "AI公司现金流分析",
                "input": {
                    "cash_balance": 5000000,
                    "monthly_burn": 800000,
                    "monthly_revenue": 200000
                }
            },
        ]
    },
    "r06": {
        "name": "蛙得清",
        "title": "数据分析师",
        "tasks": [
            {
                "skill": "quality", "action": "audit",
                "desc": "AI数据质量六维审计",
                "input_type": "csv",
                "input": "date,channel,revenue,cost,users\n2026-11-01,抖音,15000,4500,1200\n2026-11-02,微信,12000,3600,980\n2026-11-03,小红书,8000,2400,650\n2026-11-04,知乎,6000,1800,450\n2026-11-05,抖音,18000,5400,1500"
            },
            {
                "skill": "explore", "action": "trend",
                "desc": "AI业务趋势分析",
                "input_type": "csv",
                "input": "date,amount\n2026-11-01,15000\n2026-11-02,12000\n2026-11-03,8000\n2026-11-04,6000\n2026-11-05,18000"
            },
            {
                "skill": "describe", "action": "describe",
                "desc": "AI数据描述统计",
                "input_type": "csv",
                "input": "value\n100\n150\n200\n180\n220\n190\n210"
            },
        ]
    },
    "r07": {
        "name": "蛙得明",
        "title": "产品经理",
        "tasks": [
            {
                "skill": "priority", "action": "backlog",
                "desc": "AI需求优先级排序",
                "input": {
                    "items": [
                        {"id": "F001", "title": "AI智能推荐", "value": 9, "effort": 8},
                        {"id": "F002", "title": "语音交互", "value": 7, "effort": 6},
                        {"id": "F003", "title": "数据分析", "value": 8, "effort": 4}
                    ]
                }
            },
        ]
    },
}


def write_input_file(role_id: str, skill: str, action: str, input_data: Any, input_type: str = "json") -> str:
    """写入输入文件"""
    task_dir = os.path.join(OUTPUT_DIR, role_id, f"{skill}_{action}")
    os.makedirs(task_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if input_type == "csv":
        input_file = os.path.join(task_dir, f"input_{timestamp}.csv")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(input_data)
    else:
        input_file = os.path.join(task_dir, f"input_{timestamp}.json")
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)
    
    return input_file


def run_agent_task(role_id: str, skill: str, action: str, input_file: str) -> Dict[str, Any]:
    """运行单个智能体任务"""
    # 查找agent.py
    import glob
    agent_files = glob.glob(os.path.join(AGENTS_ROOT, f"{role_id}-*", "agent.py"))
    if not agent_files:
        return {"error": f"Agent not found: {role_id}", "success": False}
    
    agent_py = agent_files[0]
    agent_dir = os.path.dirname(agent_py)
    
    cmd = [PYTHON_EXE, agent_py, skill, action, "--input", input_file]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",  # 使用replace处理无法解码的字符
            timeout=60,
            cwd=agent_dir
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        
        # 解析结果
        parsed = None
        marker = "__AGENT_RESULT__ "
        if marker in stdout:
            for line in stdout.splitlines():
                if line.startswith(marker):
                    try:
                        parsed = json.loads(line[len(marker):])
                    except:
                        parsed = {"raw": line[len(marker):]}
                    break
        
        return {
            "success": result.returncode == 0 and parsed is not None,
            "exit_code": result.returncode,
            "elapsed_ms": elapsed_ms,
            "stdout": stdout[:1000],
            "stderr": stderr[:500],
            "parsed": parsed
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "success": False, "elapsed_ms": 60000}
    except Exception as e:
        return {"error": str(e), "success": False}


def save_output(role_id: str, skill: str, action: str, result: Dict[str, Any]):
    """保存任务输出"""
    task_dir = os.path.join(OUTPUT_DIR, role_id, f"{skill}_{action}")
    os.makedirs(task_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存原始结果
    result_file = os.path.join(task_dir, f"result_{timestamp}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 如果有解析结果，保存为业务产出
    if result.get("parsed"):
        output_file = os.path.join(task_dir, f"output_{timestamp}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result["parsed"], f, ensure_ascii=False, indent=2)


def main():
    print("=" * 80)
    print("全量智能体能力域执行")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 80)
    
    all_results = {}
    summary = {"total": 0, "success": 0, "failed": 0}
    
    for role_id, config in CAPABILITY_TASKS.items():
        print(f"\n{'='*60}")
        print(f"执行 {role_id} - {config['name']} ({config['title']})")
        print(f"{'='*60}")
        
        role_results = []
        
        for task in config["tasks"]:
            skill = task["skill"]
            action = task["action"]
            desc = task["desc"]
            input_data = task["input"]
            input_type = task.get("input_type", "json")
            
            print(f"\n  [{skill}/{action}] {desc}")
            
            # 写入输入文件
            input_file = write_input_file(role_id, skill, action, input_data, input_type)
            print(f"    输入文件: {input_file}")
            
            # 执行任务
            result = run_agent_task(role_id, skill, action, input_file)
            
            # 保存输出
            save_output(role_id, skill, action, result)
            
            # 记录结果
            task_result = {
                "role_id": role_id,
                "skill": skill,
                "action": action,
                "description": desc,
                "input_file": input_file,
                **result
            }
            role_results.append(task_result)
            
            summary["total"] += 1
            if result.get("success"):
                summary["success"] += 1
                print(f"    状态: [成功] ({result.get('elapsed_ms', 0)}ms)")
            else:
                summary["failed"] += 1
                error = result.get("error", "Unknown")
                print(f"    状态: [失败] {error}")
        
        all_results[role_id] = {
            "name": config["name"],
            "title": config["title"],
            "tasks": role_results
        }
    
    # 保存总结果
    summary_file = os.path.join(OUTPUT_DIR, "execution_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print("执行完成!")
    print(f"总任务: {summary['total']}")
    print(f"成功: {summary['success']}")
    print(f"失败: {summary['failed']}")
    print(f"成功率: {summary['success']/summary['total']*100:.1f}%")
    print(f"结果保存: {summary_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
