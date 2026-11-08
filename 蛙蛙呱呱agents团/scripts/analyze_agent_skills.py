#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能体能力分析器 - 分析每个智能体的技能接口"""
import json
import os
import re
import sys
from typing import Any, Dict, List

AGENTS_ROOT = r"D:\一人公司\agents"

def analyze_agent_skills(role_dir: str) -> Dict[str, Any]:
    """分析单个智能体的技能配置"""
    agent_path = os.path.join(AGENTS_ROOT, role_dir)
    skills_dir = os.path.join(agent_path, "skills")
    
    result = {
        "role_dir": role_dir,
        "skills": {},
        "examples": []
    }
    
    # 读取SKILL.md获取描述
    skill_md = os.path.join(agent_path, "SKILL.md")
    if os.path.exists(skill_md):
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
            result["skill_md"] = content[:500]
    
    # 分析skills目录
    if os.path.exists(skills_dir):
        for fname in sorted(os.listdir(skills_dir)):
            if fname.startswith("s") and fname.endswith(".py") and not fname.startswith("_"):
                skill_file = os.path.join(skills_dir, fname)
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 提取NAME和DESC
                name_match = re.search(r"NAME\s*=\s*['\"]([^'\"]+)['\"]", content)
                desc_match = re.search(r"DESC\s*=\s*['\"]([^'\"]+)['\"]", content)
                
                # 提取add_parser中的actions
                actions = re.findall(r"sp\.add_parser\(['\"]([^'\"]+)['\"]\)", content)
                
                skill_name = name_match.group(1) if name_match else fname.replace(".py", "")
                result["skills"][skill_name] = {
                    "file": fname,
                    "desc": desc_match.group(1) if desc_match else "",
                    "actions": actions
                }
    
    # 查找examples目录
    examples_dir = os.path.join(agent_path, "examples")
    if os.path.exists(examples_dir):
        result["examples"] = [f for f in os.listdir(examples_dir) if f.endswith(".json")]
    
    return result

def main():
    """分析所有智能体"""
    all_agents = {}
    
    for item in sorted(os.listdir(AGENTS_ROOT)):
        if item.startswith("r") and "-" in item:
            role_id = item.split("-")[0]
            print(f"分析 {role_id} - {item}...")
            all_agents[role_id] = analyze_agent_skills(item)
    
    # 保存分析结果
    output_file = os.path.join(AGENTS_ROOT, "workspace", "agent_skills_analysis.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_agents, f, ensure_ascii=False, indent=2)
    
    print(f"\n分析完成! 结果保存到: {output_file}")
    
    # 打印摘要
    print("\n" + "="*80)
    print("智能体技能摘要")
    print("="*80)
    for role_id, data in all_agents.items():
        print(f"\n{role_id} ({data['role_dir']}):")
        for skill_name, skill_info in data["skills"].items():
            actions = ", ".join(skill_info["actions"][:3])
            if len(skill_info["actions"]) > 3:
                actions += f" ... ({len(skill_info['actions'])}个)"
            print(f"  - {skill_name}: {actions}")

if __name__ == "__main__":
    main()
