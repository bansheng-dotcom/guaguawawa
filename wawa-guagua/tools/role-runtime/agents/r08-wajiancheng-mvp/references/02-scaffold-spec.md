# s02 Spec 转仓库（scaffold / spec）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/architecture/SKILL.md
>


来源沉淀：`makerskills`（spec-to-repo / scaffold）。

## 一、方法论（什么时候用、核心口径）

「把 PRD/设计翻译成能立刻跑起来的仓库骨架」。两个动作：
- `scaffold`：校验仓库脚手架——stack 白名单、目录树含入口、文件清单带用途、
  可执行命令齐备、鉴权方式合法。
- `spec`：校验工程 Spec——触发条件、技术栈、交付形态、鉴权四要素齐备，
  是把「想法」转成「工程任务」的最小字段集。

核心红线（R08 实现型身份）：**脚手架是骨架不是生产工程**。`run_commands` 必须是
本地可跑的命令（`npx serve .` / `flutter run`），不能写 CI/CD 流水线命令——
生产级部署、监控告警、多机房属于 R09/R20 的边界。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

栈白名单、鉴权类型、入口标记全部外置：`scaffold.stack_types`、`scaffold.auth_types`、
`scaffold.entry_markers`（验证链：`experience/thresholds.json → _common.load_thresholds()
→ s02_scaffold._validate_scaffold/_validate_spec`）。

**scaffold 校验规则**：
- `stack` 不在 6 类（nextjs/rails/mcp/python-flask/vite-html/node-express）→ `scaffold.stack` BLOCKER。
- `tree` 为空或非数组 → `scaffold.tree` BLOCKER。
- `tree` 拼接后不含入口标记（main/index/app，不区分大小写）→ `scaffold.entry` BLOCKER。
- `files` 每项缺 path / purpose → `scaffold.file.{k}` BLOCKER。
- `run_commands` 为空 → `scaffold.run_commands` BLOCKER。
- `auth` 不在 4 类（none/api-key/oauth/session）→ `scaffold.auth` BLOCKER；缺省按 none。
- `env_vars` 若存在，每项缺 name / description → `scaffold.env_vars` BLOCKER。

**spec 校验规则**：
- `trigger` / `delivery` 任一为空 → `spec.trigger` / `spec.delivery` BLOCKER。
- `stack` 非法、`auth` 非法 → 复用 scaffold 白名单口径。

**输出键**：scaffold → `file_count / stack / verdict / next`；spec → `stack / verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/scaffold.json`：vite-html、tree 含 index.html、files 2 项、run_commands 1 条、
  auth=none、env_vars 1 项 → ok=true、file_count=2、stack=vite-html、verdict=PASS。
- `examples/spec.json`：trigger/stack/delivery/auth 四要素齐 → ok=true、verdict=PASS。
- 脏夹具 `scaffold_dirty.json`：stack=java-spring（非法，且 tree 无入口）→ ok=false / exit 1。
- 脏夹具 `spec_dirty.json`：缺 delivery → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **入口判定要跨 str 与 dict 两种 tree 节点**：tree 可能是 `["index.html"]` 也可能是
  `[{path: "src/main.ts"}]`。实现里对 dict 节点先 `json.dumps` 再小写匹配，否则嵌套树
  形式的目录清单会被误判「无入口」（假阴性放行坏树）。
- **auth 的缺省语义**：`auth` 字段允许缺失（按 none 处理），但如果写了非法值
  （如 `"basic"`）必须拦——「没写」和「写错」是两种语义，不能都放行。
- **env_vars 是可选但一旦存在就逐项校验**：只写了 `name` 没写 `description` 的 env
  会在部署时变成哑变量，必须在门禁期拦下。
- **run_commands 不能空**：没有可执行命令的脚手架等于「一堆文件」，无法被下一位
  协作者验证——这是实现型角色的最低交付底线。
