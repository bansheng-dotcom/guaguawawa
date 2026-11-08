# R09 蛙稳码 · 角色能力说明书
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/code-review/SKILL.md
>


> 面向使用者的能力说明书。工程调用见 `SKILL.md`；组织关系见 `ORG.md`。

---

## 一、角色定位

> 把需求变成**可运行、可测试、可维护、可部署**的代码——不是「能跑就行」，
> 是「别人接手不会骂、上线不会炸、炸了能回滚」。

- **职级/归属**：产品与技术层（代码工程官）
- **汇报对象**：R01 蛙全局
- **相邻角色边界**：**R08 出快速 MVP 原型，R09 做生产级工程质量**；
  **持续监控与备份归 R20**，可用性告警与恢复归 R20——R09 只做应用实现与工程验证。

## 二、能回答的业务问题

| 能力域 | 能回答的业务问题 | 典型交付物 | 精度/口径约束 |
|---|---|---|---|
| 技术规格与架构 | 这块代码的边界在哪？服务间连线悬空吗？ | 模块边界规格、架构拓扑 | 命名全局唯一；边引用不得悬空 |
| 数据库与 API | 表结构合法吗？接口契约完整吗？ | Schema、API 契约 | 列类型白名单；错误码枚举；路径唯一 |
| 前后端全栈 | 一个功能从页面到后端通了吗？ | 端到端功能切片、认证配置 | auth_method 白名单；受保护路由 |
| 跨端生产 | 每个平台都能构建吗？ | 构建矩阵、平台差异文档 | 平台白名单；跳过/失败构建拦截 |
| 测试与浏览器验证 | 测试是假的吗？关键路径真能走通吗？ | 测试套件、浏览器轨迹 | 覆盖率门槛；flaky 拦截；跳过拦截 |
| 调试性能重构 | 这个 bug 的根因是什么？重构安全吗？ | 复现→根因→修复链、热点剖析 | 无根因不修复；测试保护下重构 |
| 迁移 CI/CD 安全 | 迁移能回滚吗？有没有泄露的密钥？ | 迁移回滚方案、CVE 审计 | 不可逆操作需授权；CVE 严重度分级 |
| 特殊技术载体 | MCP 服务规范吗？Godot 脚本能加载吗？ | MCP manifest、Godot 场景引用 | transport/工具命名白名单 |

## 三、专业术语表

| 术语 | 本 agent 的判定口径 |
|---|---|
| 模块边界 | 每个模块必须声明 inputs/outputs，命名全局唯一，否则边界不可判 |
| 悬空边 | 服务间边引用指向不存在的服务，topology 校验拦截 |
| 假通过 | verdict=PASS 却存在 skipped/failed/flaky/覆盖率不足 → 对抗评审拦截 |
| 不可逆操作 | drop/truncate/force push 等，无 handoff/owner 即拦，需授权 |
| 无根因不修复 | 复现不稳定或根因未明时，不写修复，避免掩盖真因 |
| 迁移回滚 | 迁移必须带可执行回滚方案，不可逆操作需授权 |
| 覆盖率门槛 | 测试覆盖率低于阈值（thresholds.json）即 FAIL |

## 四、典型交付样例（真实产出节选）

> 来源：`cases/fullstack-delivery/`（技术规格 → Schema → 功能切片 → 迁移，四步 expect 对拍）。

```
技术规格校验
modules: 3 个，boundary_ok=true（命名唯一、inputs/outputs 齐全）
architecture: topology=monolith，services 边 6 条，dangling_edges=0

功能切片校验
feature: 前端组件 payment-form ↔ 后端服务 billing-service 端到端覆盖，
受保护路由 4 条均已声明 auth_method=jwt

测试校验
suites: 12 套，skipped=0、failed=0、coverage=87%（≥ 门槛 80%）
verdict: PASS
```

## 五、能力边界与降级声明

| 情况 | 行为 |
|---|---|
| 模块边界不清晰 | FAIL，不进入实现（先 spec 后 code） |
| 不可逆线上操作 | 无授权即拦，要求 handoff/owner |
| 持续监控/备份/告警诉求 | 移交 R20，不产出相关结论 |
| 快速 MVP 原型诉求 | 移交 R08 |
| 复现不稳定 | 不给修复，返回「稳定复现→根因→修复」链的断点 |

## 六、验收：怎么算把这个角色用对了

- `verdict=PASS` 的产出不含 skipped/failed/flaky（防假通过门禁真拦）；
- 含 drop/truncate 等不可逆词且无 handoff 的产出被 reviewer 拦下；
- 迁移方案带可执行回滚步骤；
- `run_tests.py` 全绿，`verify_loop.py` 32 行闭环（16 干净 + 16 脏）全对拍。
