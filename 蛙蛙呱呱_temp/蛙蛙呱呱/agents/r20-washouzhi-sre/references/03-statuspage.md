# 03 · 状态页与事件沟通口径（statuspage）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/skills/status-report/SKILL.md
>


> 技能：`statuspage` ｜ 动作：`statuspage`（组件状态）、`incident`（事件时间线）
> 来源：louislam__uptime-kuma（状态页组件状态、事件状态、对外状态信息）

## 第一层：方法论

状态页层定义**对外呈现什么状态、事件怎么通报**。把这段做成确定性校验的价值，
不在于"页面更好看"，而在于**让倒挂的时间线和越界的组件状态上不了对外页面**——
一张显示 `unknown` 状态的状态页，等于对外承认"我不知道自己死没死"；一条 ts
倒挂的时间线，等于对外撒了个谎。

三条方法论：

1. **状态页是「对外事实」，不是「内部判断」**。本角色只校验组件与事件时间线
   结构能否对外如实呈现，不替业务判断"严重不严重"（那是告警 s02 的事）。
2. **状态必须落在枚举里**。组件状态只许 operational/degraded/outage/
   maintenance；事件状态只许 investigating/identified/monitoring/resolved。
   "unknown" 不是状态，是事故。
3. **时间线必须单调**。ts 单调非递减是硬约束，倒挂 = 沟通失实。resolved
   事件必须带结束时间（resolved_at），否则事件永远"悬着"。

**本角色只校验状态页结构，不实际发布页面**。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| page_id | 非空字符串 | 状态页标识 |
| components | ≥ 1 个组件 | 服务组件集 |
| 每组件 | 含 component_id/name/status 三字段 | 组件结构 |
| component.status | ∈ `statuspage.component_statuses`（operational/degraded/outage/maintenance） | 组件状态枚举 |
| 组件 id | 唯一 | 组件去重 |
| incident_id | 非空字符串 | 事件标识 |
| timeline | ≥ 1 个节点 | 事件时间线 |
| 每节点 | 含 ts/status 两字段 | 时间线结构 |
| 节点 status | ∈ `statuspage.incident_statuses`（investigating/identified/monitoring/resolved） | 事件状态枚举 |
| 时序 | ts 单调非递减 | 时间线顺序 |
| resolved | 末节点 resolved 时须带 resolved_at | 结束时间 |

**阈值单一真源**：`statuspage.component_statuses` / `statuspage.incident_statuses`
以 `experience/thresholds.json` 的 `statuspage` 段为准。

## 第三层：已验证的算例

**算例 A（干净状态页）**：`examples/statuspage.json`
```
status-main / components=[{api,operational},{db,operational}]
```
组件 id 唯一、状态在枚举 → `ok=true`，`verdict=PASS`。

**算例 B（脏状态页）**：`examples/statuspage_dirty.json`
```
components=[{api,unknown}]
```
BLOCKER ×1：`statuspage.required` 拦——status=`unknown` 不在组件状态白名单。

**算例 C（事件时间线）**：`examples/incident.json` vs `incident_dirty.json`
```
timeline=[10:00 investigating, 10:30 identified, 11:00 resolved]
  + resolved_at=11:00  → 时序单调，PASS
timeline=[11:00 resolved, 10:00 investigating]  → ts 倒挂，FAIL
```
时间线 ts 必须单调非递减。末节点 resolved 时须带 resolved_at。

## 第四层：实战踩坑

1. **时序判据用字符串比较**。ts 是 ISO 8601 字符串（`2026-11-05T10:00:00Z`），
   `ts_list == sorted(ts_list)` 依赖字典序恰好等于时间序。这要求上游统一
   ISO 8601 零时区格式。若混入 `2026-11-05 10:00` 和 `2026-11-05T10:00:00Z`，
   字典序会失配——这是 R18 管道 timestamp 口径在 R20 的复现点。

2. **resolved_at 判据只在末节点是 resolved 时触发**。中间节点 resolved 但后面
   又 investigating（状态回退）不在这个判据的射程内，但会被"状态白名单"放过、
   被"时序"放过的状态回退本身是**语义问题**——R20 口径只保证时序与枚举，
   状态机回退交给人工审（s03 的 boundary 写明了"不替业务判断严重性"）。

3. **component_id 唯一判据只看 id**，name 重复不拦。两个组件共用名字"API"
   是产品语义问题（页面上看不出区别），但不是结构问题。R20 只拦 id 重复。

4. **`_validate_resolved_has_end` 是 harness 复用的辅助函数**。主判据内联在
   `_validate_incident` 里，辅助函数供外部（如编排器）单独问"这个事件闭环了吗"。
   两者必须保持同一口径，改一处要同步改。

5. **status 判据用 `not in` 白名单而非 `==`**。给未来新增状态（如
   `partial_outage`）留了明确的扩展点：只改 thresholds 的枚举，判据不变。
