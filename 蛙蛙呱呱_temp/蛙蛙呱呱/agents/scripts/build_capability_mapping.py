#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力域深度映射构建器

解析每个智能体的技能接口，构建能力域到任务的映射表。
"""
import json
import os
import re
from typing import Any, Dict, List

AGENTS_ROOT = r"D:\一人公司\agents"

# AI主题任务模板 - 按能力域定制
AI_TASK_TEMPLATES = {
    # R01 CEO
    "r01": {
        "intent_brief": {"desc": "AI产品战略意图识别", "input_type": "brief"},
        "intent_clarify": {"desc": "AI项目六问澄清", "input_type": "clarify"},
        "intent_triage": {"desc": "AI决策分级路由", "input_type": "triage"},
        "decompose_taskcard": {"desc": "AI项目跨部门拆解", "input_type": "taskcard"},
        "decide_card": {"desc": "AI投资决策卡", "input_type": "decision_card"},
        "redteam_devil": {"desc": "AI方案反方质询", "input_type": "redteam"},
        "companyos_os": {"desc": "AI公司治理OS评估", "input_type": "companyos"},
        "decisionlog_entry": {"desc": "AI决策留痕记录", "input_type": "decisionlog"},
        "boardroom_memo": {"desc": "AI董事会汇报材料", "input_type": "board"},
    },
    # R02 COO
    "r02": {
        "schedule_wbs": {"desc": "AI项目WBS工作分解", "input_type": "wbs"},
        "schedule_sprint": {"desc": "AI迭代冲刺规划", "input_type": "sprint"},
        "capacity_check": {"desc": "AI团队容量检查", "input_type": "capacity"},
        "handoff_package": {"desc": "AI交付物打包验收", "input_type": "handoff"},
        "retro_postmortem": {"desc": "AI事故复盘分析", "input_type": "incident"},
        "process_sop": {"desc": "AI流程SOP标准化", "input_type": "sop"},
        "knowledge_digest": {"desc": "AI知识文档摘要", "input_type": "digest"},
        "portfolio_status": {"desc": "AI项目群状态追踪", "input_type": "portfolio"},
    },
    # R03 CFO
    "r03": {
        "financial_rollforward": {"desc": "AI财务报表结转", "input_type": "financial_rollforward"},
        "cfo_runway": {"desc": "AI公司Runway现金流分析", "input_type": "cfo_runway"},
        "tax_iso": {"desc": "AI税务ISO合规检查", "input_type": "tax_iso"},
        "contract_scan": {"desc": "AI合同条款扫描", "input_type": "contract_scan"},
        "privacy_map": {"desc": "AI隐私数据流映射", "input_type": "privacy_map"},
        "aigov_aiclassify": {"desc": "AI系统风险分类", "input_type": "aigov_aiclassify"},
        "audit_retention": {"desc": "AI审计留存策略", "input_type": "audit_retention"},
        "risk_kyc": {"desc": "AI KYC客户身份验证", "input_type": "risk_kyc"},
    },
    # R06 数据分析师
    "r06": {
        "semantics_validate": {"desc": "AI指标语义模型验证", "input_type": "semantic_model"},
        "quality_audit": {"desc": "AI数据质量六维审计", "input_type": "dataset"},
        "explore_trend": {"desc": "AI业务趋势时序分析", "input_type": "timeseries"},
        "explore_funnel": {"desc": "AI转化漏斗分析", "input_type": "funnel_data"},
        "rootcause_drilldown": {"desc": "AI指标异常根因下钻", "input_type": "multidim_data"},
        "abtest_abtest": {"desc": "AI A/B实验显著性检验", "input_type": "abtest_data"},
        "describe_describe": {"desc": "AI数据描述统计", "input_type": "numeric_data"},
        "viz_report": {"desc": "AI可视化分析报告", "input_type": "chart_spec"},
        "selfmedia_dashboard": {"desc": "AI自媒体运营仪表盘", "input_type": "social_metrics"},
    },
    # R07 产品经理
    "r07": {
        "discover_jtbd": {"desc": "AI产品JTBD用户研究", "input_type": "user_research"},
        "prd_write": {"desc": "AI功能PRD撰写", "input_type": "feature_req"},
        "priority_backlog": {"desc": "AI需求优先级排序", "input_type": "backlog_items"},
        "roadmap_release": {"desc": "AI产品路线图规划", "input_type": "roadmap_input"},
        "metrics_define": {"desc": "AI北极星指标定义", "input_type": "metric_spec"},
    },
}


def extract_skill_actions(agent_dir: str) -> Dict[str, List[str]]:
    """从agent目录提取所有技能的actions"""
    skills_dir = os.path.join(AGENTS_ROOT, agent_dir, "skills")
    result = {}
    
    if not os.path.exists(skills_dir):
        return result
    
    for fname in sorted(os.listdir(skills_dir)):
        if fname.startswith("s") and fname.endswith(".py") and not fname.startswith("_"):
            skill_file = os.path.join(skills_dir, fname)
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 提取NAME
            name_match = re.search(r"NAME\s*=\s*['\"]([^'\"]+)['\"]", content)
            skill_name = name_match.group(1) if name_match else fname.replace(".py", "")
            
            # 提取actions - 查找 add_parser 调用（支持多种模式）
            # 模式1: sp.add_parser("action")
            actions1 = re.findall(r"sp\.add_parser\(['\"]([^'\"]+)['\"]\)", content)
            # 模式2: act.add_parser("action")
            actions2 = re.findall(r"act\.add_parser\(['\"]([^'\"]+)['\"]\)", content)
            # 模式3: 从元组列表提取 (("a1", "h1"), ("a2", "h2"))
            tuple_matches = re.findall(r'\(\(["\'"]([^\'"]+)["\']', content)
            
            actions = list(set(actions1 + actions2 + tuple_matches))
            
            if actions:
                result[skill_name] = actions
    
    return result


def build_capability_mapping():
    """构建完整的能力域映射表"""
    mapping = {}
    
    # 遍历所有智能体目录
    for item in sorted(os.listdir(AGENTS_ROOT)):
        if item.startswith("r") and "-" in item and os.path.isdir(os.path.join(AGENTS_ROOT, item)):
            role_id = item.split("-")[0]
            print(f"分析 {role_id} - {item}...")
            
            # 提取技能actions
            skills = extract_skill_actions(item)
            
            # 获取示例文件
            examples_dir = os.path.join(AGENTS_ROOT, item, "examples")
            examples = []
            if os.path.exists(examples_dir):
                examples = [f for f in os.listdir(examples_dir) if f.endswith(".json")]
            
            mapping[role_id] = {
                "dir": item,
                "skills": skills,
                "examples": examples,
                "templates": AI_TASK_TEMPLATES.get(role_id, {})
            }
    
    return mapping


def generate_task_dataset(role_id: str, skill: str, action: str, template: Dict) -> Dict[str, Any]:
    """为特定能力域生成定制化数据集"""
    input_type = template.get("input_type", "generic")
    
    # 根据输入类型生成不同的数据结构
    if input_type == "brief":
        return {
            "problem": "是否引入AI客服系统替代人工客服",
            "options": [
                {"label": "全面替换", "summary": "节省60%人力成本，但可能影响服务质量"},
                {"label": "人机协作", "summary": "AI处理简单问题，复杂问题转人工"},
                {"label": "暂不引入", "summary": "维持现状，观察竞品效果"}
            ],
            "assumptions": ["AI客服准确率可达85%", "客户接受度调研显示70%愿意尝试"],
            "constraints": {"time": "Q4上线", "budget": "50万以内"},
            "success_criteria": [{"metric": "客户满意度", "threshold": ">=4.2/5"}],
            "kill_criteria": [{"metric": "投诉率", "threshold": ">5%", "action": "回滚到纯人工"}]
        }
    
    elif input_type == "dataset" or input_type == "timeseries":
        # 返回CSV内容
        rows = ["date,channel,revenue,cost,users,conversion_rate"]
        channels = ["抖音", "微信", "小红书", "知乎"]
        for i in range(30):
            date = f"2026-10-{i+1:02d}"
            channel = channels[i % 4]
            revenue = round(1000 + i * 50 + (i % 7) * 100, 2)
            cost = round(revenue * 0.3, 2)
            users = int(100 + i * 10)
            conv = round(users / 1000, 3)
            rows.append(f"{date},{channel},{revenue},{cost},{users},{conv}")
        return "\n".join(rows)
    
    elif input_type == "semantic_model":
        return {
            "metrics": [
                {"name": "DAU", "definition": "日活跃用户数", "formula": "COUNT(DISTINCT user_id WHERE active=true)"},
                {"name": "Retention_D7", "definition": "7日留存率", "formula": "COUNT(returning_users) / COUNT(new_users)"}
            ],
            "dimensions": ["date", "channel", "platform", "user_segment"]
        }
    
    elif input_type == "aigov_aiclassify":
        return {
            "system": {
                "practices": ["credit_scoring", "automated_decision_making"],
                "conformity_assessment": True,
                "human_oversight": True,
                "data_subjects": 10000,
                "deployment_scope": "EU"
            }
        }
    
    elif input_type == "wbs":
        return {
            "project": "AI智能客服系统",
            "phases": [
                {"name": "需求分析", "duration_days": 5, "owner": "PM"},
                {"name": "技术选型", "duration_days": 3, "owner": "Tech Lead"},
                {"name": "MVP开发", "duration_days": 14, "owner": "Dev Team"},
                {"name": "测试验收", "duration_days": 5, "owner": "QA"}
            ]
        }
    
    elif input_type == "user_research":
        return {
            "persona": "中小企业财务总监",
            "jobs_to_be_done": [
                "快速完成月度财务报表",
                "实时监控现金流状况",
                "自动生成合规审计报告"
            ],
            "pain_points": ["手工录入耗时", "数据口径不一致", "审计准备周期长"]
        }
    
    else:
        # 通用JSON输入
        return {
            "intent": f"AI{template.get('desc', '任务')}",
            "context": {"domain": "ai_business", "priority": "high"},
            "parameters": {"scope": "enterprise"}
        }


def main():
    print("=" * 80)
    print("构建能力域-任务映射表")
    print("=" * 80)
    
    mapping = build_capability_mapping()
    
    # 保存映射表
    output_file = os.path.join(AGENTS_ROOT, "workspace", "capability_task_mapping.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\n映射表已保存到: {output_file}")
    
    # 打印摘要
    print("\n" + "=" * 80)
    print("能力域摘要")
    print("=" * 80)
    
    total_skills = 0
    total_actions = 0
    
    for role_id, data in sorted(mapping.items()):
        skills = data.get("skills", {})
        templates = data.get("templates", {})
        
        skill_count = len(skills)
        action_count = sum(len(actions) for actions in skills.values())
        template_count = len(templates)
        
        total_skills += skill_count
        total_actions += action_count
        
        print(f"\n{role_id} ({data['dir']}):")
        print(f"  技能数: {skill_count}, 动作数: {action_count}, 预定义模板: {template_count}")
        
        for skill_name, actions in list(skills.items())[:3]:
            print(f"    - {skill_name}: {', '.join(actions[:3])}")
    
    print(f"\n总计: {len(mapping)} 个智能体, {total_skills} 个技能, {total_actions} 个动作")


if __name__ == "__main__":
    main()
