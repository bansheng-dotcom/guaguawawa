# -*- coding: utf-8 -*-
"""R01 知识注入层：把 references/ + experience/ + cases/ 升级为 LLM 可调用的知识基座。

设计原则：
  - 按需加载：LLM 调用前才读文件，不常驻内存
  - 结构化注入：按能力域组织，支持选择性注入（避免 context 爆炸）
  - 版本可追溯：每次注入记录文件 hash，便于审计
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))


def _file_hash(path: str) -> str:
    """计算文件 MD5 前 8 位，用于版本追踪。"""
    if not os.path.exists(path):
        return ""
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:8]


def _load_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------------- #
# 知识域映射：能力域 → 关联的 references 文件
# --------------------------------------------------------------------------- #
KNOWLEDGE_MAP: Dict[str, List[str]] = {
    "intent": ["references/01-vision-intent.md"],
    "decompose": ["references/02-orchestration-decomposition.md"],
    "decide": ["references/03-hard-decisions.md"],
    "redteam": ["references/03-hard-decisions.md"],
    "companyos": ["references/04-company-os.md"],
    "decisionlog": ["references/04-company-os.md"],
    "boardroom": ["references/04-company-os.md"],
    "governance": ["references/05-governance-audit.md"],
    "charter": ["references/00-capability-charter.md"],
}


def load_knowledge(
    domains: Optional[List[str]] = None,
    include_charter: bool = True,
    include_thresholds: bool = True,
    include_cases: bool = False,
) -> Dict[str, Any]:
    """按需加载知识域，返回结构化知识包。

    Args:
        domains: 要加载的能力域列表（如 ["decide", "redteam"]），None=全部
        include_charter: 是否包含角色能力说明书（00-capability-charter.md）
        include_thresholds: 是否加载 experience/thresholds.json
        include_cases: 是否加载案例库（pricing-freeze / quarterly-boardroom）

    Returns:
        {
            "knowledge_text": str,      # 拼接后的 Markdown 文本（供 LLM system prompt）
            "sources": List[Dict],      # 每份文件的元信息（路径/hash/域）
            "thresholds": Dict,         # 业务阈值（如 include_thresholds=True）
            "cases": List[Dict],        # 案例摘要（如 include_cases=True）
        }
    """
    if domains is None:
        domains = list(KNOWLEDGE_MAP.keys())

    sources: List[Dict[str, Any]] = []
    texts: List[str] = []

    # 1. 加载能力说明书（全局）
    if include_charter:
        path = os.path.join(_HERE, "references", "00-capability-charter.md")
        text = _load_text(path)
        if text:
            sources.append({
                "path": "references/00-capability-charter.md",
                "domain": "charter",
                "hash": _file_hash(path),
            })
            texts.append(f"# 角色能力说明书\n\n{text}")

    # 2. 按域加载 references
    loaded_files = set()
    for domain in domains:
        for rel_path in KNOWLEDGE_MAP.get(domain, []):
            if rel_path in loaded_files:
                continue
            loaded_files.add(rel_path)
            path = os.path.join(_HERE, rel_path)
            text = _load_text(path)
            if text:
                sources.append({
                    "path": rel_path,
                    "domain": domain,
                    "hash": _file_hash(path),
                })
                texts.append(f"# {domain} 知识域\n\n{text}")

    # 3. 加载阈值配置
    thresholds: Dict[str, Any] = {}
    if include_thresholds:
        from skills import _common as c
        thresholds = c.load_thresholds()
        sources.append({
            "path": "experience/thresholds.json",
            "domain": "thresholds",
            "hash": _file_hash(c.thresholds_path()),
        })

    # 4. 加载案例库
    cases: List[Dict[str, Any]] = []
    if include_cases:
        import cases as cases_module
        for case_info in cases_module.list_cases():
            case_id = case_id if isinstance(case_id, str) else case_id.get("case_id")
            case_data = cases_module.load_case(case_id)
            cases.append({
                "case_id": case_id,
                "display_name": case_data.get("display_name", ""),
                "description": case_data.get("description", ""),
                "default_question": case_data.get("default_question", ""),
            })

    knowledge_text = "\n\n---\n\n".join(texts)

    return {
        "knowledge_text": knowledge_text,
        "sources": sources,
        "thresholds": thresholds,
        "cases": cases,
    }


def build_system_prompt(
    domains: Optional[List[str]] = None,
    task_context: Optional[str] = None,
) -> str:
    """构建 LLM system prompt：角色定位 + 知识注入 + 任务上下文。

    Args:
        domains: 要注入的知识域（如 ["decide", "redteam"]），None=全部
        task_context: 当前任务上下文（如用户输入的意图描述）

    Returns:
        完整的 system prompt 字符串
    """
    knowledge = load_knowledge(domains=domains, include_charter=True)

    prompt_parts = [
        "你是 R01 蛙全局 · CEO 主理人 / 编排器。",
        "",
        "## 核心职责",
        "- 把创始人的一句话意图变成有主责、有验收、有终止条件的任务卡",
        "- 收口成一份能签字的决策汇报",
        "- 不替专业部门干活，也不替创始人签字",
        "",
        "## 关键原则",
        "- 不可逆动作必须创始人授权（签约/扣款/裁员等）",
        "- 先锁标准再谈实现（成功/杀死标准先于决策写）",
        "- 上下文隔离：子进程边界调用其它 Agent，不共享内存",
        "- 端口契约：跨角色交接只认 inputs/outputs",
        "",
        "## 知识基座",
        knowledge["knowledge_text"],
        "",
    ]

    if task_context:
        prompt_parts.extend([
            "## 当前任务上下文",
            task_context,
            "",
        ])

    prompt_parts.extend([
        "## 输出要求",
        "- 所有结论必须带成功/杀死标准",
        "- 所有建议必须标注可逆性等级",
        "- 涉及不可逆动作时必须声明 human_signoff_required",
        "- 使用结构化 JSON 输出，便于下游校验",
    ])

    return "\n".join(prompt_parts)


def get_domain_for_intent(intent: str) -> List[str]:
    """根据用户意图推断需要加载的知识域。

    简单的关键词匹配，未来可升级为 LLM 路由。
    """
    intent_lower = intent.lower()
    domains = []

    if any(k in intent_lower for k in ["简报", "brief", "澄清", "六问", "意图", "分级"]):
        domains.append("intent")
    if any(k in intent_lower for k in ["拆解", "任务卡", "波次", "路由", "分工", "wbs"]):
        domains.append("decompose")
    if any(k in intent_lower for k in ["决策", "可逆", "拍板", "定夺", "升级"]):
        domains.append("decide")
    if any(k in intent_lower for k in ["质询", "反方", "红队", "魔鬼代言人", "交叉评估"]):
        domains.append("redteam")
    if any(k in intent_lower for k in ["公司os", "记分卡", "ids", "冷却", "freeze", "治理"]):
        domains.append("companyos")
    if any(k in intent_lower for k in ["决策日志", "留痕", "复盘", "retro"]):
        domains.append("decisionlog")
    if any(k in intent_lower for k in ["董事会", "汇报", "陪练", "board"]):
        domains.append("boardroom")

    # 默认加载 charter + governance（全局治理原则）
    if not domains:
        domains = ["charter", "governance"]

    return domains
