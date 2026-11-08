# 07 · 人工审批与运维接口口径（ops）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/incident-response/SKILL.md
>


> 技能：`ops` ｜ 动作：`request`（运维请求审批）、`alert`（告警规则）
> 来源：apache__airflow（运维动作 backfill / 清理，高风险动作需人工触发）+ airbyte（连接删除/重置）+ dbt（run/clean）

## 第一层：方法论

运维接口是**「请求闸口」不是「执行器」**。高风险动作——回填（backfill）、迁移
（migration）、外发（export）、删除（delete）——都不可逆或影响生产，必须先审批。
把这段做成确定性校验的价值，不在于"运维更快"，而在于
**让高风险动作在人工授权前寸步难行**。

三条方法论：

1. **高风险动作必须显式授权**。`authorization ∈ {authorized, approved}` 才放行，
   `pending` 一律拦。这是红线 2：不擅自回填/迁移/外发/删数据。
2. **审批人与运行手册必填**。谁批的（`approver`）、出事怎么办（`runbook`）、
   能不能撤回（`rollback_plan`）——三者缺一不可。没有退路的操作不能上。
3. **告警规则是运维的眼睛**。没有告警的管道 = 挂了没人知道。告警必须有阈值
   （`condition`）、渠道（`channel`）、严重度（`severity`）。

**本角色只产出「审批单 / 告警配置 / 运维手册」**，**绝不执行**任何高风险动作。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| request.operation | ∈ `ops.operations` = `[backfill, migration, export, delete]` | 高风险动作白名单 |
| request.authorization | ∈ `ops.authorizations` = `[authorized, approved, pending]` | 授权状态 |
| request.authorized | `authorization ∈ {authorized, approved}` | R18 红线 2 |
| request.approver | 非空 | 谁批的 |
| request.runbook | 非空 | 运行手册 |
| request.rollback | `rollback_plan` 非空 | 出事有退路 |
| alert.rules | ≥ 1 条规则 | 无告警 = 瞎跑 |
| alert.required | 每条规则含 `metric`/`condition`/`channel`/`severity` | 告警四要素 |
| alert.severity | severity ∈ `{critical, warning, info}` | 严重度白名单 |

**阈值单一真源**：`ops.operations` / `ops.authorizations` 以
`experience/thresholds.json` 的 `ops` 段为准。

## 第三层：已验证的算例

**算例 A（干净运维请求）**：`examples/ops_request.json`
```
backfill / authorized / approver=R01 / runbook=runbook/backfill.md / rollback_plan=restore from snapshot
```
操作白名单、已授权、审批人+运行手册+回滚计划齐 → `ok=true`，`verdict=PASS`。

**算例 B（脏运维请求）**：`examples/ops_request_dirty.json`
```
drop_all / pending / approver="" / runbook="" / rollback_plan=""
```
BLOCKER ×5：`operation='drop_all'` 不在白名单（`ops.operation`）、`pending` 未授权
（`ops.authorized`）、审批人/运行手册/回滚计划皆空。

**算例 C（脏告警）**：`examples/alert_dirty.json`
```
rules=[{row_count, "< 100", slack, fatal}]
```
BLOCKER ×1：`severity='fatal'` 不在 `{critical, warning, info}`（`alert.severity`）。
对照 `alert.json`（severity=warning）→ `ok=true`。

## 第四层：实战踩坑

1. **`pending` 是"未授权"的显式表达，不是"还没填"**。白名单里有 `pending` 是
   为了能**明确区分**"状态是待批"和"状态字段缺失/非法"。`authorization='pending'`
   → `ops.authorization` 过但 `ops.authorized` 拦（清晰的"待批"语义）。

2. **操作白名单必须严格**。`drop_all` / `truncate_all` 这类不在
   `[backfill, migration, export, delete]` 里的操作，即使看着像"删除"的变体，也
   一律拦——**不认识的破坏性动作 = 最危险的**。要执行须先把它登记进白名单（走
   代码变更 + 评审）。

3. **runbook 与 rollback_plan 是两件事**。runbook 是"怎么操作"，rollback_plan 是
   "怎么撤"。有了 runbook 不代表有退路——两者独立必填。

4. **严重度只有三档不是随意分级**。`critical`（必须立即处理）/ `warning`（需关注）/
   `info`（记录备查）。`fatal` / `error` / `severe` 等自定义档会让告警路由失效，
   一律拦。

5. **告警四要素缺一不可**。`metric`（监控什么）+ `condition`（什么条件触发）+
   `channel`（发到哪）+ `severity`（多严重）。少一个的告警要么不触发、要么触发了
   没人收到、要么收到不知道多严重。

6. **不要写"我已执行删除操作"**。这是越权（`execution_gate`）。正确写法："产出
   运维请求 ops_request.json（operation=delete，已授权，审批人 R01），交人工执行。"

7. **`operations` 白名单是"可申请"不是"可自动执行"**。即使操作在白名单里，仍需
   `authorized` 才放行。白名单管"这个动作认不认"，授权管"这次允不允许"。

8. **告警阈值是字符串条件不是数值**。`condition="< 100"` 是表达式字符串（不解析
   求值），R18 只校验"非空"。真正求值由监控系统做——R18 的职责是"告警配置完整"，
   不是"告警已触发"。
