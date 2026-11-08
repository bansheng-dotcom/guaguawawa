# -*- coding: utf-8 -*-
"""Unified LLM Knowledge Injection CLI for all roles r01-r20.

Usage:
    python agents/chat.py --role r02 --intent "排期Q1冲刺并计算关键路径"
    python agents/chat.py --role r03 --intent "月结对账发现差异" --output prompt.txt
    python agents/chat.py --role r06 --intent "分析订单趋势与漏斗留存" --vector
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.dirname(_HERE)
if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from agents.shared.chat_cli import handle_chat


def main() -> int:
    parser = argparse.ArgumentParser(description="一人公司 20 角色通用知识注入与 Prompt 构建器")
    parser.add_argument("--role", required=True, help="角色ID（如 r01..r20）")
    parser.add_argument("--intent", required=True, help="用户意图")
    parser.add_argument("--domains", default=None, help="手动指定知识域（逗号分隔）")
    parser.add_argument("--output", default=None, help="输出文件路径")
    parser.add_argument("--vector", action="store_true", help="使用向量语义检索")

    args = parser.parse_args()
    role_id = args.role.lower()

    return handle_chat(args, role_id=role_id)


if __name__ == "__main__":
    raise SystemExit(main())
