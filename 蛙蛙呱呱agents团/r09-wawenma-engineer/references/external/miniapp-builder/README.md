# miniapp-builder

Taro 小程序开发插件，通过 stdio MCP 接入 Agent，在 Trae 的 MCP Apps 工具面板中提供工作台，用于 H5 预览、错误诊断、真机扫码预览和开发版上传。支持微信、抖音和支付宝平台。

## 支持能力

| MCP 工具 | 能力 |
| --- | --- |
| `prepare` | 检查环境、初始化新项目、安装 npm 项目依赖、指定平台本地构建 |
| `workbench` | 显示项目卡片，由用户点击打开 MCP Apps 工作台 |
| `control` | 启动、重启或停止 H5 预览 |
| `inspect` | 按游标读取构建、运行和网络日志，构建日志可按最新任务过滤 |
| `status` | 查看预览状态、最新任务及阶段、平台配置和二维码状态 |
| `qrcode` | 构建并上传预览包，生成或读取真机预览二维码 |
| `publish` | 构建并上传开发版，不提审、不正式发布 |

工作台支持平台选择、凭证配置、二维码展示、日志搜索与筛选、上传阶段和结果查看，以及将错误发送到当前对话。`credentials` 和 `logs` 仅在客户端声明 MCP Apps 能力后注册，标记为 `visibility: ["app"]`，不暴露给模型。`logs(action="append" | "clear")` 负责追加和清空日志，`inspect` 只读。

侧栏“构建日志”入口默认选择“Web 预览”；从上传任务进入构建日志时定位到“小程序”。

工作台通过宿主 `trae/telemetry/report` 统计以下五个行为，统一携带 `result`（`succeeded`、`failed`）。失败时携带 `message`，使用现有脱敏规则并截断至 128 UTF-8 字节，成功时不传。

| 事件 | 行为 | 其他属性 |
| --- | --- | --- |
| `workbench` | 当前页面首次挂载完整工作台，或打开、初始化失败 | 无 |
| `compile` | H5 编译结果或平台构建结果 | `platform`：`h5`、`weapp`、`tt`、`alipay` |
| `qrcode` | 生成预览二维码的任务结果或提交失败 | `platform` |
| `publish` | 上传平台开发版的任务结果或提交失败 | `platform` |
| `repair` | 一键修复消息发送结果 | `source`：`compile`、`runtime`、`network` |

已进入任务的结果还携带 `operation_id`，有阶段和错误码时携带 `phase`、`error_code`；平台编译结果使用对应 `buildId` 关联，H5 编译只增加 `phase: "build"`。同一二维码/上传任务的编译失败与任务失败可按 `operation_id` 关联，不能直接将事件数当成独立操作数。新增字段均使用宿主允许的标量类型，不增加 IP 专用上报字段。

编译、二维码和上传基于工作台轮询观察到的结果上报，同一结果不因重复轮询计数；首次读取的历史平台构建和任务结果不计数，首次读取的当前 H5 编译结果计数。工作台关闭、页面隐藏或轮询间隔内未观察到的结果可能漏计，不提供后台任务全量统计。宿主须声明埋点能力并授予插件事件及字段权限；缺少能力时不发送，失败不改变业务结果，也不重试。初始化失败仅在宿主连接和埋点能力仍可用时上报。Dev 模式不发送埋点；`accepted` 仅表示交给宿主 Tea 入口，实际入库仍需宿主接线和数据平台验收。

连续点击“Web 预览”标题 5 次（相邻点击间隔不超过 1 秒）打开隐藏的“页面诊断”弹窗，可复制诊断信息或清空记录。这里展示工作台自身的宿主能力快照、预览/外链/消息能力、接口调用结果及耗时（含排队）、页面异常，最近 200 条仅保留在当前页面内存中，重新加载页面即清空；来源卡片与独立工作台分别缓存，不合并记录。接口记录不包含请求参数和响应正文，异常文本使用现有脱敏规则并限制长度；该入口不会上传日志，也不改变小程序的构建、运行和网络日志。

`workbench(projectRoot)` 只接收项目路径，显示 inline 项目信息卡片，点击“预览小程序”打开完整工作台，不启动编译。卡片从项目 `package.json` 读取名称、说明和版本，显示调用时的预览状态；完整工作台挂载后才轮询状态与日志。`control(projectRoot, action)` 仅执行 H5 控制，不创建卡片或打开工作台；`action` 必填，支持 `start`、`restart`、`stop`。初始化、安装、构建、生成二维码和上传返回任务 ID，依赖后续操作前应通过 `status` 确认成功。`preview.state: "ready"` 表示 H5 编译成功，不代表页面实际加载成功。

