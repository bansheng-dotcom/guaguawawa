# -*- coding: utf-8 -*-
"""DSH 深度集成：在 DSH 主 Agent 中通过 subagent 调用 r01，自动完成知识注入。

使用方式：
    from agents.shared.dsh_integration import DSHKnowledgeInjector

    injector = DSHKnowledgeInjector()
    result = injector.inject_and_call(
        role_id="r01",
        intent="我们是否应该冻结定价90天？",
        llm_client=your_llm_client,
    )
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from agents.shared.knowledge_base import KnowledgeBase, create_r01_knowledge_base


class DSHKnowledgeInjector:
    """DSH 知识注入器：自动加载角色配置、构建 system prompt、调用 LLM。"""

    def __init__(self, config_dir: str = "agents/configs"):
        """初始化注入器。

        Args:
            config_dir: 角色配置目录（agents/configs/*.yaml）
        """
        self.config_dir = config_dir
        self._kb_cache: Dict[str, KnowledgeBase] = {}

    def _load_role_config(self, role_id: str) -> Dict[str, Any]:
        """加载角色配置（YAML）。"""
        config_path = os.path.join(self.config_dir, f"{role_id}.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"角色配置不存在: {config_path}")
        import yaml
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_kb(self, role_id: str) -> KnowledgeBase:
        """获取角色知识基座（带缓存）。"""
        if role_id in self._kb_cache:
            return self._kb_cache[role_id]

        config = self._load_role_config(role_id)
        _agents_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            from core import registry
            r = registry.by_id(role_id)
            role_dir = os.path.join(_agents_dir, r["dir"])
        except Exception:
            matched = [d for d in os.listdir(_agents_dir) if d.startswith(role_id)]
            role_dir = os.path.join(_agents_dir, matched[0]) if matched else os.path.join(_agents_dir, role_id)

        kb = KnowledgeBase(
            role_dir=role_dir,
            knowledge_map=config["knowledge_map"],
            role_name=config["role_name"],
            role_title=config["role_title"],
            core_duties=config["core_duties"],
            key_principles=config["key_principles"],
            output_requirements=config["output_requirements"],
            language=config.get("language", "zh"),
            enable_cache=config.get("enable_cache", True),
            enable_vector=config.get("enable_vector", False),
        )
        self._kb_cache[role_id] = kb
        return kb

    def inject_and_call(
        self,
        role_id: str,
        intent: str,
        llm_client: Any,
        domains: Optional[List[str]] = None,
        use_vector: bool = False,
        incremental: bool = False,
        last_hash: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """注入知识并调用 LLM。

        Args:
            role_id: 角色 ID（如 "r01"）
            intent: 用户意图
            llm_client: LLM 客户端（需实现 chat(system, user) 方法）
            domains: 手动指定知识域（None=自动推断）
            use_vector: 是否使用向量检索
            incremental: 是否启用增量加载
            last_hash: 上次加载的 hash 映射

        Returns:
            {
                "response": str,           # LLM 原始响应
                "parsed": Dict,            # 解析后的 JSON
                "domains": List[str],      # 实际加载的知识域
                "sources": List[Dict],     # 知识来源（含 hash）
                "changed": List[str],      # 增量加载时变更的文件
            }
        """
        kb = self._get_kb(role_id)
        config = self._load_role_config(role_id)

        # 1. 自动推断知识域
        if domains is None:
            domains = kb.get_domain_for_intent(
                intent, config["keyword_map"], use_vector=use_vector
            )

        # 2. 构建 system prompt
        prompt = kb.build_system_prompt(
            domains=domains,
            task_context=intent,
            incremental=incremental,
            last_hash=last_hash,
        )

        # 3. 调用 LLM
        response = llm_client.chat(system=prompt, user=intent)

        # 4. 解析结果
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = {"raw_response": response}

        # 5. 返回完整结果
        knowledge = kb.load_knowledge(domains=domains, incremental=incremental, last_hash=last_hash)
        return {
            "response": response,
            "parsed": parsed,
            "domains": domains,
            "sources": knowledge["sources"],
            "changed": knowledge["changed"],
        }


# --------------------------------------------------------------------------- #
# 简化版：无需 YAML 配置，直接使用 R01
# --------------------------------------------------------------------------- #
def quick_inject_r01(
    intent: str,
    llm_client: Any,
    domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """快速注入 R01 知识并调用 LLM（无需 YAML 配置）。

    Args:
        intent: 用户意图
        llm_client: LLM 客户端
        domains: 手动指定知识域

    Returns:
        同 DSHKnowledgeInjector.inject_and_call
    """
    kb = create_r01_knowledge_base("agents/r01-waquanju-ceo")
    if domains is None:
        from agents.shared.knowledge_base import R01_CONFIG
        domains = kb.get_domain_for_intent(intent, R01_CONFIG["keyword_map"])
    prompt = kb.build_system_prompt(domains=domains, task_context=intent)
    response = llm_client.chat(system=prompt, user=intent)
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        parsed = {"raw_response": response}
    return {
        "response": response,
        "parsed": parsed,
        "domains": domains,
        "sources": kb.load_knowledge(domains=domains)["sources"],
    }
