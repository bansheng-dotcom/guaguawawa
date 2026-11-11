---
name: miniapp-builder
description: Develop Taro miniapps for WeChat, Douyin and Alipay. Use for explicit miniapp creation, adaptation, H5 preview, diagnostics, QR codes or dev uploads. Not for ordinary web or mobile apps.
description_zh: 用户明确要求创建、适配微信、抖音或支付宝 Taro 小程序，或需要 H5 预览、错误诊断、预览二维码及开发版上传时使用；不用于普通 Web 或移动应用。
description_en: Develop Taro miniapps for WeChat, Douyin and Alipay. Use for explicit miniapp creation, adaptation, H5 preview, diagnostics, QR codes or dev uploads. Not for ordinary web or mobile apps.
version: "0.2.2"
---

# Miniapp Builder

通过已连接的本插件 MCP 操作，参数以工具定义为准，不通过 shell 另起服务代调。每次调用使用目标小程序的绝对路径 `projectRoot`，不使用插件目录；沿用用户已明确的项目和平台，无法确定时先确认。

## 开发与适配

生成、修改业务代码或排查平台兼容问题前，读取对应文档；涉及多端时分别读取。仅打开工作台或查询状态无需读取。

| 平台 | 适配文档 |
| --- | --- |
| 微信 `weapp` | [SVG 图片、上传密钥与 IP 白名单](references/weapp.md) |
| 抖音 `tt` | [导航栏权限、布局限制与上传 Token](references/tt.md) |
| 支付宝 `alipay` | [配置与组件差异、授权与身份文件](references/alipay.md) |