## 兼容性与运行要求

- Node.js ≥20.19，系统需提供 npm；客户端需能在项目所在环境启动 stdio MCP 进程。原生工作台要求客户端支持 MCP Apps；工具面板展示、主题扩展、外链打开和 H5 预览地址解析使用当前 Trae MCP Apps 代码中的协议。
- 构建适配基准为 Taro 4.1.9、React、Webpack5。初始化使用固定版本 CLI，生成 React、TypeScript、Webpack5、Sass 项目；其他 Taro 版本未保证兼容，其他框架及 Vite 构建器未适配。
- 本次宿主 API 调整已完成发布构建和协议自动化测试，宿主端到端验收尚未完成。Windows 和 Linux 有运行适配，但完整安装、预览、三端构建及平台上传尚未实测。
- Windows 通过 Node 执行 npm/npx 的 JS 入口，使用 `taskkill /T /F` 清理进程树；macOS/Linux 使用进程组终止。构建产物位于项目内，避免 Windows 跨盘输出问题。
- 平台操作依赖对应官方 SDK 的系统、CPU 架构、网络和权限要求；存在适配代码不等于所有组合均已验证。
- 原生工作台同步宿主深浅色，并将 Trae 主题变量按原名覆盖到页面全局；主题更新时清除已失效的旧变量。
- 工作台读取宿主 `locale`，支持中文、英文和日文，其他语言使用英文；宿主语言更新会刷新界面文案，保留当前表单和预览状态。项目名称、业务内容及工具返回的原始日志不做翻译。

| 小程序平台 | 标识 | 锁定 SDK | 凭证 |
| --- | --- | --- | --- |
| 微信 | `weapp` | `miniprogram-ci@2.1.31` | App ID、代码上传私钥文件 |
| 抖音 | `tt` | `tt-ide-cli@0.1.33` | App ID、上传 Token |
| 支付宝 | `alipay` | `minidev@2.2.5` | App ID、官方工具生成的 identity 文件 |

各 SDK 精确版本及传递依赖以 `app/sdk/<platform>/package.json` 和 `package-lock.json` 为准。目标项目需安装对应的 Taro 平台插件。

微信私钥在保存前及平台任务编译前解析检查，要求未加密的 PEM RSA 私钥；无效文件不会覆盖已有凭证。此检查不证明密钥与 App ID 匹配或密钥仍有效。白名单和私钥错误在现有错误信息中说明处理方法，凭证配置沿用工作台已有入口。白名单错误使用微信报错中的出口 IP，不另查公网 IP、不修改系统网络或平台白名单。

任务失败统一记为 `failed`，包括平台拒绝、网络错误、请求超时、连接中断和进程退出。错误码以 `operation.errorCode` 返回，并保留在任务日志中；网络错误标明具体类别，原始错误仍经脱敏保留。旧版未完成记录恢复为失败。上传请求已发出时先核实平台记录，不自动重传。

## 接入与使用

插件根目录的 `.mcp.json`：

```json
{
  "mcpServers": {
    "miniapp-builder": {
      "command": "node",
      "args": ["./app/core/index.js"]
    }
  }
}
```

发布包 `dist/` 就是插件根目录，运行时相对路径均以此为基准；安装后以复制出的插件目录为根，不再附加 `dist/`。其他客户端可将 Node 和入口文件改为绝对路径；Windows JSON 路径使用 `/` 或转义的 `\\`。不要使用 `npm start` 作为 MCP command，避免 npm 输出混入 stdio 协议。

发布产物已打包 MCP 核心依赖，无需安装核心依赖。源码开发先在源码目录执行：

```sh
npm --prefix app ci
npm --prefix app/web ci
```

开发工作台 UI 时，在源码目录运行：

```sh
npm --prefix app/web run dev
```

打开 Vite 输出的本地地址即可预览，修改页面和样式会自动更新。Dev 模式通过 `app/web/dev/api.js` 提供本地示例状态和构建日志，可直接编辑该文件调整展示数据；可查看平台切换、日志面板和凭证、上传弹窗，不连接项目、不执行上传或发送对话消息。此开发适配仅在 Vite Dev 模式加载，构建产物使用 `src/libs/api.js` 的 MCP Apps 接口。

