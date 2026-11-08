# R09 蛙稳码（代码工程官）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/code-review/SKILL.md
>


> R09 负责从需求到可运行、可测试、可维护、可部署代码的完整工程链路。
> 核心红线（三条）：**不靠跳过测试制造假通过**；**不可逆线上操作需授权**；
> **持续监控与备份归 R20**，R09 只做应用实现与工程验证。

## 运行方式

```bash
python agent.py manifest                     # 角色能力清单
python agent.py demo                         # 用真实示例跑代表性动作
python agent.py <skill> <action> --input examples/<fixture>.json
python agent.py run --task <task_id>          # workspace 协议（intent 路由）
python agent.py contract list|validate ...
python agent.py review --packet <packet.json> # T7 对抗评审
python agent.py case [<case_id>]              # 案例库
python agent.py harness materials|testreport|plan|runlog ...
python agent.py local-verify --project . --kind unittest --command python # 安全入口本地运行测试
python run_tests.py                           # 全量断言测试
python verify_loop.py                         # 闭环矩阵（32 行全绿）
```

子技能中的结构校验、计划分析为 simulated（只检查给定描述，不表示实际代码/外部系统已执行）。本地 tests/build 仅在 `local-verify` 安全白名单入口运行，并记录 capability_status；部署、线上变更与外部凭据未接入时 blocked。
`__AGENT_RESULT__ {json}` 单行供编排器消费。

## 技能总览（8 技能 × 16 动作）

| 技能 | 动作 | 说明 |
|---|---|---|
| spec 技术规格架构 | spec | 技术规格：模块边界 inputs/outputs、命名唯一 |
| spec 技术规格架构 | arch | 架构拓扑：topology 枚举、服务连线无悬空 |
| data_api 数据库API | schema | Schema：列类型白名单、主键、索引引用 |
| data_api 数据库API | api | API 契约：method 枚举、错误码、路径唯一 |
| fullstack 前后端全栈 | feature | 功能切片：前端组件+后端服务端到端覆盖 |
| fullstack 前后端全栈 | auth | 认证：auth_method 白名单、受保护路由 |
| crossplatform 跨端生产 | build | 构建矩阵：平台白名单、跳过/失败构建拦截 |
| crossplatform 跨端生产 | platform | 平台差异：状态管理白名单、差异文档化 |
| testing 测试浏览器验证 | suites | 测试套件：类型白名单、跳过拦截、覆盖率门槛 |
| testing 测试浏览器验证 | browser | 浏览器关键路径：flow 结果、flaky 拦截、轨迹 |
| debug 调试性能重构 | debug | 稳定复现→根因→修复（无根因不修复） |
| debug 调试性能重构 | refactor | 热点剖析+测试保护下重构（回归全绿） |
| ops 迁移CI/CD安全 | migration | 迁移回滚：不可逆操作需授权 |
| ops 迁移CI/CD安全 | security | 依赖与密钥：CVE 严重度、泄露密钥拦截 |
| special 特殊技术载体 | mcp | MCP 工具服务：transport、工具命名、manifest |
| special 特殊技术载体 | godot | Godot 可加载脚本：场景与脚本引用 |

## 边界声明

- **in_scope**：技术规格与架构、数据库与 API、前后端全栈、跨端生产工程、
  测试与浏览器验证、调试性能重构、迁移 CI/CD 安全、特殊技术载体
  （Godot / MCP / 工程 Agent）
- **out_of_scope**：持续监控与备份（归 R20）、可用性告警与恢复（归 R20）、
  快速 MVP 原型（归 R08）
- **never**：跳过测试制造假通过、未授权执行不可逆线上操作、
  产出持续监控/备份结论而不移交 R20

## 输入契约

每个动作的输入/输出 JSON Schema 登记在 `contracts.py`：
`python agent.py contract list` 查看；输出硬口径 `ok:boolean + checks:array + verdict`。

## 阈值外置

全部枚举/禁词/模式/评分口径在 `experience/thresholds.json`
（topology_types、module_required、column_types、http_methods、auth_methods、
platforms、build_statuses、suite_types、coverage_min、flow_results、
min_repro_steps、irreversible_ops、cve_severities、mcp_transports、
review 禁词/证据键/越界词等）。改口径不改代码。

## 意图路由（run --task 的 intent 关键词 → 动作）

| 关键词示例 | 路由 |
|---|---|
| 技术规格 / 模块边界 / tech spec | spec/spec |
| 架构 / 拓扑 / architecture | spec/arch |
| 数据库 / schema / 索引 | data_api/schema |
| api 契约 / 接口 / 错误码 | data_api/api |
| 全栈 / 端到端 / fullstack | fullstack/feature |
| 认证 / 登录 / auth | fullstack/auth |
| 构建 / 编译 / build | crossplatform/build |
| 跨端 / flutter / 平台差异 | crossplatform/platform |
| 单元测试 / 覆盖率 / test suite | testing/suites |
| 浏览器验证 / e2e / playwright | testing/browser |
| 调试 / 复现 / 根因 / bug | debug/debug |
| 性能 / 重构 / 热点 | debug/refactor |
| 迁移 / 回滚 / migration | ops/migration |
| 安全审计 / cve / 密钥 | ops/security |
| mcp / 工具服务 | special/mcp |
| godot / 游戏工程 | special/godot |
| （兜底） | spec/spec |

## 对抗评审（T7 五检查）

对代码工程产出本身再评审（`review.py`）：
1. **test_skipped_gate**：verdict=PASS 却有 skipped/failed/flaky/覆盖率不足 → react（防假通过）
2. **irreversible_gate**：产出含不可逆操作词（drop/truncate/force push…）但无 handoff/owner → writer
3. **concrete_artifact**：无具体可运行/可交付物（modules/services/tables/suites…）→ controller
4. **scope_boundary**：产出含持续监控/备份/告警词（R20 职责）但无 handoff/owner → writer
5. **evidence_gate**：verdict=PASS 却无任何证据字段 → react

## 案例库

- `fullstack-delivery`：技术规格 → Schema → 功能切片 → 迁移（四步 expect 对拍）
- `refactor-guard`：调试根因 → 测试保护重构（两步 expect 对拍）

## 测试

```bash
python run_tests.py     # T01-T16 全量断言
python verify_loop.py   # 32 行闭环矩阵（16 干净 + 16 脏数据）
```

## 来源

- 补充技能：`KarmenLoop__fullstack-web-delivery`（全栈交付生命周期）、
  `wshobson__agents`（工程规格与架构）、`Jeffallan__claude-skills`、
  `mattpocock__skills`（工程实践）、`browser-use__browser-use`（QA/浏览器验证）、
  `snarktank__ralph`（PRD 转可执行规格）、`obra__superpowers`
  （TDD / 系统化调试 / 验证后才算完成）、`godotengine__godot-demo-projects`
  （Godot 可加载脚本）、`open-gsd__gsd-core`（工程 Agent 工作流）
- 方法论：`references/s01` – `references/s08`
