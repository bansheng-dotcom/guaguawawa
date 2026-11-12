#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能体诊断报告生成器

基于全量运行结果，为每个智能体生成详细的诊断报告。
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List

AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.join(AGENTS_ROOT, "workspace")
REPORT_DIR = os.path.join(WORKSPACE_ROOT, "ai_benchmark_reports")
RESULTS_FILE = os.path.join(REPORT_DIR, "full_benchmark_results.json")
SKILLS_ANALYSIS_FILE = os.path.join(WORKSPACE_ROOT, "agent_skills_analysis.json")

# 角色元数据
ROLE_METADATA = {
    "r01": {"name": "蛙全局", "title": "CEO 主理人 / 编排器", "domain": "战略与治理"},
    "r02": {"name": "蛙排布", "title": "COO 首席运营官", "domain": "运营与执行"},
    "r03": {"name": "蛙守线", "title": "财务合规官 / 红线负责人", "domain": "财务与合规"},
    "r04": {"name": "蛙挑刺", "title": "独立评审官", "domain": "质量与评审"},
    "r05": {"name": "蛙深远", "title": "战略研究官", "domain": "研究与分析"},
    "r06": {"name": "蛙得清", "title": "数据分析师", "domain": "数据与分析"},
    "r07": {"name": "蛙得明", "title": "产品经理", "domain": "产品与规划"},
    "r08": {"name": "蛙建成", "title": "产品实现官 (MVP)", "domain": "产品与实现"},
    "r09": {"name": "蛙稳码", "title": "代码工程官", "domain": "工程与开发"},
    "r10": {"name": "蛙成美", "title": "视觉设计官", "domain": "设计与创意"},
    "r11": {"name": "蛙点题", "title": "内容主笔", "domain": "内容与营销"},
    "r12": {"name": "蛙引流", "title": "增长运营官", "domain": "增长与运营"},
    "r13": {"name": "蛙客成", "title": "客户成功与销售运营官", "domain": "客户与销售"},
    "r14": {"name": "蛙交易", "title": "交易与收入履约官", "domain": "交易与收入"},
    "r15": {"name": "蛙供应", "title": "ERP 与供应链运营官", "domain": "供应链与ERP"},
    "r16": {"name": "蛙人事", "title": "人员与组织运营官", "domain": "人力与组织"},
    "r17": {"name": "蛙织网", "title": "自动化与集成工程师", "domain": "自动化与集成"},
    "r18": {"name": "蛙数仓", "title": "数据工程与管道官", "domain": "数据工程"},
    "r19": {"name": "蛙智模", "title": "模型工程与 AI 评估官", "domain": "AI与模型"},
    "r20": {"name": "蛙值守", "title": "可靠性与恢复官", "domain": "运维与可靠性"},
}