地址加 `?mode=inline` 预览摘要卡片，点击按钮切换到完整工作台；加 `&theme=dark` 查看深色主题，`&locale=zh-CN` 或 `&locale=ja` 查看对应语言。默认地址保持英文完整工作台预览。Dev 模式不提供宿主外链和项目预览地址能力。

MCP 接入使用完整发布包。`ui://miniapp-builder/app/web/index.html` 通过 `resources/read` 返回发布根目录下的 `app/web/index.html`，运行时只读取这一份文件。资源缺失时返回文件读取错误，不自动构建。HTML 内联脚本、样式与静态资源，上限 2 MiB。

源码主包锁文件含内部 registry 地址，外部开发环境需具备相应访问条件或使用发布产物。

使用时向 Agent 指定目标项目绝对路径和目标平台。Agent 启动预览、查看效果、打开或重新打开工作台（包括生成小程序后展示工作台、进入凭证配置）前先调用 `status(projectRoot)`：`preview.port` 存在表示预览进程已启动，直接调用 `workbench(projectRoot)`；否则先调用 `control(action: "start", projectRoot)`，再立即调用 `workbench(projectRoot)`。`starting`、`compiling` 无需等待，`error` 时按端口是否存在判断进程是否仍在运行。Agent 重启预览并展示工作台使用 `control(action: "restart", projectRoot)` → 立即 `workbench(projectRoot)`；工作台 UI 内重启只调用 `restart`。工作台自行轮询状态并在就绪后加载页面；Agent 不循环调用 `status` 或使用 `sleep` 等待编译。每轮预览请求提供一次新卡片，按工具返回的实际状态说明，不把启动成功说成编译成功。启动后返回失败或已有进程处于 `error` 时提供卡片并读取构建日志；除打开前检查外，仅在用户要求查询状态或诊断需要时调用 `status`。停止预览只调用 `control(action: "stop")`，按返回的 `state` 确认停止。初始化、依赖安装、本地构建、二维码和上传仍按任务 ID 查询结果，再执行依赖步骤。

`workbench` 返回后，App 连接并收到项目数据，显示 inline 摘要卡片。用户点击“预览小程序”时调用 `trae/panel/open`，创建独立工作台 App，来源卡片保持 inline。同次调用重复打开复用已有面板；资源使用 `panel.scope: "call"`，不同调用独立，跨会话隔离。布局与最大化由宿主管理。卡片本身不启动编译，完整工作台通过 MCP 读取项目状态。工具调用成功不等于面板已显示。连接实际项目的工作台通过 MCP Apps 打开，未声明此能力的客户端调用 `workbench` 时会收到错误。平台凭证在工作台填写。

终端辅助命令，在插件根目录执行：

```sh
node app/core/index.js --check-sdk
```

`--check-sdk` 只检查本地 SDK 文件，不下载、不执行平台 SDK。停止预览使用 `control(action: "stop", projectRoot)`；`restart` 停止后重新启动编译，工作台的“刷新”按钮调用此动作。停止 MCP 会清理它管理的全部项目 worker。

## 实现方式

```text
Agent ────────────── stdio MCP ── Manager ── worker ── Taro / 平台 SDK
                         ↑
Trae 工具面板 ── MCP App 工作台
                         │
               H5 iframe / MessageChannel 日志
```

Core 按职责组织，入口和资源基准路径保持固定：

```text
app/core/
  index.js                  # 命令行入口、Node 版本检查
  worker.cjs                # 独立子进程入口：执行 Taro 与平台 SDK
  paths.js                  # 插件根路径、模块与 SDK 路径解析
  mcp/
    server.js               # stdio MCP 注册、工具结果、退出清理
    tools.js                # 工具描述、参数 schema 与校验
    app.js                  # MCP App 资源、展示元数据、二维码图片
  project/
    manager.js              # 任务调度、预览、构建、SDK 准备与上传
    store.js                # 项目缓存、状态持久化、日志、凭证与产物
    source-version.js       # 源码指纹与缓存
  runtime/
    process-manager.js      # 子进程创建、输出、超时与进程树清理
    taro-plugin.cjs          # Taro 编译结果回传
    capture.js              # H5 console、异常与 fetch/XHR 日志采集
  sdk/
    check.js                # 官方 SDK 的只读完整性检查
  shared/
    files.js                # 有大小上限的文件读取
    redact.js               # 敏感信息脱敏
```

