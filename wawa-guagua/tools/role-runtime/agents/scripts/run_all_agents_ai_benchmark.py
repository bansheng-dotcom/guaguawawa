#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量智能体运行脚本 - AI主题任务生成与执行

为20个智能体生成AI主题的随机任务和数据集，执行每个智能体的能力域测试，
收集结果并生成诊断报告。
"""
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# 配置
AGENTS_ROOT = r"D:\一人公司\agents"
WORKSPACE_ROOT = os.path.join(AGENTS_ROOT, "workspace")
REPORT_DIR = os.path.join(WORKSPACE_ROOT, "ai_benchmark_reports")
PYTHON_EXE = sys.executable

# 确保报告目录存在
os.makedirs(REPORT_DIR, exist_ok=True)

# AI主题任务模板 - 按角色定制
AI_TASK_TEMPLATES = {
    "r01": {
        "name": "蛙全局",
        "title": "CEO 主理人 / 编排器",
        "tasks": [
            {"skill": "intent", "action": "brief", "desc": "AI产品战略意图识别"},
            {"skill": "decompose", "action": "taskcard", "desc": "AI项目跨部门拆解"},
            {"skill": "decide", "action": "card", "desc": "AI投资决策卡"},
            {"skill": "redteam", "action": "devil", "desc": "AI方案反方质询"},
            {"skill": "companyos", "action": "os", "desc": "AI公司治理OS"},
            {"skill": "decisionlog", "action": "entry", "desc": "AI决策留痕"},
            {"skill": "boardroom", "action": "memo", "desc": "AI董事会汇报"},
        ]
    },
    "r02": {
        "name": "蛙排布",
        "title": "COO 首席运营官",
        "tasks": [
            {"skill": "schedule", "action": "wbs", "desc": "AI项目WBS拆解"},
            {"skill": "capacity", "action": "check", "desc": "AI团队容量检查"},
            {"skill": "handoff", "action": "package", "desc": "AI交付物打包"},
            {"skill": "retro", "action": "postmortem", "desc": "AI事故复盘"},
            {"skill": "process", "action": "sop", "desc": "AI流程SOP"},
            {"skill": "knowledge", "action": "digest", "desc": "AI知识摘要"},
            {"skill": "portfolio", "action": "status", "desc": "AI项目群状态"},
        ]
    },
    "r03": {
        "name": "蛙守线",
        "title": "财务合规官 / 红线负责人",
        "tasks": [
            {"skill": "financial", "action": "rollforward", "desc": "AI财务报表结转"},
            {"skill": "cfo", "action": "runway", "desc": "AI公司Runway分析"},
            {"skill": "tax", "action": "iso", "desc": "AI税务ISO合规"},
            {"skill": "contract", "action": "scan", "desc": "AI合同扫描"},
            {"skill": "privacy", "action": "map", "desc": "AI隐私数据映射"},
            {"skill": "aigov", "action": "aiclassify", "desc": "AI系统分类"},
            {"skill": "audit", "action": "retention", "desc": "AI审计留存"},
            {"skill": "risk", "action": "kyc", "desc": "AI KYC风控"},
        ]
    },
    "r04": {
        "name": "蛙挑刺",
        "title": "独立评审官",
        "tasks": [
            {"skill": "verify", "action": "artifact", "desc": "AI产物核验"},
            {"skill": "gate", "action": "harness", "desc": "AI硬门禁复核"},
            {"skill": "criteria", "action": "external", "desc": "AI外置判据"},
            {"skill": "quality", "action": "score", "desc": "AI质量评价"},
            {"skill": "source", "action": "factcheck", "desc": "AI事实来源检查"},
            {"skill": "merit", "action": "preserve", "desc": "AI保留优点复评"},
            {"skill": "workflow", "action": "human", "desc": "AI人工评审工作流"},
        ]
    },
    "r05": {
        "name": "蛙深远",
        "title": "战略研究官",
        "tasks": [
            {"skill": "research", "action": "deep", "desc": "AI深度研究"},
            {"skill": "industry", "action": "scan", "desc": "AI行业扫描"},
            {"skill": "competitor", "action": "intel", "desc": "AI竞品情报"},
            {"skill": "business", "action": "model", "desc": "AI商业模式分析"},
            {"skill": "market", "action": "size", "desc": "AI市场规模测算"},
            {"skill": "macro", "action": "scenario", "desc": "AI宏观情景"},
            {"skill": "automation", "action": "pipeline", "desc": "AI研究自动化"},
        ]
    },
    "r06": {
        "name": "蛙得清",
        "title": "数据分析师",
        "tasks": [
            {"skill": "semantics", "action": "validate", "desc": "AI指标语义建模"},
            {"skill": "quality", "action": "audit", "desc": "AI数据清洗质检"},
            {"skill": "explore", "action": "trend", "desc": "AI趋势分析"},
            {"skill": "rootcause", "action": "drilldown", "desc": "AI根因贡献分解"},
            {"skill": "abtest", "action": "abtest", "desc": "AI A/B实验"},
            {"skill": "describe", "action": "describe", "desc": "AI描述统计"},
            {"skill": "viz", "action": "report", "desc": "AI可视化报告"},
            {"skill": "selfmedia", "action": "dashboard", "desc": "AI自媒体数据运营"},
        ]
    },
    "r07": {
        "name": "蛙得明",
        "title": "产品经理",
        "tasks": [
            {"skill": "discovery", "action": "jtbd", "desc": "AI产品发现JTBD"},
            {"skill": "research", "action": "opportunity", "desc": "AI机会树用户研究"},
            {"skill": "story", "action": "prd", "desc": "AI用户故事PRD"},
            {"skill": "priority", "action": "backlog", "desc": "AI优先级Backlog"},
            {"skill": "roadmap", "action": "release", "desc": "AI路线图发布"},
            {"skill": "vision", "action": "metrics", "desc": "AI愿景指标"},
            {"skill": "translate", "action": "code2prd", "desc": "AI代码反推PRD"},
            {"skill": "experience", "action": "retrieve", "desc": "AI经验检索"},
        ]
    },
    "r08": {
        "name": "蛙建成",
        "title": "产品实现官 (MVP)",
        "tasks": [
            {"skill": "slice", "action": "mvp", "desc": "AI产品切片MVP"},
            {"skill": "spec", "action": "repo", "desc": "AI Spec转仓库"},
            {"skill": "landing", "action": "h5", "desc": "AI落地页H5"},
            {"skill": "saas", "action": "email", "desc": "AI SaaS邮件脚手架"},
            {"skill": "crossplatform", "action": "prototype", "desc": "AI跨平台原型"},
            {"skill": "component", "action": "design", "desc": "AI组件设计实现"},
            {"skill": "quality", "action": "verify", "desc": "AI质量验证交接"},
        ]
    },
    "r09": {
        "name": "蛙稳码",
        "title": "代码工程官",
        "tasks": [
            {"skill": "arch", "action": "spec", "desc": "AI技术规格架构"},
            {"skill": "db", "action": "api", "desc": "AI数据库API"},
            {"skill": "fullstack", "action": "implement", "desc": "AI前后端全栈"},
            {"skill": "crossplatform", "action": "production", "desc": "AI跨端生产工程"},
            {"skill": "test", "action": "browser", "desc": "AI测试浏览器验证"},
            {"skill": "debug", "action": "performance", "desc": "AI调试性能重构"},
            {"skill": "migrate", "action": "cicd", "desc": "AI迁移CI/CD安全"},
            {"skill": "special", "action": "carrier", "desc": "AI特殊技术载体"},
        ]
    },
    "r10": {
        "name": "蛙成美",
        "title": "视觉设计官",
        "tasks": [
            {"skill": "aiimage", "action": "generate", "desc": "AI生图插画"},
            {"skill": "logo", "action": "vi", "desc": "AI Logo图标VI"},
            {"skill": "uiux", "action": "product", "desc": "AI产品UI/UX"},
            {"skill": "prototype", "action": "motion", "desc": "AI交互原型动效"},
            {"skill": "image", "action": "edit", "desc": "AI修图图像工程"},
            {"skill": "video", "action": "process", "desc": "AI视频音频处理"},
            {"skill": "transcribe", "action": "subtitle", "desc": "AI转写字幕"},
            {"skill": "dataviz", "action": "marketing", "desc": "AI数据视觉营销物料"},
        ]
    },
    "r11": {
        "name": "蛙点题",
        "title": "内容主笔",
        "tasks": [
            {"skill": "strategy", "action": "topic", "desc": "AI内容策略选题"},
            {"skill": "seo", "action": "aeo", "desc": "AI SEO/AEO优化"},
            {"skill": "hook", "action": "outline", "desc": "AI钩子提纲"},
            {"skill": "copy", "action": "longform", "desc": "AI文案长文"},
            {"skill": "tone", "action": "edit", "desc": "AI品牌语调编辑"},
            {"skill": "adpr", "action": "press", "desc": "AI广告公关"},
            {"skill": "multiplatform", "action": "adapt", "desc": "AI多平台适配"},
            {"skill": "localization", "action": "continuous", "desc": "AI持续本地化"},
        ]
    },
    "r12": {
        "name": "蛙引流",
        "title": "增长运营官",
        "tasks": [
            {"skill": "diagnosis", "action": "baseline", "desc": "AI增长诊断基线"},
            {"skill": "loop", "action": "organic", "desc": "AI增长循环自然获客"},
            {"skill": "coldstart", "action": "outreach", "desc": "AI冷启动外联"},
            {"skill": "influencer", "action": "collab", "desc": "AI红人合作增长"},
            {"skill": "aso", "action": "publish", "desc": "AI ASO发布"},
            {"skill": "paid", "action": "cro", "desc": "AI付费投放CRO"},
            {"skill": "activation", "action": "retention", "desc": "AI激活留存推荐"},
            {"skill": "attribution", "action": "revops", "desc": "AI归因RevOps"},
            {"skill": "selfmedia", "action": "operation", "desc": "AI自媒体运营"},
        ]
    },
    "r13": {
        "name": "蛙客成",
        "title": "客户成功与销售运营官",
        "tasks": [
            {"skill": "contact", "action": "manage", "desc": "AI客户与联系人管理"},
            {"skill": "pipeline", "action": "sales", "desc": "AI销售管道"},
            {"skill": "activity", "action": "followup", "desc": "AI销售活动与跟进"},
            {"skill": "omnichannel", "action": "support", "desc": "AI全渠道客服"},
            {"skill": "voc", "action": "feedback", "desc": "AI客户反馈VOC"},
            {"skill": "health", "action": "renewal", "desc": "AI客户健康续约"},
            {"skill": "knowledge", "action": "escalation", "desc": "AI服务知识与升级"},
            {"skill": "automation", "action": "interface", "desc": "AI客户运营自动化接口"},
        ]
    },
    "r14": {
        "name": "蛙交易",
        "title": "交易与收入履约官",
        "tasks": [
            {"skill": "ecommerce", "action": "backend", "desc": "AI商品电商后端"},
            {"skill": "subscription", "action": "metering", "desc": "AI订阅计量计费"},
            {"skill": "payment", "action": "integrate", "desc": "AI支付集成"},
            {"skill": "esign", "action": "audit", "desc": "AI电子签审计"},
            {"skill": "appointment", "action": "service", "desc": "AI服务预约"},
            {"skill": "orchestration", "action": "status", "desc": "AI交易状态编排"},
            {"skill": "revenue", "action": "data", "desc": "AI收入数据接口"},
            {"skill": "automation", "action": "transaction", "desc": "AI交易自动化接口"},
        ]
    },
    "r15": {
        "name": "蛙供应",
        "title": "ERP 与供应链运营官",
        "tasks": [
            {"skill": "procurement", "action": "supplier", "desc": "AI采购供应商"},
            {"skill": "inventory", "action": "warehouse", "desc": "AI库存仓库"},
            {"skill": "fulfillment", "action": "sales", "desc": "AI销售履约记录"},
            {"skill": "production", "action": "resource", "desc": "AI生产服务资源"},
            {"skill": "erp", "action": "finance", "desc": "AI ERP财务接口"},
            {"skill": "masterdata", "action": "permission", "desc": "AI主数据权限"},
            {"skill": "report", "action": "operation", "desc": "AI运营报表"},
        ]
    },
    "r16": {
        "name": "蛙人事",
        "title": "人员与组织运营官",
        "tasks": [
            {"skill": "recruitment", "action": "onboard", "desc": "AI招聘与入职"},
            {"skill": "personnel", "action": "contract", "desc": "AI人员与合同档案"},
            {"skill": "attendance", "action": "leave", "desc": "AI考勤与休假"},
            {"skill": "performance", "action": "goal", "desc": "AI绩效与目标"},
            {"skill": "compensation", "action": "prepare", "desc": "AI薪酬准备"},
            {"skill": "expense", "action": "benefit", "desc": "AI费用与福利业务"},
            {"skill": "org", "action": "report", "desc": "AI组织运营报表"},
        ]
    },
    "r17": {
        "name": "蛙织网",
        "title": "自动化与集成工程师",
        "tasks": [
            {"skill": "saas", "action": "api", "desc": "AI SaaS/API集成"},
            {"skill": "webhook", "action": "event", "desc": "AI Webhook事件"},
            {"skill": "mapping", "action": "identity", "desc": "AI字段身份映射"},
            {"skill": "batch", "action": "scheduled", "desc": "AI定时批处理"},
            {"skill": "approval", "action": "human", "desc": "AI人工审批"},
            {"skill": "retry", "action": "failure", "desc": "AI失败重试"},
            {"skill": "aiworkflow", "action": "pipeline", "desc": "AI工作流"},
            {"skill": "audit", "action": "log", "desc": "AI审计日志"},
        ]
    },
    "r18": {
        "name": "蛙数仓",
        "title": "数据工程与管道官",
        "tasks": [
            {"skill": "elt", "action": "connect", "desc": "AI数据连接ELT"},
            {"skill": "warehouse", "action": "transform", "desc": "AI数仓转换"},
            {"skill": "pipeline", "action": "schedule", "desc": "AI管道调度"},
            {"skill": "quality", "action": "gate", "desc": "AI数据质量门禁"},
            {"skill": "incremental", "action": "batchstream", "desc": "AI批流增量"},
            {"skill": "catalog", "action": "metadata", "desc": "AI数据目录"},
            {"skill": "ops", "action": "approval", "desc": "AI人工审批运维"},
        ]
    },
    "r19": {
        "name": "蛙智模",
        "title": "模型工程与 AI 评估官",
        "tasks": [
            {"skill": "experiment", "action": "track", "desc": "AI实验追踪"},
            {"skill": "registry", "action": "version", "desc": "AI模型注册与版本"},
            {"skill": "evaluation", "action": "dataset", "desc": "AI评估数据集与评分器"},
            {"skill": "trace", "action": "debug", "desc": "AI Agent Trace与调试"},
            {"skill": "regression", "action": "candidate", "desc": "AI回归与发布候选"},
            {"skill": "monitor", "action": "interface", "desc": "AI模型监控接口"},
            {"skill": "asset", "action": "documentation", "desc": "AI模型资产说明"},
        ]
    },
    "r20": {
        "name": "蛙值守",
        "title": "可靠性与恢复官",
        "tasks": [
            {"skill": "availability", "action": "monitor", "desc": "AI可用性监控"},
            {"skill": "alert", "action": "escalation", "desc": "AI告警升级"},
            {"skill": "statuspage", "action": "communication", "desc": "AI状态页沟通"},
            {"skill": "backup", "action": "encrypted", "desc": "AI加密增量备份"},
            {"skill": "recovery", "action": "drill", "desc": "AI恢复演练"},
            {"skill": "disaster", "action": "rollback", "desc": "AI灾难恢复回滚"},
            {"skill": "retro", "action": "operation", "desc": "AI运行复盘"},
        ]
    },
}


def generate_ai_dataset(role_id: str, task: Dict[str, Any]) -> str:
    """为指定角色和任务生成AI主题的测试数据集"""
    dataset_dir = os.path.join(REPORT_DIR, "datasets", role_id)
    os.makedirs(dataset_dir, exist_ok=True)
    
    # 根据技能类型生成不同的数据集
    skill = task["skill"]
    action = task["action"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if role_id == "r06":
        # 数据分析师 - 生成CSV数据
        csv_path = os.path.join(dataset_dir, f"{skill}_{action}_{timestamp}.csv")
        rows = ["order_id,date,channel,amount,status,user_id,ai_score"]
        channels = ["抖音", "微信", "小红书", "知乎", "B站"]
        statuses = ["浏览", "加购", "支付", "退款"]
        for i in range(50):
            date = f"2026-11-{random.randint(1, 30):02d}"
            channel = random.choice(channels)
            amount = round(random.uniform(10, 1000), 2) if random.random() > 0.1 else ""
            status = random.choice(statuses)
            ai_score = round(random.uniform(0, 1), 3)
            rows.append(f"O{i:04d},{date},{channel},{amount},{status},U{i:03d},{ai_score}")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("\n".join(rows))
        return csv_path
    
    elif role_id == "r03":
        # CFO - 生成JSON配置
        json_path = os.path.join(dataset_dir, f"{skill}_{action}_{timestamp}.json")
        data = {
            "system": {
                "practices": ["credit_scoring", "automated_decision"],
                "conformity_assessment": True,
                "human_oversight": True,
                "ai_model_version": "v2.1.0",
                "deployment_date": "2026-11-01"
            },
            "financial_metrics": {
                "monthly_revenue": random.randint(100000, 500000),
                "burn_rate": random.randint(50000, 150000),
                "runway_months": round(random.uniform(6, 24), 1)
            }
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return json_path
    
    else:
        # 通用JSON输入
        json_path = os.path.join(dataset_dir, f"{skill}_{action}_{timestamp}.json")
        data = {
            "intent": f"AI{task['desc']}",
            "context": {
                "domain": "artificial_intelligence",
                "priority": random.choice(["high", "medium", "low"]),
                "deadline": "2026-12-31",
                "stakeholders": ["CTO", "Product", "Engineering"]
            },
            "parameters": {
                "scope": "enterprise",
                "budget_range": f"${random.randint(10000, 100000)}-${random.randint(100000, 500000)}",
                "timeline_weeks": random.randint(4, 16)
            }
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return json_path


def run_agent_skill(role_id: str, skill: str, action: str, input_file: str) -> Dict[str, Any]:
    """运行单个智能体技能并返回结果"""
    agent_py = os.path.join(AGENTS_ROOT, f"r{role_id[1:]}-*", "agent.py")
    
    # 查找实际的agent.py路径
    import glob
    agent_files = glob.glob(os.path.join(AGENTS_ROOT, f"r{role_id[1:]}-*", "agent.py"))
    if not agent_files:
        return {"error": f"Agent not found for {role_id}", "exit_code": -1}
    
    agent_py = agent_files[0]
    
    cmd = [PYTHON_EXE, agent_py, skill, action, "--input", input_file]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            cwd=os.path.dirname(agent_py)
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        output = result.stdout or ""
        stderr = result.stderr or ""
        
        # 解析 __AGENT_RESULT__ 标记
        parsed_result = None
        marker = "__AGENT_RESULT__ "
        if marker in output:
            for line in output.splitlines():
                if line.startswith(marker):
                    try:
                        parsed_result = json.loads(line[len(marker):])
                    except json.JSONDecodeError:
                        parsed_result = {"raw": line[len(marker):]}
                    break
        
        return {
            "exit_code": result.returncode,
            "elapsed_ms": elapsed_ms,
            "stdout": output[:2000],
            "stderr": stderr[:500],
            "parsed": parsed_result,
            "success": result.returncode == 0 and parsed_result is not None
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "Timeout after 60s",
            "exit_code": -2,
            "elapsed_ms": 60000,
            "success": False
        }
    except Exception as e:
        return {
            "error": str(e),
            "exit_code": -3,
            "elapsed_ms": int((time.time() - start_time) * 1000),
            "success": False
        }


def run_all_agents() -> Dict[str, Any]:
    """运行所有20个智能体的AI主题任务"""
    print("=" * 80)
    print("开始全量智能体AI主题基准测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    all_results = {}
    summary = {
        "total_agents": 0,
        "total_tasks": 0,
        "successful_tasks": 0,
        "failed_tasks": 0,
        "skipped_tasks": 0,
        "total_elapsed_ms": 0
    }
    
    for role_id, config in AI_TASK_TEMPLATES.items():
        print(f"\n{'='*60}")
        print(f"运行 {role_id} - {config['name']} ({config['title']})")
        print(f"{'='*60}")
        
        agent_results = {
            "role_id": role_id,
            "name": config["name"],
            "title": config["title"],
            "tasks": [],
            "summary": {"total": 0, "success": 0, "failed": 0, "skipped": 0}
        }
        
        for task in config["tasks"]:
            print(f"  [{task['skill']}/{task['action']}] {task['desc']}...", end=" ")
            
            # 生成测试数据集
            input_file = generate_ai_dataset(role_id, task)
            
            # 运行技能
            result = run_agent_skill(role_id, task["skill"], task["action"], input_file)
            
            task_result = {
                "skill": task["skill"],
                "action": task["action"],
                "description": task["desc"],
                "input_file": input_file,
                **result
            }
            
            agent_results["tasks"].append(task_result)
            agent_results["summary"]["total"] += 1
            
            if result.get("success"):
                agent_results["summary"]["success"] += 1
                summary["successful_tasks"] += 1
                print(f"[OK] ({result['elapsed_ms']}ms)")
            elif result.get("exit_code") == -1:
                agent_results["summary"]["skipped"] += 1
                summary["skipped_tasks"] += 1
                print("[SKIP]")
            else:
                agent_results["summary"]["failed"] += 1
                summary["failed_tasks"] += 1
                print(f"[FAIL] ({result.get('error', 'Unknown error')})")
            
            summary["total_tasks"] += 1
            summary["total_elapsed_ms"] += result.get("elapsed_ms", 0)
        
        all_results[role_id] = agent_results
        summary["total_agents"] += 1
    
    # 保存完整结果
    results_file = os.path.join(REPORT_DIR, "full_benchmark_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print("基准测试完成!")
    print(f"总智能体数: {summary['total_agents']}")
    print(f"总任务数: {summary['total_tasks']}")
    print(f"成功: {summary['successful_tasks']} | 失败: {summary['failed_tasks']} | 跳过: {summary['skipped_tasks']}")
    print(f"总耗时: {summary['total_elapsed_ms']}ms")
    print(f"结果文件: {results_file}")
    print(f"{'='*80}")
    
    return {"summary": summary, "results": all_results, "results_file": results_file}


if __name__ == "__main__":
    run_all_agents()
