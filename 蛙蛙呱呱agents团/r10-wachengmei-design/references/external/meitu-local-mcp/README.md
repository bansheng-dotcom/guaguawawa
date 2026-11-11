# MeituHub（TRAE Plugin）

本插件通过 TRAE OAuth Connector 连接美图账号，并通过随包提供的本地 MCP Server 向 TRAE 暴露美图图片、视频工具和当前账号可见的自定义工作流。

## 包含内容

- `meitu-local-tools` Skill：指导 Agent 选择和调用美图工具。
- `meitu-local` 本地 MCP：动态获取普通工具和用户工作流配置并执行调用。
- `meitu-oauth` Connector 声明：触发美图账号 OAuth 授权。
- MCP 协议使用官方 Node.js SDK，并支持 TRAE 当前的 `2025-11-25` 协议与表单 Elicitation。

插件已经包含运行所需的 JavaScript，不要求用户安装 `meitu-cli`。

## 与内部 meitu-cli 的能力基线

本包版本为 `0.2.14`，通过 `@meitu/meitu-runtime` `1.1.1` 与内部 `@meitu/meitu-cli` `2.1.30` 对齐以下业务能力：

- 使用同一套远端工具配置解析、媒体参数映射、上传策略、任务提交和状态轮询逻辑。
- 使用同一套账号工作流 Registry、超时规则、服务端操作链接透传和服务分区配置。
- 使用统一 MTCC 结构，并补充 TRAE 的 `client=trae`、`source=trae_plugin`、Skill、工具名称以及 Runtime 维护的应用标识。
- 工具上下线和参数变化由远端 Registry 动态生效，不需要为每个命令重新发布 Local MCP 代码。

对齐目标是业务工具目录和执行行为。CLI 专属的命令行 Help、shell Batch 配置文件、AK/SK 本地登录、包管理，以及内部 `meitu mcptool` 运维命令不作为 MCP 工具暴露；TRAE 使用 MCP JSON Schema、`tools/list` 和 `tools/call` 完成对应的 Agent 调用。

## 运行要求

- TRAE 支持试运行版 Plugin、项目级 Skill、本地 stdio MCP 和 OAuth Connector。
- 本机安装 Node.js 18 或更高版本，并能通过 `node` 命令启动。
- TRAE 服务端已按单独提供的 OAuth 对接文档配置名为 `meitu-oauth` 的 Connector Provider Template。

## 认证链路

1. TRAE 安装插件时触发 `meitu-oauth` 授权。
2. TRAE 服务端完成 Authorization Code + PKCE 换取和刷新 Token。
3. TRAE 只把当前有效的 Access Token 映射到本地 MCP 的 `MEITU_OAUTH_ACCESS_TOKEN` 环境变量。
4. 本地 MCP 使用 `Authorization: oauth-token <access_token>` 调用美图业务网关。

业务工具提交及状态查询会使用与 `meitu-cli` 相同的 MTCC 编码结构，并明确上报 `client=trae`、`source=trae_plugin`、Skill 名称和工具名称。本地 MCP 会在 `~/.meitu/trae/device.json` 中生成并复用独立随机 `gnum`；该文件不包含账号 Token，也不依赖 `meitu-cli` 会话。

Client Secret 和 Refresh Token 只应由 TRAE 服务端保存，不得注入本地 MCP。用户无需提供 AK/SK，也不应在对话中提交 Token。

## 验收建议