`mcp/server.js` 持有 `Manager`，后者组合 `ProjectStore` 和 `ProcessManager`，分别管理项目数据和子进程。这里的 server 只承载 stdio MCP，不监听 HTTP 工作台端口。`worker.cjs` 隔离 Taro 和 SDK 的输出与同步操作；构建配置在内存中覆盖，不修改项目源码配置。`runtime/capture.js` 只注入 H5 开发页面。

`runtime/safe-area.cjs` 在微信、抖音和支付宝构建产物中适配 `env/constant(safe-area-inset-*)`：由平台窗口信息提供物理 px 值，自定义导航使用状态栏高度，原生导航的顶部值为 0，避免重复留白；底部和左右使用屏幕安全区。支持页面覆盖全局导航配置及分包页面，页面加载和窗口尺寸变化时更新，缺少测量值时保留原生 CSS 回退。支付宝按 `transparentTitle: "always"` 或 `titleBar: false` 识别自定义导航。适配只包装 Taro React 页面根模板，不修改项目源码，也不自动添加业务 padding 或胶囊按钮避让。已验证三端构建和运行逻辑，真机布局仍需扫码验收。

测试统一放在 `app/tests/`，宿主 API 回归验证运行 `node --test app/tests/host-api.test.mjs`。安全区回归验证复用目标 Taro 项目的依赖：`MINIAPP_TEST_PROJECT=/absolute/path/to/project node --test app/tests/safe-area.test.mjs`。

发布时将内部模块打包到 `index.js` 和 `worker.cjs`，保留 `runtime/taro-plugin.cjs`、`runtime/capture.js` 作为 worker 运行时资源。`paths.js` 以 Core 入口所在目录为基准，源码和发布包使用相同的路径规则。

`app/web/src/` 使用 React 实现工作台，图标使用 SVG。`libs/api.js` 通过 `App.callServerTool` 操作项目，通过 `App.sendMessage` 发送修复请求。业务生命周期回调设置后调用 `window.trae.bind(app)`，复用原有 AppBridge。宿主扩展请求通过同一 `App.request` 调用 `trae/navigation/openUrl`（`{ url, browser: "external" }`）、`trae/preview/getUrl`（`{ port }`）与 `trae/panel/open`（`{}`），保留请求超时和预览取消信号。Zod 校验已知响应字段并忽略额外字段。调用前读取 `experimental["trae/host-actions"]` 或 `experimental["trae/panel"]` 的版本和对应能力；缺少能力时明确提示不支持。

App 从工具结果获取归一化项目路径。H5 状态返回端口，工作台在编译就绪后向宿主解析实际预览 URL，保留宿主附带的查询参数，并以实际 URL 的 origin 建立 MessageChannel。运行和网络日志通过 MessageChannel 直接进入工作台前端，脱敏后每类最多保留当前预览的 300 条记录；HMR、页面重载和重新连接保留日志，真正启动新预览进程时清空。独立低频同步通过 `logs(action="append")` 写入本地文件，不影响实时展示。构建、运行和网络日志通过 `inspect` 查询。预览域范围由宿主在 App 初始化时根据当前会话环境统一授权，插件不声明 localhost 或远端域；宿主保证返回的预览 URL 位于已授权范围内。工作台不直接发起网络请求。二维码图片最多 1 MiB；远端二维码由 MCP 下载后以图片数据返回。上传确认在工作台表单内完成。凭证帮助和发布指引的平台入口通过宿主打开系统浏览器，失败时显示提示。

同一 MCP 进程内，项目通过 `realpath` 归一化并复用状态，最多管理 20 个项目。每个项目同时只允许一个受管理的操作，H5 watch 可与平台构建并存。工作台关闭不取消任务；MCP 断开或退出时清理 worker。多个独立 MCP 进程不共享运行状态，同一项目应由一个 MCP 进程管理。

## SDK 与数据位置

SDK 由 MCP 在首次生成对应平台二维码或上传开发版时按需安装，直接使用当前插件的 `app/sdk/<platform>/node_modules`，供所有业务项目共用。环境检查、打开工作台、H5 预览及仅本地构建不下载平台 SDK；不向业务项目的 package.json 添加 SDK。