def load_results() -> Dict[str, Any]:
    """加载运行结果"""
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_skills_analysis() -> Dict[str, Any]:
    """加载技能分析"""
    with open(SKILLS_ANALYSIS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_agent_report(role_id: str, results: Dict[str, Any], skills: Dict[str, Any]) -> str:
    """为单个智能体生成诊断报告"""
    meta = ROLE_METADATA.get(role_id, {"name": role_id, "title": "Unknown", "domain": "Unknown"})
    agent_result = results["results"].get(role_id, {})
    agent_skills = skills.get(role_id, {})
    
    report_lines = [
        f"# {meta['name']} ({role_id}) - 运行诊断报告",
        "",
        f"**角色**: {meta['title']}",
        f"**领域**: {meta['domain']}",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 一、执行摘要",
        "",
    ]
    
    # 执行统计
    summary = agent_result.get("summary", {})
    total = summary.get("total", 0)
    success = summary.get("success", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    
    success_rate = (success / total * 100) if total > 0 else 0
    
    report_lines.extend([
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总任务数 | {total} |",
        f"| 成功 | {success} |",
        f"| 失败 | {failed} |",
        f"| 跳过 | {skipped} |",
        f"| 成功率 | {success_rate:.1f}% |",
        "",
    ])
    
    # 状态评估
    if success_rate >= 80:
        status = "[优秀]"
        status_desc = "该智能体运行状态优秀，大部分能力域正常工作。"
    elif success_rate >= 50:
        status = "[良好]"
        status_desc = "该智能体运行状态良好，部分能力域需要关注。"
    elif success_rate >= 20:
        status = "[一般]"
        status_desc = "该智能体运行状态一般，多个能力域存在问题。"
    else:
        status = "[需改进]"
        status_desc = "该智能体运行状态不佳，大部分能力域需要修复。"
    
    report_lines.extend([
        f"**健康状态**: {status}",
        "",
        f"{status_desc}",
        "",
        "---",
        "",
        "## 二、能力域详细分析",
        "",
    ])
    
    # 按技能分组分析
    tasks = agent_result.get("tasks", [])
    skill_stats = {}
    for task in tasks:
        skill = task.get("skill", "unknown")
        if skill not in skill_stats:
            skill_stats[skill] = {"total": 0, "success": 0, "failed": 0, "tasks": []}
        skill_stats[skill]["total"] += 1
        if task.get("success"):
            skill_stats[skill]["success"] += 1
        else:
            skill_stats[skill]["failed"] += 1
        skill_stats[skill]["tasks"].append(task)
    
    # 生成技能表格
    report_lines.extend([
        "| 技能 | 描述 | 任务数 | 成功 | 失败 | 状态 |",
        "|------|------|--------|------|------|------|",
    ])
    
    for skill_name, stats in skill_stats.items():
        skill_info = agent_skills.get("skills", {}).get(skill_name, {})
        desc = skill_info.get("desc", "N/A")[:30]
        s_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        s_status = "[OK]" if s_rate >= 50 else "[FAIL]"
        report_lines.append(
            f"| {skill_name} | {desc} | {stats['total']} | {stats['success']} | {stats['failed']} | {s_status} |"
        )
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 三、失败任务详情",
        "",
    ])
    
    # 失败任务分析
    failed_tasks = [t for t in tasks if not t.get("success")]
    if failed_tasks:
        report_lines.append("以下任务执行失败，需要关注：")
        report_lines.append("")
        for i, task in enumerate(failed_tasks[:10], 1):  # 只显示前10个
            error = task.get("error", "Unknown error")
            stderr = task.get("stderr", "")[:100]
            report_lines.extend([
                f"### {i}. {task.get('skill')}/{task.get('action')}",
                "",
                f"- **描述**: {task.get('description', 'N/A')}",
                f"- **错误**: {error}",
                f"- **退出码**: {task.get('exit_code', 'N/A')}",
                f"- **耗时**: {task.get('elapsed_ms', 0)}ms",
            ])
            if stderr:
                report_lines.append(f"- **stderr**: `{stderr}`")
            report_lines.append("")
    else:
        report_lines.append("所有任务执行成功！")
        report_lines.append("")
    
    report_lines.extend([
        "---",
        "",
        "## 四、成功任务示例",
        "",
    ])
    
    # 成功任务示例
    success_tasks = [t for t in tasks if t.get("success")]
    if success_tasks:
        for i, task in enumerate(success_tasks[:3], 1):  # 只显示前3个
            parsed = task.get("parsed", {})
            report_lines.extend([
                f"### {i}. {task.get('skill')}/{task.get('action')}",
                "",
                f"- **描述**: {task.get('description', 'N/A')}",
                f"- **耗时**: {task.get('elapsed_ms', 0)}ms",
                f"- **结果**: `{json.dumps(parsed, ensure_ascii=False)[:200]}...`" if parsed else "- **结果**: N/A",
                "",
            ])
    else:
        report_lines.append("没有成功执行的任务。")
        report_lines.append("")
    
    report_lines.extend([
        "---",
        "",
        "## 五、建议与改进",
        "",
    ])
    
    # 生成建议
    if failed > 0:
        report_lines.extend([
            "### 高优先级",
            "",
            "1. **修复失败任务**: 检查失败任务的输入数据格式是否符合技能要求",
            "2. **验证技能接口**: 确认技能的action参数是否正确配置",
            "3. **检查依赖**: 确认所有外部依赖已正确安装",
            "",
        ])
    
    if success_rate < 50:
        report_lines.extend([
            "### 中优先级",
            "",
            "1. **增加测试覆盖**: 为关键技能添加更多测试用例",
            "2. **完善文档**: 更新技能使用文档和示例",
            "3. **监控告警**: 添加运行监控和失败告警",
            "",
        ])
    
    report_lines.extend([
        "### 低优先级",
        "",
        "1. **性能优化**: 分析耗时较长的任务，优化执行效率",
        "2. **用户体验**: 改进错误提示信息，使其更友好",
        "3. **扩展功能**: 根据业务需求扩展新的能力域",
        "",
        "---",
        "",
        f"*报告生成时间: {datetime.now().isoformat()}*",
    ])
    
    return "\n".join(report_lines)


