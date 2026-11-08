#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力产出报告生成器

基于执行结果，为每个智能体生成：
1. 各能力域的业务产出报告
2. 智能体运行诊断报告
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List

AGENTS_ROOT = r"D:\一人公司\agents"
WORKSPACE_ROOT = os.path.join(AGENTS_ROOT, "workspace")
OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, "ai_capability_outputs")
REPORT_DIR = os.path.join(WORKSPACE_ROOT, "ai_capability_reports")

os.makedirs(REPORT_DIR, exist_ok=True)


def load_execution_results() -> Dict[str, Any]:
    """加载执行结果"""
    summary_file = os.path.join(OUTPUT_DIR, "execution_summary.json")
    with open(summary_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_capability_output_report(role_id: str, role_data: Dict[str, Any]) -> str:
    """生成单个智能体的能力产出报告"""
    name = role_data.get("name", role_id)
    title = role_data.get("title", "")
    tasks = role_data.get("tasks", [])
    
    report_lines = [
        f"# {name} ({role_id}) - 能力产出报告",
        "",
        f"**角色**: {title}",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 一、执行概览",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 任务总数 | {len(tasks)} |",
        f"| 成功 | {sum(1 for t in tasks if t.get('success'))} |",
        f"| 失败 | {sum(1 for t in tasks if not t.get('success'))} |",
        "",
        "---",
        "",
        "## 二、各能力域产出详情",
        "",
    ]
    
    for i, task in enumerate(tasks, 1):
        skill = task.get("skill", "unknown")
        action = task.get("action", "unknown")
        desc = task.get("description", "")
        success = task.get("success", False)
        parsed = task.get("parsed", {})
        
        status_icon = "[PASS]" if success else "[FAIL]"
        
        report_lines.extend([
            f"### {i}. {skill}/{action} - {desc}",
            "",
            f"**状态**: {status_icon}",
            f"**耗时**: {task.get('elapsed_ms', 0)}ms",
            "",
        ])
        
        if success and parsed:
            report_lines.append("**业务产出**:")
            report_lines.append("")
            report_lines.append("```json")
            report_lines.append(json.dumps(parsed, ensure_ascii=False, indent=2))
            report_lines.append("```")
            report_lines.append("")
            
            # 提取关键信息
            if "checks" in parsed:
                checks = parsed["checks"]
                passed = sum(1 for c in checks if c.get("ok"))
                failed = len(checks) - passed
                report_lines.append(f"**门禁检查**: {passed} 通过 / {failed} 失败")
                report_lines.append("")
                
                for check in checks:
                    ok = check.get("ok", False)
                    msg = check.get("msg", "")
                    sev = check.get("sev", "")
                    icon = "[OK]" if ok else f"[{sev}]"
                    report_lines.append(f"- {icon} {msg}")
                report_lines.append("")
            
            if "next" in parsed:
                report_lines.append(f"**下一步建议**: {parsed['next']}")
                report_lines.append("")
        else:
            error = task.get("error", "Unknown error")
            stderr = task.get("stderr", "")[:200]
            report_lines.extend([
                f"**错误**: {error}",
            ])
            if stderr:
                report_lines.append(f"**stderr**: `{stderr}`")
            report_lines.append("")
        
        report_lines.append("---")
        report_lines.append("")
    
    return "\n".join(report_lines)


def generate_agent_diagnostic_report(role_id: str, role_data: Dict[str, Any]) -> str:
    """生成单个智能体的运行诊断报告"""
    name = role_data.get("name", role_id)
    title = role_data.get("title", "")
    tasks = role_data.get("tasks", [])
    
    total = len(tasks)
    success_count = sum(1 for t in tasks if t.get("success"))
    fail_count = total - success_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    # 健康状态评估
    if success_rate >= 80:
        health = "[优秀]"
        health_desc = "该智能体运行状态优秀，大部分能力域正常工作。"
    elif success_rate >= 50:
        health = "[良好]"
        health_desc = "该智能体运行状态良好，部分能力域需要关注。"
    elif success_rate >= 20:
        health = "[一般]"
        health_desc = "该智能体运行状态一般，多个能力域存在问题。"
    else:
        health = "[需改进]"
        health_desc = "该智能体运行状态不佳，大部分能力域需要修复。"
    
    report_lines = [
        f"# {name} ({role_id}) - 运行诊断报告",
        "",
        f"**角色**: {title}",
        f"**健康状态**: {health}",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 一、执行摘要",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总任务数 | {total} |",
        f"| 成功 | {success_count} |",
        f"| 失败 | {fail_count} |",
        f"| 成功率 | {success_rate:.1f}% |",
        "",
        f"{health_desc}",
        "",
        "---",
        "",
        "## 二、能力域状态矩阵",
        "",
        "| 技能 | 动作 | 描述 | 状态 | 耗时(ms) |",
        "|------|------|------|------|----------|",
    ]
    
    for task in tasks:
        skill = task.get("skill", "?")
        action = task.get("action", "?")
        desc = task.get("description", "")[:20]
        success = task.get("success", False)
        elapsed = task.get("elapsed_ms", 0)
        status = "[PASS]" if success else "[FAIL]"
        report_lines.append(f"| {skill} | {action} | {desc} | {status} | {elapsed} |")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 三、失败分析",
        "",
    ])
    
    failed_tasks = [t for t in tasks if not t.get("success")]
    if failed_tasks:
        for i, task in enumerate(failed_tasks, 1):
            skill = task.get("skill", "?")
            action = task.get("action", "?")
            desc = task.get("description", "")
            error = task.get("error", "Unknown")
            exit_code = task.get("exit_code", "?")
            parsed = task.get("parsed", {})
            
            report_lines.extend([
                f"### {i}. {skill}/{action}",
                "",
                f"- **描述**: {desc}",
                f"- **退出码**: {exit_code}",
                f"- **错误**: {error}",
            ])
            
            # 如果有解析结果但ok=false，显示详细原因
            if parsed and parsed.get("ok") == False:
                checks = parsed.get("checks", [])
                blockers = [c for c in checks if c.get("sev") == "BLOCKER" or c.get("sev") == "CRITICAL"]
                if blockers:
                    report_lines.append("- **阻断原因**:")
                    for b in blockers:
                        report_lines.append(f"  - [{b.get('sev')}] {b.get('msg')}")
            
            report_lines.append("")
    else:
        report_lines.append("所有任务执行成功！")
        report_lines.append("")
    
    report_lines.extend([
        "---",
        "",
        "## 四、改进建议",
        "",
    ])
    
    if fail_count > 0:
        report_lines.extend([
            "### 高优先级",
            "",
            "1. **修复输入数据格式**: 确保输入符合技能的预期schema",
            "2. **补充必填字段**: 检查任务卡/配置中的必填项",
            "3. **验证参数范围**: 确认数值参数在允许范围内",
            "",
        ])
    
    report_lines.extend([
        "### 低优先级",
        "",
        "1. **增加测试覆盖**: 为边界情况添加测试用例",
        "2. **优化性能**: 分析耗时较长的任务",
        "3. **完善文档**: 更新技能使用说明",
        "",
        "---",
        "",
        f"*报告生成时间: {datetime.now().isoformat()}*",
    ])
    
    return "\n".join(report_lines)


