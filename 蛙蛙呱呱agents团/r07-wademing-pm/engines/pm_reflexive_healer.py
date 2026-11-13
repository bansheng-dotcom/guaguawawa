# -*- coding: utf-8 -*-
"""engines/pm_reflexive_healer.py - L03 自愈反思与边界审判层 (PM Reflexive Healing & Boundary Critic).

对标开源标杆：Reflexion / Critic-Agent / OpenHands
核心职责：
1. 自愈反思修复 (Reflexive Auto-Healing)：
   - 自动检测并补全缺失的验收标准 (Gherkin 结构：Given/When/Then)；
   - 自动检测并补齐缺失的成败量化门禁与北极星指标 (Success/Guardrail Metrics)；
   - 补全不足 3 个的承重假设 (Core Assumptions)。
2. 严厉拦截 PM 三大越界红线 (Boundary Critic Interception)：
   - 红线 1: "拍板决策" (越界擅自拍板高风险决策，而非提供数据依据交由业务负责人裁定)；
   - 红线 2: "越界写代码 / 越界技术选型" (PM 越俎代庖替研发指定底层代码库或类库实现细节)；
   - 红线 3: "虚荣指标" (以注册量、累计下载量等无行为沉淀的 vanity metrics 冒充核心成功指标)。
3. 提供自愈与批评日志 (Reflection Trail)，确保每次干预均有据可查。
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Tuple


class PMReflexiveHealer:
    """R07 L03 自愈反思与产品边界红线审判器。"""

    # 红线关键词拦截模式
    REDLINE_DECISION_PATTERNS = [
        re.compile(r"拍板决定"),
        re.compile(r"我已拍板"),
        re.compile(r"无需审批立即执行"),
        re.compile(r"擅自拍板"),
        re.compile(r"由我最终裁决"),
    ]

    REDLINE_CODE_PATTERNS = [
        re.compile(r"必须使用\s*(?:React|Vue|Spring|Django|Go|Rust)\s*(?:重写|编写|实现)"),
        re.compile(r"越界写代码"),
        re.compile(r"底层采用\s*(?:B\+树|红黑树|协程池|Redis分布式锁)"),
        re.compile(r"指定代码实现细节"),
    ]

    VANITY_METRIC_KEYWORDS = [
        "注册用户数", "总注册量", "下载量", "安装量", "pv", "页面曝光量", "访问次数", "总pv"
    ]

    def __init__(self):
        self.reflection_logs: List[Dict[str, Any]] = []

    def audit_redlines(self, doc_data: Dict[str, Any]) -> List[str]:
        """全量审计是否存在触碰 PM 职业边界与伦理红线的问题。"""
        violations: List[str] = []
        raw_text = str(doc_data)

        # 1. 检查拍板决策越界
        for pat in self.REDLINE_DECISION_PATTERNS:
            if pat.search(raw_text):
                violations.append(f"触犯边界红线 [拍板决策]: 产品经理不可擅自替代决策层拍板裁定，检测到敏感表述: '{pat.pattern}'")

        # 2. 检查越界写代码/技术实现指定
        for pat in self.REDLINE_CODE_PATTERNS:
            if pat.search(raw_text):
                violations.append(f"触犯边界红线 [越界技术实现]: 产品经理不可越权指定代码细节或强制底层技术选型，检测到: '{pat.pattern}'")

        # 3. 检查虚荣指标冒充成功指标
        metrics = doc_data.get("metrics", {})
        if isinstance(metrics, dict):
            ns = str(metrics.get("north_star", "")).lower()
            target = str(metrics.get("target", "")).lower()
            for v_kw in self.VANITY_METRIC_KEYWORDS:
                if v_kw in ns:
                    violations.append(f"触犯边界红线 [虚荣指标]: 北极星指标不可采用无转化沉淀的虚荣指标 '{v_kw}'，应采用留存/激活/LTV等真实价值指标")

        return violations

    def audit_and_heal(self, doc_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """对 PRD / 用户故事 / 决策卡进行全量门禁自愈修复并输出审计报告。"""
        healed_data = copy.deepcopy(data)
        actions_taken: List[str] = []

        # 1. 红线审查
        redline_violations = self.audit_redlines(healed_data)

        # 自动清洗违规拍板用语
        if redline_violations:
            text_fields = ["executive_summary", "decision", "summary", "problem_statement"]
            for f in text_fields:
                if f in healed_data and isinstance(healed_data[f], str):
                    for pat in self.REDLINE_DECISION_PATTERNS:
                        if pat.search(healed_data[f]):
                            healed_data[f] = pat.sub("提交业务委员会评审决策", healed_data[f])
                            actions_taken.append(f"自动修复字段 '{f}' 中越界拍板表述为合规决策流")

        # 2. 结构自愈与缺失门禁补全
        if doc_type in ("prd", "feature-prd"):
            # 2.1 补全验收标准 (Given/When/Then)
            ac_list = healed_data.get("acceptance_criteria", [])
            if not ac_list or not isinstance(ac_list, list):
                ac_list = []

            # 检查是否有合规的 Gherkin
            has_valid_gherkin = False
            for ac in ac_list:
                if isinstance(ac, dict) and ("given" in ac or ("text" in ac and "given" in ac["text"].lower())):
                    has_valid_gherkin = True
                    break

            if not has_valid_gherkin or len(ac_list) < 2:
                default_acs = [
                    {
                        "given": "用户已通过身份验证进入功能页面",
                        "when": "用户触发核心业务操作并提交",
                        "then": "系统在 500ms 内反馈处理结果并正确持久化数据",
                    },
                    {
                        "given": "网络异常或入参不合法",
                        "when": "用户提交表单",
                        "then": "系统给出友好提示并保留用户当前已填写数据",
                    },
                ]
                ac_list.extend(default_acs)
                healed_data["acceptance_criteria"] = ac_list
                actions_taken.append(f"自愈补全缺失/不足的标准 Gherkin 验收条件 (新增 {len(default_acs)} 条)")

            # 2.2 补全成功指标与防虚荣保底
            metrics = healed_data.get("metrics")
            if not metrics or not isinstance(metrics, dict):
                healed_data["metrics"] = {
                    "north_star": "7日核心功能使用留存率",
                    "input_metrics": ["首日功能完成率", "平均操作耗时"],
                    "guardrail": ["用户流失率", "系统报错率"],
                    "baseline": "15%",
                    "target": "25%",
                    "data_source": "业务埋点系统",
                }
                actions_taken.append("自愈补齐缺失的完整量化度量指标 (NorthStar/Input/Guardrail)")
            else:
                if not metrics.get("north_star") or any(v in str(metrics.get("north_star")) for v in self.VANITY_METRIC_KEYWORDS):
                    metrics["north_star"] = "7日活跃用户功能采纳留存率"
                    actions_taken.append("自愈替换/修正虚荣指标为有效北极星留存指标")
                if not metrics.get("guardrail"):
                    metrics["guardrail"] = ["核心链路报错率 < 0.1%", "客诉率不上升"]
                    actions_taken.append("自愈补齐防护护栏指标 (guardrail metrics)")

            # 2.3 补全承重假设 (至少 3 个)
            assumptions = healed_data.get("assumptions", healed_data.get("risks", []))
            if not isinstance(assumptions, list):
                assumptions = []
            if len(assumptions) < 3:
                needed = 3 - len(assumptions)
                default_assumptions = [
                    {"hypothesis": "目标客群对该痛点具有强烈的自主解决意愿", "validation": "小流量灰度访谈"},
                    {"hypothesis": "核心交互流程不会显著增加用户认知负荷", "validation": "可用性测试"},
                    {"hypothesis": "功能上线后能够形成可持续的正向留存闭环", "validation": "A/B 增量实验"},
                ]
                assumptions.extend(default_assumptions[:needed])
                healed_data["assumptions"] = assumptions
                if "risks" in healed_data:
                    healed_data["risks"] = assumptions
                actions_taken.append(f"自愈补足承重风险假设至 3 项 (补入 {needed} 项)")

            # 2.4 补全遥测埋点
            if not healed_data.get("telemetry"):
                healed_data["telemetry"] = [
                    {"event": "feature_view", "desc": "功能页面曝光"},
                    {"event": "feature_action_click", "desc": "核心操作点击"},
                    {"event": "feature_complete_success", "desc": "核心流程完成"},
                ]
                actions_taken.append("自愈补齐底层基础行为遥测与埋点规格 (telemetry)")

        elif doc_type == "story":
            ac = healed_data.get("acceptance_criteria", [])
            if len(ac) < 4:
                needed = 4 - len(ac)
                default_story_acs = [
                    {"text": "Given 用户未满足前置条件 When 触发操作 Then 提示前置阻断原因"},
                    {"text": "Given 网络延时超时 When 用户点击 Then 显示加载态且防止重复点击"},
                    {"text": "Given 正常提交 When 服务端成功返回 Then 状态变更为已完成并刷新列表"},
                    {"text": "Given 权限不足 When 尝试访问 Then 阻断并引导联系管理员申请权限"},
                ]
                ac.extend(default_story_acs[:needed])
                healed_data["acceptance_criteria"] = ac
                actions_taken.append(f"自愈补全不足 4 条的用户故事验收标准 (补入 {needed} 条)")

        is_clean = len(self.audit_redlines(healed_data)) == 0
        return {
            "ok": is_clean,
            "layer": "L03",
            "healed_data": healed_data,
            "actions_taken": actions_taken,
            "redline_violations_initial": redline_violations,
            "redline_violations_remaining": self.audit_redlines(healed_data),
            "is_healed": len(actions_taken) > 0,
        }