```text
<pluginRoot>/app/sdk/
  weapp/                    # 清单、锁文件、node_modules、安装指纹
  tt/
  alipay/
  alipay-assets/            # 支付宝共享附加资源

<projectRoot>/.miniapp/
  task.json                 # 最新任务
  compile.log               # 有容量限制的构建与平台任务日志
  runtime.log               # 当前预览的运行日志，最多 2 MiB
  network.log               # 当前预览的网络日志，最多 2 MiB
  credentials/<platform>/   # App ID 与平台凭证
  build/<platform>/         # H5 / 小程序构建产物
  qrcodes/<platform>/       # 最新二维码与元数据
```

SDK 直接在 `app/sdk/<platform>/` 执行 `npm ci`，使用跨进程目录锁避免并发安装；安装前清除成功标记，校验通过后写入安装指纹，失败后下次重新安装。本地安装脚本保留已下载依赖，下次使用时按新锁文件校验。插件 `app/sdk/` 必须可写；SDK 变更期间应避免其他项目正在使用同平台 SDK。平台配置和凭证保持项目隔离，不能放入共享 SDK 目录。

抖音 SDK 的 `setAppConfig` 必须将 Token 写入配置文件；插件为每次调用创建系统临时目录，成功或失败后删除，长期凭证只保存在 `.miniapp/credentials/tt/config.json`。下次抖音调用会删除旧版本留在 `.miniapp/sdk/tt/.tma-cli/appConfig.json` 的副本；进程被强制终止时临时目录可能残留。

支付宝 SDK 的附加资源检查与 npm 包检查分开报告，目录存在不代表下载完整。异常退出遗留安装锁时，先停止使用该 SDK 的 MCP 进程，再处理错误提示中指定的锁目录。旧项目中的 SDK 依赖不会自动迁移或删除。

## 注意事项与边界

