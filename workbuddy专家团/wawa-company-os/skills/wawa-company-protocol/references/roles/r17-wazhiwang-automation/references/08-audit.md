# 参考层 08 —— 自动化审计（debugging-executions / execution logs）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/skills/code-review/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/debugging-executions`
> 角色：R17 蛙织网 · S08 audit 的确定性口径来源。

## 第一层 · 方法论

自动化不可观察 = 不可运维。n8n 的执行日志（executions）记录每次运行的完整
轨迹。审计的核心立场：**保留六类证据**——谁触发、输入什么、执行了什么、输出
什么、有没有错、谁操作的：

1. **trigger**：什么触发了这次执行（webhook 路径 / schedule / manual）。
2. **input**：进入工作流的数据快照。
3. **execution**：实际跑的工作流（含版本）。
4. **output**：产出的数据。
5. **error**：失败时的错误详情（成功时无）。
6. **operator**：谁发起/审批了这次操作。

这六类证据让任何一次失败都能「回放」：知道当时输入是什么、哪一步错、谁该负责。
n8n 还提供 `debug_execution` 与 `get_resolved_node_parameters` 两个审计工具，用于
复查「节点当时拿到什么参数」。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 证据字段 | trigger/input/execution/output/operator 五类必填 | n8n 执行日志 |
| 执行状态 | success/error/crashed/waiting/running/canceled | n8n execution status |
| 失败可追溯 | status=error 的记录必须有 error 详情 | debugging-executions |
| 统计分布 | 按状态分组实算成功率 | R17 审计统计 |

## 第三层 · 已验证算例

**干净审计**：
```
records=[{execution_id: e1, status: success, trigger: webhook, input: {...},
          execution: wf_main, output: {...}, operator: r17, ts: ...}]
```
门禁：五类证据齐备 + 状态白名单 → PASS，`audit_count=1`。

**脏审计**：
```
records=[{execution_id: e1, status: success, trigger: webhook, input: {...},
          execution: wf_main, output: {...}}]   # 无 operator
```
门禁：`证据字段齐备（缺 ['e1:operator']）` → FAIL。

**干净执行日志**：
```
executions=[{e1: success}, {e2: error, error: timeout}]
```
门禁：状态白名单 + 证据齐备 + error 有详情 → PASS，`success_rate=0.5`，
`failed_count=1`。

## 第四层 · 实战踩坑

1. **`input` 空对象也算缺失**：审计证据用 `not r.get(f)` 判空时，`{}` 是 falsy
   会误报缺失。但空对象确实没有证据价值，宁可拦截——fixtures 里 `input` 必须
   有真实内容。
2. **`error` 字段只在 error 状态强校验**：success 的记录没有 error 字段是正常的，
   别对所有记录都要求 error 非空。
3. **状态集合别漏 `waiting`/`running`/`canceled`**：HITL 审批会停在工作流里等
   人，状态是 `waiting`；用户手动取消是 `canceled`。漏掉会误报状态越界。
4. **成功率是实算不是声明**：`success / total` 用 `safe_div` 实算，不信任记录
   里自带的比例字段（那可能是伪造的）。
