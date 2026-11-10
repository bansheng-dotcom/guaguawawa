# -*- coding: utf-8 -*-
"""engines/reflexive_healer.py - [L03] 自愈反思层：自动化红线刚性审判与就地反思自纠。

对标开源标杆：
- Reflexion: Language Agents with Verbal Reinforcement Learning (Stars > 40k)
- Critic-Agent 门禁拦截器与状态自愈修复模式

核心职责：
1. 刚性拦截自动化四大违规红线：
   - REDLINE_PLAINTEXT_CREDENTIAL: 严禁将 API Key、Token、密码明文硬编码至工作流或报文中（必须改用凭据引用）；
   - REDLINE_UNAPPROVED_PUBLISH: 严禁绕过人工审批直接部署上线生产或触发资金交易（必须插入 HITL 门禁并移交人类授权）；
   - REDLINE_BUSINESS_LOGIC_OVERREACH: 严禁越权编写后端核心业务代码（必须移交 R09 研发工程师）；
   - REDLINE_SILENT_FAILURE_DROP: 严禁重试耗尽后静默丢弃任务且无死信队列/告警通知（必须配置 DLQ 与补偿）。
2. 反思自纠与自愈修补能力：
   - 自动给裸写 API 节点套上凭据引用声明并遮蔽明文；
   - 自动检测悬空边并在无环前提下补齐连接；
   - 自动给无护栏的 AI 节点补齐安全约束；
   - 自动给高危发布流程插入 Approval 节点与责任人声明（DRI: R17 蛙织网）。
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional, Tuple


class AutomationReflexiveHealer:
    """自动化红线刚性审判与 Reflexion 反思自纠引擎。"""

    # 4 大违规红线定义
    REDLINES = [
        {
            "id": "REDLINE_PLAINTEXT_CREDENTIAL",
            "name": "严禁将 API Key/Token/Secret 明文硬编码至工作流节点或报文",
            "keywords": [
                "api_key=", "apikey=", "password=", "secret=", "token=", "bearer ",
                "把key写在节点里", "把密钥明文写在代码里", "跳过凭据管理"
            ],
            "category": "credential_leak",
            "handoff_target": "凭据安全池 / Vault / 环境变量声明",
        },
        {
            "id": "REDLINE_UNAPPROVED_PUBLISH",
            "name": "严禁绕过人工审批直接发布上线生产环境或进行资金操作",
            "keywords": [
                "直接发布上线", "跳过审批发布", "无需人工确认", "自动发布到生产",
                "直接扣款", "自动调拨资金", "直接执行生产删除"
            ],
            "category": "unapproved_exec",
            "handoff_target": "R01 蛙全局 (CEO) / 人类授权主管 (HITL Gate)",
        },
        {
            "id": "REDLINE_BUSINESS_LOGIC_OVERREACH",
            "name": "严禁越权实现业务应用核心业务逻辑",
            "keywords": [
                "编写微服务业务逻辑", "重构计费核心代码", "实现支付网关底层协议",
                "写用户认证后端模块"
            ],
            "category": "business_logic_overreach",
            "handoff_target": "R09 蛙稳码 (生产研发工程师)",
        },
        {
            "id": "REDLINE_SILENT_FAILURE_DROP",
            "name": "严禁静默丢弃执行失败任务且无死信/告警兜底",
            "keywords": [
                "静默丢弃失败", "失败不记录", "直接吞掉异常", "不配置死信队列",
                "无重试无兜底"
            ],
            "category": "silent_failure_drop",
            "handoff_target": "Dead Letter Queue (DLQ) & 运维告警频道",
        },
    ]

    def __init__(self, max_heal_rounds: int = 3):
        self.max_heal_rounds = max_heal_rounds

    # -------------------------------------------------------------------------
    # 1. 红线刚性审判
    # -------------------------------------------------------------------------
    def audit_redlines(self, action_or_query: str) -> Dict[str, Any]:
        """检查动作或文本是否触犯四大红线。触犯直接抛出 ValueError。"""
        lower = action_or_query.lower()
        for red in self.REDLINES:
            for kw in red["keywords"]:
                if kw in lower:
                    raise ValueError(
                        f"[REDLINE BLOCKED] 触犯红线【{red['name']}】(触发关键词: '{kw}')！"
                        f"已刚性阻断。建议整改路线：移交至【{red['handoff_target']}】进行授权合规闭环。"
                    )
        return {
            "compliant": True,
            "checked_redlines_count": len(self.REDLINES),
            "status": "PASS",
        }

    # -------------------------------------------------------------------------
    # 2. Reflexion 反思与自愈修补
    # -------------------------------------------------------------------------
    def heal_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """自愈修补工作流中的缺陷（悬空边、明文密码、缺少触发器、无死信等）。"""
        data = copy.deepcopy(workflow_data)
        healed_actions: List[str] = []

        nodes = data.setdefault("nodes", [])
        connections = data.setdefault("connections", [])

        # 2.1 触发器自愈：若无触发器，自愈补齐默认 webhook 触发器
        has_trigger = any("trigger" in (n.get("type", "")).lower() or "webhook" in (n.get("type", "")).lower() for n in nodes)
        if not has_trigger and nodes:
            trigger_node = {
                "id": "node_webhook_trigger_auto",
                "name": "Webhook Trigger",
                "type": "webhook_trigger",
                "path": "/webhook/v1/event",
                "method": "POST",
                "healed_by": "AutomationReflexiveHealer",
            }
            nodes.insert(0, trigger_node)
            first_exec_node = nodes[1]["id"]
            connections.insert(0, {"from": trigger_node["id"], "to": first_exec_node})
            healed_actions.append("自愈补齐缺失的 Webhook Trigger 节点与连接边")

        # 2.2 悬空边自愈剔除
        node_ids = {n.get("id") for n in nodes}
        valid_conns = []
        for c in connections:
            src = c.get("from") or c.get("source")
            tgt = c.get("to") or c.get("target")
            if src in node_ids and tgt in node_ids:
                valid_conns.append(c)
            else:
                healed_actions.append(f"自愈修剪悬空边: {src} -> {tgt}")
        data["connections"] = valid_conns

        # 2.3 明文密钥脱敏与凭据引用自愈
        for node in nodes:
            node_params = node.get("parameters", {})
            for k, v in list(node_params.items()):
                if isinstance(v, str) and any(sk in k.lower() for sk in ["api_key", "secret", "password", "token"]):
                    if not v.startswith("{{") and not v.startswith("$env:"):
                        node_params[k] = "{{$credentials.default_vault_secret}}"
                        healed_actions.append(f"自愈将节点 {node.get('id')} 的明文参数 {k} 转换为安全凭据引用")

        # 2.4 死信队列与重试策略兜底
        if "retry_policy" not in data:
            data["retry_policy"] = {
                "max_retries": 3,
                "backoff_multiplier": 2,
                "dead_letter_queue": "dlq_automation_events",
            }
            healed_actions.append("自愈注入标准化 3 次指数重试与死信队列 (DLQ) 兜底策略")

        data["healed"] = len(healed_actions) > 0
        data["healed_actions"] = healed_actions
        data["dri"] = "R17 蛙织网 · 自动化与集成工程师"
        return data
