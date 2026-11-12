# -*- coding: utf-8 -*-
"""MCP 适配器（零第三方依赖）：stdio 与 Streamable HTTP 两种传输。

设计目标
- **现在不接任何服务**：registry 里全部 enabled=false，只保留槽位与配置模板。
- **你说接哪个，就填哪个**：填 command/args 或 url，把 enabled 改 true，跑 `mcp_doctor.py doctor`。
- **兼容两代协议**：旧版 `initialize` 握手（≤2025-11-25）与新版每请求 `_meta`（≥2026-07-28）。

用法：
    from shared.mcp.client import load_registry, MCPClient
    reg = load_registry()
    c = MCPClient.from_entry(reg["servers"]["search"])
    c.initialize(); print(c.list_tools())
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).resolve().parent / "registry.json"

PROTO_MODERN = "2026-07-28"
PROTO_LEGACY = "2025-11-25"
CLIENT_INFO = {"name": "guagua-agents", "version": "1.0.0"}


class MCPError(RuntimeError):
    pass


def load_registry(path: Path | None = None) -> dict:
    p = path or REGISTRY
    data = json.loads(p.read_text(encoding="utf-8"))
    _validate(data)
    return data


def _validate(data: dict) -> None:
    if "servers" not in data or not isinstance(data["servers"], dict):
        raise MCPError("registry 缺 servers 字典")
    for name, s in data["servers"].items():
        if "transport" not in s or s["transport"] not in ("stdio", "http"):
            raise MCPError(f"{name}: transport 必须是 stdio 或 http")
        # 预留槽位允许留空；启用时才要求填写连接信息
        if s.get("enabled"):
            if s["transport"] == "stdio" and not s.get("command"):
                raise MCPError(f"{name}: 启用 stdio 槽位必须给 command")
            if s["transport"] == "http" and not s.get("url"):
                raise MCPError(f"{name}: 启用 http 槽位必须给 url")
        if not s.get("owner_role"):
            raise MCPError(f"{name}: 必须声明 owner_role（谁负责这个数据源）")


class _StdioTransport:
    def __init__(self, command: str, args: list[str] | None = None, env: dict | None = None):
        self.proc = subprocess.Popen(
            [command, *(args or [])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            env={**os.environ, **(env or {})},
        )
        self._q: queue.Queue[dict] = queue.Queue()
        self._stderr: list[str] = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _read_stderr(self) -> None:
        assert self.proc.stderr is not None
        for line in self.proc.stderr:
            self._stderr.append(line.rstrip())

    def send(self, msg: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def recv(self, timeout: float = 20.0) -> dict:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty as exc:
            tail = "\n".join(self._stderr[-5:])
            raise MCPError(f"等响应超时（{timeout}s）；stderr: {tail}") from exc

    def close(self) -> None:
        try:
            self.proc.terminate()
        except Exception:  # noqa: BLE001
            pass


class _HttpTransport:
    def __init__(self, url: str, headers: dict | None = None):
        self.url = url
        self.headers = {"Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream", **(headers or {})}

    def send(self, msg: dict) -> None:
        body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, headers=self.headers, method="POST")
        self._resp = urllib.request.urlopen(req, timeout=30)
        self._raw = self._resp.read().decode("utf-8", "replace")

    def recv(self, timeout: float = 20.0) -> dict:
        ctype = self._resp.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            for line in self._raw.splitlines():
                if line.startswith("data:"):
                    try:
                        return json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
            raise MCPError("SSE 响应里没有可解析的 data")
        return json.loads(self._raw)

    def close(self) -> None:
        try:
            self._resp.close()
        except Exception:  # noqa: BLE001
            pass


class MCPClient:
    def __init__(self, entry: dict, name: str = ""):
        self.name = name or entry.get("label", "mcp")
        self.transport_kind = entry["transport"]
        if self.transport_kind == "stdio":
            self.t = _StdioTransport(entry["command"], entry.get("args"), entry.get("env"))
        else:
            self.t = _HttpTransport(entry["url"], entry.get("headers"))
        self._id = 0
        self._modern = False

    @classmethod
    def from_entry(cls, entry: dict, name: str = "") -> "MCPClient":
        return cls(entry, name)

    def _rpc(self, method: str, params: dict | None = None, timeout: float = 20.0) -> dict:
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        if self._modern and method != "initialize":
            msg["params"] = {**msg["params"],
                             "_meta": {"protocolVersion": PROTO_MODERN, "clientInfo": CLIENT_INFO}}
        self.t.send(msg)
        while True:
            resp = self.t.recv(timeout)
            if resp.get("id") == self._id:
                if "error" in resp:
                    raise MCPError(f"{method} 失败: {resp['error']}")
                return resp.get("result", {})

    def initialize(self) -> dict:
        """先按旧版握手；服务器不支持再退回新版每请求元数据。"""
        try:
            res = self._rpc("initialize", {
                "protocolVersion": PROTO_LEGACY,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            })
            self.t.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            return res
        except MCPError:
            self._modern = True
            return self._rpc("tools/list", {})

    def list_tools(self) -> list[dict]:
        return self._rpc("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None, timeout: float = 60.0) -> dict:
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}}, timeout)

    def close(self) -> None:
        self.t.close()


def doctor(entry: dict, name: str) -> dict:
    """连通性体检：起服务 → 握手 → 列工具 → 关闭。不调用任何会写数据的工具。"""
    if not entry.get("enabled"):
        return {"name": name, "status": "reserved", "detail": "槽位已预留，enabled=false"}
    client = None
    try:
        client = MCPClient.from_entry(entry, name)
        client.initialize()
        tools = client.list_tools()
        return {"name": name, "status": "ok", "tools": [t.get("name") for t in tools],
                "count": len(tools)}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "status": "error", "detail": f"{type(exc).__name__}: {exc}"}
    finally:
        if client:
            client.close()