def generate_overall_summary(results: Dict[str, Any]) -> str:
    """生成总体汇总报告"""
    all_results = results.get("results", {})
    summary = results.get("summary", {})
    
    report_lines = [
        "# 20个智能体AI主题全量能力校验报告",
        "",
        f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 一、总体执行摘要",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 智能体总数 | {len(all_results)} |",
        f"| 总任务数 | {summary.get('total', 0)} |",
        f"| 成功任务 | {summary.get('success', 0)} |",
        f"| 失败任务 | {summary.get('failed', 0)} |",
        "",
    ]
    
    total = summary.get("total", 0)
    success = summary.get("success", 0)
    rate = (success / total * 100) if total > 0 else 0
    report_lines.append(f"**总体成功率**: {rate:.1f}%")
    report_lines.append("")
    
    report_lines.extend([
        "---",
        "",
        "## 二、各智能体状态概览",
        "",
        "| 角色ID | 名称 | 任务数 | 成功 | 失败 | 成功率 | 状态 |",
        "|--------|------|--------|------|------|--------|------|",
    ])
    
    for role_id in sorted(all_results.keys()):
        role_data = all_results[role_id]
        name = role_data.get("name", role_id)
        tasks = role_data.get("tasks", [])
        total_t = len(tasks)
        success_t = sum(1 for t in tasks if t.get("success"))
        fail_t = total_t - success_t
        rate_t = (success_t / total_t * 100) if total_t > 0 else 0
        status = "[OK]" if rate_t >= 50 else "[FAIL]"
        report_lines.append(f"| {role_id} | {name} | {total_t} | {success_t} | {fail_t} | {rate_t:.0f}% | {status} |")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 三、典型产出示例",
        "",
    ])
    
    # 展示一些成功的产出
    examples_shown = 0
    for role_id, role_data in all_results.items():
        for task in role_data.get("tasks", []):
            if task.get("success") and task.get("parsed"):
                if examples_shown < 3:
                    skill = task.get("skill", "?")
                    action = task.get("action", "?")
                    desc = task.get("description", "")
                    parsed = task.get("parsed", {})
                    
                    report_lines.extend([
                        f"### {role_id} - {skill}/{action}",
                        "",
                        f"**描述**: {desc}",
                        "",
                        "**产出**:",
                        "```json",
                        json.dumps(parsed, ensure_ascii=False, indent=2)[:500],
                        "```",
                        "",
                    ])
                    examples_shown += 1
    
    report_lines.extend([
        "---",
        "",
        "## 四、问题分析与建议",
        "",
        "### 主要问题",
        "",
        "1. **输入数据格式不匹配**: 部分任务的输入不符合技能预期的schema",
        "2. **必填字段缺失**: 任务卡等复杂结构缺少必要的字段",
        "3. **参数范围越界**: 某些数值参数超出允许范围",
        "",
        "### 改进建议",
        "",
        "1. **标准化输入模板**: 为每个技能建立标准的输入模板",
        "2. **增强错误提示**: 提供更详细的错误信息和修复建议",
        "3. **自动化测试**: 建立完整的自动化测试流程",
        "",
        "---",
        "",
        "## 五、附录",
        "",
        f"- 执行结果: `{os.path.join(OUTPUT_DIR, 'execution_summary.json')}`",
        f"- 报告目录: `{REPORT_DIR}`",
        "",
        f"*报告生成时间: {datetime.now().isoformat()}*",
    ])
    
    return "\n".join(report_lines)