- 初始化目录必须不存在；项目依赖安装只支持 npm，不改 pnpm/yarn 项目的锁文件。
- 私钥、Token 和 identity 文件只在工作台填写，不放入 AI 对话或业务代码。项目 `.miniapp/` 自动加入 `.gitignore`，并排除构建复制与源码指纹扫描。文件权限受操作系统支持限制，Windows 不能依赖 Unix 权限位实现访问隔离。
- 生成二维码会构建并上传预览包；上传开发版需明确目标平台、版本和说明，并满足平台权限、IP 白名单及网络要求。
- 每个项目只保存最新任务，每个平台只保存最新二维码。平台调用中断、超时或响应丢失时标记 `failed` 并记录具体原因，先核实平台记录，不自动重传。
- 源码指纹用于判断产物是否过期；源码变化或无法校验时拒绝读取旧二维码。该机制不提供不可变源码快照，也不覆盖环境变量、未链接的外部依赖或 node_modules 内容。
- 构建日志包含准备、安装、编译、上传与二维码生成，记录任务、平台、阶段及脱敏错误；二维码读取不写入构建日志，读取失败时按提示重新生成。新启动预览进程时清空全部三类日志，编译日志不区分 H5 和小程序；复用已有进程不清空。`compileAfter` 标记编译日志清空游标。日志文件上限 8 MiB，内存与工作台展示仍有条数限制；可手动清空。SDK 原始输出可能包含凭证，不直接展示，仅记录安全的进度和异常信息。
- 运行和网络日志在停止、异常断开、HMR 和 H5 页面重连时保留，仅真正启动新预览进程或手动清空时移除。`revision` 只在启动新进程时递增；工作台同一轮预览复用日志 `session`，MessageChannel 重连不创建新日志会话。新工作台接入会替代旧写入会话，但保留已有文件和缓存；按 `session` 与记录 ID 去重，避免不同工作台的 ID 冲突。工作台同步队列最多 300 条，溢出丢弃较早记录；每 5 秒最多提交一批 100 条、256 KiB 的日志，上次请求结束后才安排下一次，不重叠或快速补发。响应丢失后重试不会重复记录或清空。每类文件及缓存最多 2 MiB，超限逐条裁剪较早记录；队列丢弃和容量裁剪通过 `inspect.truncated` 提示。MCP 只缓存序列化记录，inspect 按游标或最新条目选取后再解析，避免全量解析。新增记录异步追加到对应文件，仅初始化、清空、容量裁剪或异常写入恢复时重写；MCP 重启后不恢复这些日志或预览进程。修复只同步本次消息实际包含的错误，完成同步和发送前不插入其他同步或清空操作；消息附带数字 `session`，AI 查询须使用同一值，仅返回该会话日志，已被替代的会话会报错；不传 `session` 可查询保留的历史。
- 预览进程意外退出时显示错误并保留已加载的 iframe，待同步日志仍可落盘；主动停止关闭 iframe，保留日志。重新编译不卸载已加载页面。宿主连接断开时保留已渲染的工作台、日志、诊断信息和 iframe，显示关闭提示并停止轮询与日志同步；此时仅保留页面内的查看能力，宿主操作不可用。
- console 日志包含浏览器生成的调用位置，未做源码映射。网络监控覆盖 H5 fetch/XHR 的显式请求头、浏览器可见响应头及文本请求/响应体；浏览器自动添加或隐藏的头不可读取，不采集静态资源、WebSocket 或真机日志。头及正文各保留约 2000 字符，二进制与流式正文跳过；fetch 响应副本读取最多 4096 字节并限时 1.5 秒，不消费业务响应。日志有速率和数量限制，并对常见敏感字段脱敏；业务代码仍应避免主动打印秘密。
- 本地 H5 预览服务绑定 `127.0.0.1`，使用宿主返回的 `localhost` 地址；远端沙箱由 Agent 注入 `TRAE_SANDBOX_NAME`，服务绑定 `0.0.0.0`，接受预览网关的 Host，通过宿主返回的会话预览地址访问。远端访问依赖宿主网关认证和域授权，不提供公开分享链接。HMR 使用页面所在主机和端口建立 WebSocket。
- 宿主初始化预览域授权不依赖服务是否启动或当前端口；本地动态端口和同一远端预览网关下的端口变化不需要重开卡片。若会话环境变化导致预览地址超出初始化授权范围，宿主拒绝返回该 URL，需要重新调用 `workbench` 并打开新卡片。
- “一键修复”通过 MCP Apps 将错误作为用户消息发送到当前对话，收到宿主确认后为对应日志显示“已发送修复”，保留原错误状态。后续发送跳过已标记记录，新产生的同类错误仍可发送；没有待发送记录时按钮显示“暂无新增错误”。每次按完整日志条目组成不超过 32768 字符的消息，超出批次的记录留待下次发送；单条过长则提示通过 `inspect` 读取，不标记成功。构建卡片聚合多条日志时显示部分发送数量，展开后可看到每条已发送标记。
- 发送标记仅随当前工作台内存中的日志保留，切换日志面板不丢失；清空、运行日志重置或关闭并重新打开工作台后不恢复。工作台关闭会停止前端轮询和日志通道，不取消已经开始的后台任务。
- 日志面板的“清空日志”会清除所选日志的界面记录和本地文件；运行、网络日志同时移除清空前的待同步记录，并等待在途同步结束后清文件，避免旧批次写回。清空游标同时约束后续修复同步，旧错误不能重新写回；清空期间新产生的日志继续保留。构建日志异步合批写入，待写队列最多 1000 条、8 MiB，超限裁剪较早记录并标记 `truncated`，避免慢磁盘造成无限积压。
- 更新插件后需重启 MCP 进程以加载新代码，这会停止该进程管理的所有项目 worker。

## 构建与本地安装

源码位于仓库 `sources/miniapp-builder/`，可安装的插件产物位于 `plugins/miniapp-builder/`。

更新发布版本运行 `node scripts/update-version.mjs`，默认递增补丁版本；也可传入指定版本，如 `node scripts/update-version.mjs 0.1.6`。脚本同步插件元数据、Core 包及锁文件、Skill 版本，不执行构建。

在源码根目录 `sources/miniapp-builder/` 执行：

```sh
node scripts/build-release.mjs
node scripts/install.mjs --local
```

构建脚本先构建 Web，再打包、压缩 Core，组装元数据、Skill、图标和 SDK 安装清单到仓库 `plugins/miniapp-builder/`。平台 SDK 本体不随初始产物分发，由运行时按需安装。

安装脚本支持 `--local`（默认，`~/.trae-cn-local/`）、`--dev`（`~/.trae-cn-dev/`）和 `--stable`（`~/.trae-cn/`），一次只能选择一个渠道。脚本先检查该渠道的 `plugins/trae-remote-official/miniapp-builder/`，按三段数字版本号选择最新已安装目录，再构建并覆盖，保留 SDK 依赖；没有已安装版本时在构建前报告错误。安装脚本包含构建，无需先单独构建。不传参数时安装到 TraeCN Local，只有显式传入 `--stable` 才覆盖正式目录。此命令不上传插件。平台插件发布使用仓库的发布流程。
