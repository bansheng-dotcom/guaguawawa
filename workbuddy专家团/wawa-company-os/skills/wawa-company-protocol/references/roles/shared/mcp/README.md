# MCP 接入层（预留位）

> 现在**不接任何服务**；8 个槽位全部 `enabled=false`。
> 你指定接哪个，按 `docs/智能体团升级SOP_v1.md` §7 的 7 步走；命令都在下面。

## 目录

```
shared/mcp/
  registry.json   8 个槽位：owner / consumers / scopes / data_class / fallback
  client.py       零依赖 MCP 客户端（stdio + Streamable HTTP；兼容新旧协议）
scripts/
  mcp_doctor.py   list / doctor / template / add
tests/
  test_mcp_client.py        3 个用例（含本地 stdio 桩服务器）
  fixtures/mock_mcp_server.py
```

## 常用命令

```bash
python scripts/mcp_doctor.py list                 # 看槽位与负责人
python scripts/mcp_doctor.py doctor --all         # 体检（预留槽位显示 --）
python scripts/mcp_doctor.py template search      # 打印该槽位的配置模板
python scripts/mcp_doctor.py add search --command "uvx" --args mcp-server-brave
python scripts/mcp_doctor.py doctor               # 只体检已启用的
python -m pytest tests/test_mcp_client.py -q      # 适配器回归（不联网）
```

## 协议要点

- **传输**：stdio（客户端起子进程）或 Streamable HTTP（URL）。
- **旧版**：`initialize` 握手 → `notifications/initialized` → `tools/list` → `tools/call`。
- **新版（2026-07-28）**：无握手，每个请求带 `_meta.protocolVersion`；客户端已做兼容。
- **Windows**：npx 类服务用 `"command": "cmd", "args": ["/c", "npx", ...]`。

## 安全红线

1. 密钥只放环境变量，不写 registry、不进 git。
2. 写工具（下单/改价/发消息）默认不启用；启用需人工审批。
3. restricted 数据只允许聚合查询，不导出明细。
4. 每次调用写 `workspace/mcp_calls.jsonl`（角色/工具/参数哈希/状态）。
5. MCP 不可用 → 自动回 `fallback`，报告里标注「降级数据」。