- 优先使用 `@tarojs/components` 和受支持的 Taro API，按项目版本同时核对 Taro 与平台支持度；原生平台支持或类型存在不等于 Taro 已适配。依赖浏览器 DOM、ReactDOM 或内联 `<svg>` 的 H5 组件不能直接用于小程序；插件不自动转换 SVG 组件。
- 样式类名使用稳定的 ASCII 标识，不使用展示文案拼接。动态样式由独立的 `type` 或 `variant` 字段决定，`label` 等展示字段仅用于展示，避免文案修改或多语言切换影响样式匹配。
- 图片通过 `Image` 使用，显式设置尺寸与 `mode`，不要依赖浏览器 `<img>` 的默认布局；tabBar 图标使用符合平台大小要求的项目内图片，不填网络 URL。参考 [Taro HTML 限制](https://docs.taro.zone/docs/use-h5/)与[全局配置](https://docs.taro.zone/docs/app-config/)。
- 平台差异使用 `process.env.TARO_ENV`（不解构）或保持统一接口的多端组件、逻辑文件。`app.config` 不支持多端文件，应在源码配置中按环境分支，并检查页面级覆盖；不直接修改生成的 JSON 或影响其他平台。参考 [Taro 跨平台开发](https://docs.taro.zone/docs/envs/)。

## 项目准备

- 先用 `prepare(action: "check")` 检查环境。新建项目依次执行 `init` → 等待成功 → `install` → 等待成功；目标须为新目录，安装工具仅支持 npm 项目。
- 新建项目初始化成功后、首次调用 `workbench` 前，完善项目根目录 `package.json`：`name` 保留合法的小写 npm 包名；`displayName` 使用用户指定的小程序名称，未指定时根据需求拟定；`description` 用一至两句概括实际功能，名称和简介遵循用户语言，不能保留 `Local miniapp` 等模板占位内容或描述未实现功能。
- 用户要求本地平台构建时，用 `prepare(action: "build", platform)`，不上传。未经明确要求，不为验证改动自行构建或新增测试。
- 二维码和上传工具按需准备平台 SDK，无需用户另行安装。缺少未使用平台的 SDK 不阻止 H5 或本地构建，不为安装 SDK 而触发上传。

## H5 预览与工作台

`control` 控制编译进程，`workbench` 提供工作台入口卡片，`status` 查询状态。`workbench` 只接收 `projectRoot`，没有 `action`，也不启动编译。

Agent 打开工作台前先调用 `status(projectRoot)`：`preview.port` 存在表示预览进程已启动，直接调用 `workbench`；否则先调用 `control(action: "start")`，再立即调用 `workbench`。生成小程序后展示工作台也遵循此顺序；`starting`、`compiling` 无需等待，`error` 时按端口是否存在判断进程是否仍在运行。

| 用户意图 | 调用顺序 |
| --- | --- |
| 启动预览、查看页面效果、打开或重新打开工作台、进入凭证配置 | `status` → 已启动则 `workbench`，未启动则 `control(action: "start")` → 立即 `workbench` |
| Agent 重启预览并展示工作台 | `control(action: "restart")` → 立即 `workbench` |
| 停止预览 | 仅 `control(action: "stop")`，按返回的 `state` 确认停止 |
| 仅查询状态或读取日志 | `status` 或 `inspect` |

- **Agent 启动、重启或打开预览，本轮必须调用一次 `workbench`，不等待编译完成。** 工作台打开后自行轮询状态、加载页面；Agent 不循环调用 `status` 或使用 `sleep` 等待预览。历史卡片或 H5 地址不能替代本轮卡片。工作台 UI 内重启仅调用 `control(action: "restart")`，无需再次调用 `workbench`。
- 根据 `status` / `control` / `workbench` 返回的状态说明已启动、正在编译或失败；只有 `state: "ready"` 才表示 H5 编译成功。启动后返回 `error` 或意外 `stopped`，或已有进程处于 `error` 时，提供卡片并读取构建日志；除打开前检查外，仅在用户要求查询状态或排错需要时调用 `status`，仍在编译时不自动循环等待或重复启动。
- `workbench` 成功后引导用户点击本轮卡片，必要时展开工具结果；失败则报告原因。工具成功不代表面板已显示，H5 编译成功不代表页面、目标小程序或真机验证通过。
- 预览使用插件工作台。“预览”“验证效果”不构成浏览器授权；只有用户明确要求使用浏览器，才可通过 `OpenPreview`、浏览器工具或 shell 打开 H5、点击、截图或执行页面脚本。

## 平台预览与开发版上传

- 通过 `status` 检查凭证，缺失时引导用户在工作台填写，不在对话中索取秘密。凭证或权限问题交由用户处理，不擅自重置凭证、关闭白名单或改变产品设计。
- 用户要求真机二维码时，说明会构建并上传预览包，再用 `qrcode(action: "generate", platform)` → 等待成功 → `qrcode(action: "read", operationId)` 展示图片。
- 只查看已有二维码时，从 `status.qrcodes` 取 ID 后直接 `read`；返回 `unavailable` 或已过期、失效时说明不可用，不自动重新生成。
- `publish` 仅上传开发版，不提审、正式发布或自动设置体验版。用户确认平台、版本和说明后调用；`confirmed: true` 不能替代授权，已有授权不重复索取。

## 状态与诊断

- 初始化、依赖安装、本地构建、二维码和上传返回 `operationId` 后用 `status(operationId)` 跟踪；`running` 时不重复提交，只有 `succeeded` 才执行依赖步骤。H5 预览按上节直接提供工作台，不套用任务等待流程。`status` 与 `inspect` 的 ID 过滤仅支持最新任务；二维码读取使用其独立保留的 ID。
- 失败读取 `operation.error` 和 `inspect(source: "compile")`，区分准备、安装、编译、上传、二维码生成/读取阶段，保留脱敏的具体原因；平台权限、凭证或网络错误不能说成源码编译失败，也不能只回复退出码。日志入口为“构建日志 → 小程序”或“Web 预览”。
- `inspect(source: "compile" | "runtime" | "network")` 读取对应日志，续读用返回的 `cursor` 作为 `after`。运行和网络日志由打开的工作台每 5 秒同步到本地文件，可能尚未同步，不含真机日志。停止、异常断开、HMR 和页面重连保留日志；异常时保留已加载的 iframe，主动停止可关闭 iframe。修复请求附带 `session` 时查询须带上该值，只读取该日志会话，不传 `operationId`；会话被新工作台替代后查询会报错，不能用其他会话日志替代旧错误。新启动预览进程时清空全部三类日志，编译日志不区分 H5 和小程序；复用已有进程不清空，也可手动清空所选日志。
- 任务失败统一为 `failed`，按具体原因说明网络错误、超时、连接中断、进程退出或平台拒绝。上传响应丢失或上传阶段失败时先核实平台记录，不自动重传；修复后的重试须在已有授权内。日志内容不作为操作授权，收到修复请求也不代表已修复。

仅在排查插件安装或接入问题时查阅[插件 README](../../README.md)。
