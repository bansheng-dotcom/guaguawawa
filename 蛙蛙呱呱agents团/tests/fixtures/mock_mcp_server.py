# -*- coding: utf-8 -*-
"""最小 MCP stdio 服务器（仅测试用）：initialize / tools/list / tools/call。"""
from __future__ import annotations

import json
import sys

TOOLS = [{
    "name": "echo_price",
    "description": "返回给定品种的价格（测试桩）",
    "inputSchema": {"type": "object", "properties": {"item": {"type": "string"}}, "required": ["item"]},
}]


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, mid = msg.get("method"), msg.get("id")
        if method == "initialize":
            out = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                   "serverInfo": {"name": "mock", "version": "0.1"}}
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            out = {"tools": TOOLS}
        elif method == "tools/call":
            args = msg.get("params", {}).get("arguments", {})
            out = {"content": [{"type": "text", "text": json.dumps({"item": args.get("item"), "price": 6.5})}]}
        else:
            out = {}
        if mid is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": out}, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
