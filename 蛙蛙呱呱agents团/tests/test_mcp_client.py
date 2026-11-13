# -*- coding: utf-8 -*-
"""MCP 适配器测试：不联网，起本地 stdio 桩服务器。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp.client import MCPClient, doctor, load_registry  # noqa: E402


def test_registry_slots_are_reserved() -> None:
    reg = load_registry()
    assert len(reg["servers"]) >= 8
    assert all(s["enabled"] is False for s in reg["servers"].values())
    assert all(s["owner_role"] for s in reg["servers"].values())


def test_client_handshake_list_and_call() -> None:
    entry = {"transport": "stdio", "command": sys.executable,
             "args": [str(ROOT / "tests" / "fixtures" / "mock_mcp_server.py")],
             "enabled": True, "owner_role": "r05"}
    c = MCPClient.from_entry(entry, "mock")
    try:
        c.initialize()
        tools = c.list_tools()
        assert tools and tools[0]["name"] == "echo_price"
        res = c.call_tool("echo_price", {"item": "苹果"})
        text = res["content"][0]["text"]
        assert json.loads(text)["item"] == "苹果"
    finally:
        c.close()


def test_doctor_reports_reserved() -> None:
    r = doctor({"transport": "stdio", "enabled": False, "owner_role": "r05"}, "x")
    assert r["status"] == "reserved"
