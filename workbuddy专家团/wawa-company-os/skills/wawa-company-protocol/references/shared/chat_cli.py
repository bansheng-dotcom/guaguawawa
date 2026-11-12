# -*- coding: utf-8 -*-
"""Reusable chat CLI helper for all agents r01-r20.

硬化点（META-001 Stage 3）：
    - 用 `__file__` 推导仓库根并注入 sys.path，不再依赖调用方的 cwd；
    - config 目录默认锚到 agents/configs 的**绝对路径**，异构 cwd 下也能找到；
    - 输出统一走 stdout 的 UTF-8 重配置，Windows 控制台不再乱码。
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_REPO = os.path.dirname(_AGENTS)
for _p in (_REPO, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents.shared.dsh_integration import DSHKnowledgeInjector


def add_chat_parser(subparsers: Any) -> Any:
    """在 argparse 的 subparsers 中注册统一的 chat 子命令。"""
    chat_p = subparsers.add_parser("chat", help="LLM 对话模式：注入知识基座后返回 system prompt")
    chat_p.add_argument("--intent", required=True, help="用户意图描述")
    chat_p.add_argument(
        "--domains",
        default=None,
        help="要注入的知识域（逗号分隔，如 schedule,capacity），默认自动推断",
    )
    chat_p.add_argument(
        "--output", default=None, help="输出 system prompt 到文件（默认打印到 stdout）"
    )
    chat_p.add_argument(
        "--vector", action="store_true", help="使用语义向量检索替代关键词匹配"
    )
    return chat_p


def handle_chat(args: argparse.Namespace, role_id: str, config_dir: Optional[str] = None) -> int:
    """处理 chat 命令并输出生成的 system prompt。"""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if config_dir is None:
        config_dir = os.path.join(_AGENTS, "configs")

    injector = DSHKnowledgeInjector(config_dir=config_dir)
    kb = injector._get_kb(role_id)
    config = injector._load_role_config(role_id)

    domains = (
        args.domains.split(",")
        if getattr(args, "domains", None)
        else kb.get_domain_for_intent(
            args.intent, config.get("keyword_map", {}), use_vector=getattr(args, "vector", False)
        )
    )

    prompt = kb.build_system_prompt(domains=domains, task_context=args.intent)

    if getattr(args, "output", None):
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f'{{"ok": true, "output": "{args.output}", "domains": {domains}, "prompt_length": {len(prompt)}}}')
    else:
        print(prompt)

    return 0