def generate_summary_report(results: Dict[str, Any], skills: Dict[str, Any]) -> str:
    """生成总体摘要报告"""
    summary = results.get("summary", {})
    
    report_lines = [
        "# 20个智能体AI主题全量运行诊断报告",
        "",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 一、总体执行摘要",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 智能体总数 | {summary.get('total_agents', 0)} |",
        f"| 总任务数 | {summary.get('total_tasks', 0)} |",
        f"| 成功任务 | {summary.get('successful_tasks', 0)} |",
        f"| 失败任务 | {summary.get('failed_tasks', 0)} |",
        f"| 跳过任务 | {summary.get('skipped_tasks', 0)} |",
        f"| 总耗时 | {summary.get('total_elapsed_ms', 0)}ms |",
        "",
    ]
    
    total_tasks = summary.get('total_tasks', 0)
    success_tasks = summary.get('successful_tasks', 0)
    overall_rate = (success_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    report_lines.extend([
        f"**总体成功率**: {overall_rate:.1f}%",
        "",
        "---",
        "",
        "## 二、各智能体状态概览",
        "",
        "| 角色 | 名称 | 领域 | 任务数 | 成功 | 失败 | 成功率 | 状态 |",
        "|------|------|------|--------|------|------|--------|------|",
    ])
    
    for role_id in sorted(results.get("results", {}).keys()):
        meta = ROLE_METADATA.get(role_id, {"name": role_id, "title": "Unknown"})
        agent_result = results["results"][role_id]
        s = agent_result.get("summary", {})
        total = s.get("total", 0)
        success = s.get("success", 0)
        failed = s.get("failed", 0)
        rate = (success / total * 100) if total > 0 else 0
        status = "[OK]" if rate >= 50 else "[FAIL]"
        
        report_lines.append(
            f"| {role_id} | {meta['name']} | {meta['domain']} | {total} | {success} | {failed} | {rate:.0f}% | {status} |"
        )
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 三、问题分析",
        "",
    ])
    
    # 分析问题
    if overall_rate < 50:
        report_lines.extend([
            "### 主要问题",
            "",
            "1. **输入数据格式不匹配**: 大部分失败是由于生成的测试数据格式与技能期望的输入格式不匹配",
            "2. **技能接口不一致**: 不同智能体的技能接口定义存在差异，需要统一规范",
            "3. **缺少示例数据**: 部分智能体缺少示例输入文件，导致测试数据生成困难",
            "",
            "### 根本原因",
            "",
            "- 智能体之间的技能定义和输入格式缺乏统一标准",
            "- 测试数据生成器需要针对每个技能的具体要求进行定制",
            "- 部分技能需要特定的领域知识才能生成有效的测试数据",
            "",
        ])
    
    report_lines.extend([
        "---",
        "",
        "## 四、改进建议",
        "",
        "### 短期（1-2周）",
        "",
        "1. **修复高优先级失败**: 优先修复影响核心功能的失败任务",
        "2. **标准化输入格式**: 为每个技能定义标准的输入数据格式",
        "3. **完善示例库**: 为每个智能体添加完整的示例输入文件",
        "",
        "### 中期（1-2月）",
        "",
        "1. **统一技能接口**: 建立统一的技能接口规范和测试标准",
        "2. **自动化测试**: 建立完整的自动化测试流程",
        "3. **监控告警**: 添加运行监控和失败告警机制",
        "",
        "### 长期（3-6月）",
        "",
        "1. **持续集成**: 将测试集成到CI/CD流程中",
        "2. **性能优化**: 优化耗时较长的任务",
        "3. **功能扩展**: 根据业务需求扩展新的能力域",
        "",
        "---",
        "",
        "## 五、附录",
        "",
        "### 相关文件",
        "",
        f"- 详细结果: `{RESULTS_FILE}`",
        f"- 技能分析: `{SKILLS_ANALYSIS_FILE}`",
        f"- 个别报告目录: `{REPORT_DIR}`",
        "",
        f"*报告生成时间: {datetime.now().isoformat()}*",
    ])
    
    return "\n".join(report_lines)


def main():
    """主函数"""
    print("加载运行结果...")
    results = load_results()
    
    print("加载技能分析...")
    skills = load_skills_analysis()
    
    print("生成总体摘要报告...")
    summary_report = generate_summary_report(results, skills)
    summary_file = os.path.join(REPORT_DIR, "00_总体诊断报告.md")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_report)
    print(f"  保存到: {summary_file}")
    
    print("\n生成各智能体诊断报告...")
    for role_id in sorted(results.get("results", {}).keys()):
        print(f"  生成 {role_id} 报告...")
        report = generate_agent_report(role_id, results, skills)
        meta = ROLE_METADATA.get(role_id, {"name": role_id})
        report_file = os.path.join(REPORT_DIR, f"{role_id}_{meta['name']}_诊断报告.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
    
    print(f"\n所有报告生成完成！")
    print(f"报告目录: {REPORT_DIR}")


if __name__ == "__main__":
    main()