1. 从 TRAE 发起 OAuth 授权，禁止复用手工拼接的静态 `state` 或 PKCE 链接。
2. 调用 `meitu_auth_status`，确认 Connector 已注入 Access Token；该工具不会返回 Token 内容。
3. 调用 `meitu_registry_status` 和 MCP `tools/list`，确认工具目录可用。
4. 确认账号已发布的工作流以 `meitu_workflow__<listing_code>` 出现在 `tools/list`。
5. 调用一个双方约定的无计费或低成本普通工具，再调用一个测试工作流验证完整链路。
6. 验证 Access Token 到期后的自动刷新和 Refresh Token 轮换。
7. 重启 TRAE 后重复执行，确认授权状态和工具调用仍然正常。
8. 拖入一张本地图片或提供本地绝对路径，确认 TRAE 弹出上传授权；同意后才上传并执行，拒绝后不得创建任务。
9. 再使用一张公网 HTTP/HTTPS 图片，确认无需本地文件授权即可直接执行。

## 本地媒体文件

- 工具参数同时接受公网 `http://`/`https://` URL、本地绝对路径和 `file://` URL。
- 本地路径会先解析为真实路径，并校验文件存在、为普通文件、类型和大小；默认单文件上限为 256 MiB。
- 真正读取和上传本地文件前，MCP 会通过标准 `elicitation/create` 请求 TRAE 展示实际路径并让用户确认。同一次工具调用的多个本地文件只确认一次。用户直接提交只允许本次；用户主动勾选“始终信任此插件”后，会对当前系统用户持久生效，后续本地文件调用不再弹窗。
- 可调用 `meitu_local_file_trust_status` 查看持久信任状态，调用 `meitu_local_file_trust_revoke` 撤销；撤销后下一次本地文件调用会重新确认。
- 用户拒绝、取消，或客户端没有声明表单 Elicitation 能力时，工具返回 `isError: true` 和可见错误说明，不提交任务。
- 相对路径仅在显式配置 `MEITU_MCP_WORKSPACE_ROOT` 时可用；TRAE 插件包不写死附件目录。拖入附件能否成功，取决于 TRAE Agent 是否把附件的实际本地路径传给工具。
- 可用 `MEITU_MCP_MAX_LOCAL_FILE_BYTES` 调整单文件大小限制。
- 持久信任默认写入 `~/.meitu/trae/local-file-trust.json`，也可通过 `MEITU_MCP_LOCAL_FILE_TRUST_FILE` 覆盖测试位置。

## 安全边界

- 插件不读取本机 AK/SK、`~/.meitu` 登录会话、Client Secret 或 Refresh Token。
- OAuth Token 不会被 MCP 工具持久化或返回。
- MTCC 设备文件只保存随机 `gnum`，文件权限为 `0600`。
- 本地媒体必须由用户明确提供路径。默认每次调用上传前通过 TRAE Elicitation 确认；只有用户主动勾选“始终信任此插件”后才跳过后续确认。信任记录不含 Token，并以 `0600` 权限保存在当前系统用户目录；路径、文件类型、大小和软链接校验不会被跳过。
- 不暴露充值、购买、账号删除等账号管理操作。
- 余额不足时保留服务端返回的专属充值地址作为链接目标，并统一显示为“前往 MeituHub 充值”的文字链接；同一对话后续再次询问充值入口时仍保持文字链接，同时提供通用套餐定价入口，不自动打开或购买。
- OAuth Provider 地址、Client ID 和 Client Secret 由 TRAE 根据单独的对接文档在服务端配置，不写入插件包。

## 已知限制

- 当前本地 MCP 依赖 TRAE 所在机器的系统 Node.js；TRAE 尚不保证所有系统均预装兼容版本。
- 动态 `tools/list` 和 `notifications/tools/list_changed` 仅按 TRAE 当前本地 MCP 能力生效。
- 普通业务工具完全以当前 OAuth 身份对应的美图远端工具目录为准，插件不再维护第二份本地白名单。
- 自定义工作流由当前 OAuth 账号的 Workflow Registry 决定；执行前会再次确认工作流仍然在线可见。
- 当前试运行包固定为 CN 分区。共享代码已支持 INTL 服务配置，但国际版必须单独完成 TRAE OAuth Connector 和 IAM Client 配置后再交付。

## 许可证

MIT，详见 `LICENSE`。