def main():
    print("=" * 80)
    print("生成能力产出报告和诊断报告")
    print("=" * 80)
    
    results = load_execution_results()
    all_results = results.get("results", {})
    
    # 生成总体汇总
    print("\n生成总体汇总报告...")
    overall_report = generate_overall_summary(results)
    overall_file = os.path.join(REPORT_DIR, "00_总体能力校验报告.md")
    with open(overall_file, "w", encoding="utf-8") as f:
        f.write(overall_report)
    print(f"  保存: {overall_file}")
    
    # 为每个智能体生成报告
    print("\n生成各智能体报告...")
    for role_id, role_data in sorted(all_results.items()):
        name = role_data.get("name", role_id)
        print(f"  {role_id} - {name}...")
        
        # 能力产出报告
        capability_report = generate_capability_output_report(role_id, role_data)
        cap_file = os.path.join(REPORT_DIR, f"{role_id}_{name}_能力产出报告.md")
        with open(cap_file, "w", encoding="utf-8") as f:
            f.write(capability_report)
        
        # 诊断报告
        diag_report = generate_agent_diagnostic_report(role_id, role_data)
        diag_file = os.path.join(REPORT_DIR, f"{role_id}_{name}_诊断报告.md")
        with open(diag_file, "w", encoding="utf-8") as f:
            f.write(diag_report)
    
    print(f"\n{'='*80}")
    print("报告生成完成!")
    print(f"报告目录: {REPORT_DIR}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
